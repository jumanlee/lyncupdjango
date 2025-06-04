from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework import mixins
from .auth_serializers import *
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from django.contrib.auth import get_user_model 
from django.core.exceptions import ValidationError
from django.http import Http404
from users.models import *
from .utils import send_verification_email, send_password_reset
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.tokens import default_token_generator
from rest_framework import permissions
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import AllowAny
from django.shortcuts import redirect
from django.conf import settings
from rest_framework.throttling import AnonRateThrottle
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from users.aux_func.aux_views import IsVerified


#no need for Login view as we're using JWT and it's already handled by djangorestframework-simplejwt. see main lyncup folder's urls.py

class VerifiedTokenObtainPairView(TokenObtainPairView):
    serializer_class = VerifiedTokenObtainPairSerializer

#register users
class Register(generics.GenericAPIView, mixins.CreateModelMixin):
    #skips all auth backend
    #we have a global default of JWTAuthentication in settings.py ('rest_framework_simplejwt.authentication.JWTAuthentication'), because we didn’t override it on Register view, DRF still tries to authenticate the incoming request with whatever’s in Authorization header, fails, and returns 401 before perform_create() ever runs.
    #so DRF would try to parse a token on every request—including register
    #and reject with 401 if the header is missing or invalid.
    #by setting authentication_classes to an empty list, we tell DRF: “Don’t run any authentication backends here.”
    authentication_classes = []

    #permission_classes must be explicit; an empty list would mean “no permissions defined”
    #(which by default denies all). AllowAny lets anonymous users create accounts.          
    permission_classes = [AllowAny]

    #serializer_class comes from GenericAPIView
    serializer_class = RegisterSerializer

    def post(self, request, *args, **kwargs):
        #"" the default value returned if the key "email" does not exist in request.data
        email = request.data.get("email", "").strip().lower()
        custom_user_model = get_user_model()

        #if an account already exists
        try:
            existing = custom_user_model.objects.get(email=email)
        except custom_user_model.DoesNotExist:
            existing = None
        
        if existing and not existing.is_verified:
            #silently re-send the link
            send_verification_email(existing)

            return Response(
                {
                    "detail": (
                        "This e-mail is already registered but not verified. "
                        "We've just sent you a fresh verification link, "
                        "please check your inbox."
                    ),
                    "code": "verification_resent",
                },
                status=status.HTTP_200_OK,     
            )
        if existing:
            return Response(
                {
                    "detail": (
                        "An account with that e-mail already exists. "
                        "Please log in instead."
                    ),
                    "code": "already_exists",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
            
        #otherwise, if not already existing, go create
        #.create comes from Mixin
        return self.create(request, *args, **kwargs)


    #perform_create is called by self.create above
    def perform_create(self, serializer):
        user = serializer.save()         #creates AppUser + Profile
        send_verification_email(user)

#the link that the user clicks on in the email
class VerifyEmailView(APIView):
    #authentication_classes determines who the user is by reading tokens or session info from the request and setting request.user.
    #permission_classes decides whether that user is allowed to access the view, based on rules like IsAuthenticated or custom conditions.
    #we allow anyone to access this view. the real check is done in the get() method below: if default_token_generator.check_token(user, token):
    authentication_classes = []       
    permission_classes = [AllowAny]

    def get(self, request, uidb64, token, *args, **kwargs):
        try:
            #urlsafe_base64_decode(uidb64) this decodes that base64 string back into bytes
            #force_str(...) this converts bytes back into a string
            uid = force_str(urlsafe_base64_decode(uidb64))

            #get_user_model() looks at AUTH_USER_MODEL in settings.py, so get_user_model() gets the custom AppUser class, as defined in models.py, not Django’s default User
            user = get_user_model().objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, get_user_model().DoesNotExist):
            return Response({"detail": "Invalid link"}, status=status.HTTP_400_BAD_REQUEST)

        if default_token_generator.check_token(user, token):
            if not user.is_verified:
                user.is_verified = True
                user.save()
            return redirect(settings.FRONTEND_VERIFY_SUCCESS_URL)

        # return Response({"detail": "Invalid or expired link"}, status=status.HTTP_400_BAD_REQUEST)
        return redirect(settings.FRONTEND_VERIFY_FAIL_URL)

#this is the view for when user requests a new verification email
class ResendVerificationView(generics.GenericAPIView, mixins.CreateModelMixin):

    #serializer_class is from GenericAPIView
    serializer_class = EmailSerializer
    authentication_classes = []           #no auth needed
    permission_classes = [AllowAny]    #open to anyone

    #POST { "email": "you@example.com" }

    def post(self, request, *args, **kwargs):
        #get_serializer() is from genericAPIView to instantiate the serializer_class
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        #.is_valid stores the cleaned result in serializer.validated_data
        email = serializer.validated_data["email"]

        #get_user_model() returns the appuser class, obtained from settings.py, not an instance!
        custom_user_model = get_user_model()
        try:
            user = custom_user_model.objects.get(email=email)
        except custom_user_model.DoesNotExist:
            return Response(
                {"detail": "No account with that email"},
                status=status.HTTP_404_NOT_FOUND
            )

        if user.is_verified:
            return Response(
                {"detail": "Email already verified."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # send new verification link
        send_verification_email(user)
        return Response(
            {"detail": "Verification email resent."},
            status=status.HTTP_200_OK
        )

#view for when user requests a password reset
class SendPasswordResetView(generics.GenericAPIView, mixins.CreateModelMixin):
    serializer_class = EmailSerializer
    authentication_classes = []           #no auth needed
    permission_classes = [AllowAny]    #open to anyone

    #prevent spam, limit to limited requests per hour, see settings.py rest framework
    throttle_classes   = [AnonRateThrottle]

    #POST { "email": "you@example.com" }
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        custom_user_model = get_user_model()
        try:
            user = custom_user_model.objects.get(email=email)
        except custom_user_model.DoesNotExist:
            return Response(
                {"detail": "If your email is registered, you will receive a reset link."},
                status=status.HTTP_200_OK
            )

        #send new reset link
        send_password_reset(user)
        return Response(
            {"detail": "If your email is registered, you will receive a reset link."},
            status=status.HTTP_200_OK
        )

#get: view for when user clicks on the link in the email
#post: view for when user submits the new password from React
class ResetPasswordView(APIView):
    authentication_classes = []       
    permission_classes = [AllowAny]
    throttle_classes   = [AnonRateThrottle]

    #this is for when user clicks on the link in the email
    def get(self, request, uidb64=None, token=None, *args, **kwargs):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = get_user_model().objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, get_user_model().DoesNotExist):
            return redirect(settings.FRONTEND_RESET_PASSWORD_FAIL_URL)

        if not default_token_generator.check_token(user, token):
            return redirect(settings.FRONTEND_RESET_PASSWORD_FAIL_URL)

        #redirect to react
        return redirect(f"{settings.FRONTEND_RESET_PASSWORD_URL}/{uidb64}/{token}")

    #this is for when user submits the new password from React
    def post(self, request, uidb64=None, token=None, *args, **kwargs):

        #validate input, make sure there's minimum length as per serializer
        data = {
            'uidb64': uidb64,
            'token': token,
            'new_password': request.data.get('new_password')
        }
        serializer = PasswordResetConfirmSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        new_password = serializer.validated_data['new_password']

        #lookup user
        try:
            uid  = force_str(urlsafe_base64_decode(serializer.validated_data['uidb64']))
            user = get_user_model().objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, get_user_model().DoesNotExist):
            return Response({'detail': 'Invalid or expired token.'}, status=status.HTTP_400_BAD_REQUEST)

        #check token
        if not default_token_generator.check_token(user, serializer.validated_data['token']):
            return Response({'detail': 'Invalid or expired token.'}, status=status.HTTP_400_BAD_REQUEST)

        #save new password
        user.set_password(new_password)
        user.save()
        return Response({'detail': 'Password has been reset.'}, status=status.HTTP_200_OK)

#this is for change password for users already logged in
class ChangePasswordAuthenticatedView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsVerified]

    #I'm delegating the password validation to the serializer, so I don't need to do it here. Alternatively, I could do it here too, but since I already have validate_password in other serializers, better to keep it consistent. Do deletegate to serializer, I will need to pass "context" because passing data=request.data only passes request.data, not the request.user needed for validation. "context" allows me to pass the request object to the serializer, so I can access the user in the serializer.
    def post(self, request, *args, **kwargs):
        serializer = ChangePasswordAuthenticatedSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()

        return Response({"detail": "Password updated successfully."}, status=status.HTTP_200_OK)