from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework import mixins
from .serializers import *
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from django.contrib.auth import get_user_model 
from django.core.exceptions import ValidationError
from django.http import Http404
from .models import *
from .serializers import *
from .utils import send_verification_email
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.tokens import default_token_generator
from rest_framework import permissions
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import AllowAny
from django.shortcuts import redirect
from django.conf import settings



#no need for Login view as we're using JWT and it's already handled by djangorestframework-simplejwt. see main lyncup folder's urls.py

#this is just a class for frontend users to test if the API service can be accessed with their authenticated token.
class TestApi(APIView):
    #DRF automatically handles authentication errors when IsAuthenticated is used, don't need to write it myself.
    # permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        return Response({"message": "API access successful!"}, status=200) 

#anywhere we want to block unverified accounts, add this permission
class IsVerified(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_verified)

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

class VerifiedTokenObtainPairView(TokenObtainPairView):
    serializer_class = VerifiedTokenObtainPairSerializer

class VerifyEmailView(APIView):
    #authentication_classes determines who the user is by reading tokens or session info from the request and setting request.user.
    #permission_classes decides whether that user is allowed to access the view, based on rules like IsAuthenticated or custom conditions.
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

class ResendVerificationView(generics.GenericAPIView, mixins.CreateModelMixin):

    serializer_class = ResendVerificationSerializer
    authentication_classes = []           #no auth needed
    permission_classes = [AllowAny]    #open to anyone

    #POST { "email": "you@example.com" }

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
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


#like and unlike can be placed into viewset, but will refactor later.
class LikeView(APIView):

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsVerified]

    #we are using APIVIew here instead of (generics.GenericAPIView, mixins.CreateModelMixin) because the like instance is often not unique (e.g if the row already exists, we need to increment the value of like count). unique_together that is enforced inside serializer.is_valid and on the model level (we defined it), called by .create (from mixins.CreateModelMixin would prevent that) Hence we need to use custom APIView instead, much easier to handle it this way. That means we don't need to define a serializer class (serializer_class = LikeSerializer) here and can just bypass serializer. But we still need serializer in place to ensure that the incoming request is in the right format.

    #we write our own post:
    def post(self, request, *args, **kwargs):
        #validate the data manually with serializer
        serializer = LikeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_from_instance = request.user
        user_to_id = request.data.get("user_to")
        custom_user_model = get_user_model()
        user_to_instance = get_object_or_404(custom_user_model, id=user_to_id)

        #check that the user isn't liking themself
        if user_from_instance == user_to_instance:
            raise ValidationError("User cannot like themself")

        like_instance, isCreated = Like.objects.get_or_create(user_from=user_from_instance, user_to=user_to_instance)

        #if its not newly created, then we increment the like count in the existing row:
        if not isCreated:
            like_instance.like_count += 1
            like_instance.last_like_date = now()
            like_instance.save()

        #return to the React side
        return Response({
            "user_from": user_from_instance.id,
            "user_to": user_to_instance.id,
            "like_count": like_instance.like_count,
            "last_like_date": like_instance.last_like_date
        },status=status.HTTP_200_OK)

#this is mainly to reverse a like that has been made during the same chat session when a like was made.
class UnlikeView(APIView):

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsVerified]

    def post(self, request, *args, **kwargs):
        #validate data, can share serializer with LikeView as there's no change in format
        serializer = LikeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        custom_user_model = get_user_model()

        user_to_id = request.data.get("user_to")
        user_from_instance = request.user
        user_to_instance = get_object_or_404(custom_user_model, id=user_to_id)

        if user_from_instance == user_to_instance:
            raise ValidationError("User cannot unlike themself")

        like_instance = get_object_or_404(Like, user_from=user_from_instance, user_to=user_to_instance)

        if like_instance.like_count > 0:
            like_instance.like_count -= 1
            like_instance.save()

        #return to the React side
        return Response({
            "user_from": user_from_instance.id,
            "user_to": user_to_instance.id,
            "like_count": like_instance.like_count,
            "last_like_date": like_instance.last_like_date
        },status=status.HTTP_200_OK)

#I know we could alternatively use generics.UpdateAPIView alone instead which means I don't need to use Mixin as its included but I want more flexibility to customise, such as logging different error messages as below. I prefer using these instead.
class UpdateProfileView(generics.GenericAPIView, mixins.UpdateModelMixin):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsVerified]
    serializer_class = UpdateProfileOrgSerializer

    #get_objects is called by automatically by update(), (which is automatically called by put, if using UpdateAPIView), and partial_update(), (automatically called if using UpdateAPIView), from UpdateModelMixin. The reason I override this is because the default behaviour is it would try to grab the pk in the url and then look up the relevant role in model. I don't want that, I want to eliminate the chance of the user sending the request to possibly change other users' profiles.
    def get_object(self):
        #ensure the user can only update their own profile
        #if the profile doesn't yet exist, it will create it.
        #remember, this is called by .update and .partial_update (defined in put and patch below), so it can access the "request" parameter from the parent. it is a method inside a class-based view, and self refers to the view instance that automatically contains the request object

        profile, isCreated = Profile.objects.get_or_create(appuser=self.request.user)
        return profile

    #because we're not using generics.UpdateAPIView , we're using generics.GenericAPIView, mixins.UpdateModelMixin, we need to define put and patch.
    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    #From documentation: what goes on in update (from mixins.UpdateModelMixin):
    # def update(self, request, *args, **kwargs):
    #     partial = kwargs.pop('partial', False)
    #     instance = self.get_object()
    #     serializer = self.get_serializer(instance, data=request.data, partial=partial) <---instance is from get_object
    #     serializer.is_valid(raise_exception=True)
    #     self.perform_update(serializer) <---this one calls serializer.save, which calls update in serializer.
    #     return Response(serializer.data)

    #may not need this but place here anyway just in case:
    #shares same serializer as put.
    #even though serializer defines all fields, DRF knows to update only "aboutme" because of the partial=True flag, which is done when partial_update() is called.
    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

#to show user their own profile info
class ShowProfileView(generics.RetrieveAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsVerified]

    serializer_class = ShowProfileOrgSerializer
    queryset = Profile.objects.all()
    #DRF should try to match this field. The model field that should be used for performing object lookup of individual model instances. Defaults to 'pk', see https://www.django-rest-framework.org/api-guide/generic-views/
    lookup_field = "appuser"

    #this field is what's in the url, this will be used to lookup appuser in lookup_field. See documentation.
    lookup_url_kwarg = "appuser_id"

#to query multiple profiles
class ShowMultiProfilesView(generics.ListAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsVerified]
    serializer_class = ShowProfileOrgSerializer

    def get_queryset(self):
        user_ids_param = self.request.query_params.get("user_ids", "")
        user_ids = []
        try:
            for uid in user_ids_param.split(','):
                if uid.strip().isdigit():
                    user_ids.append(int(uid.strip()))

            if not user_ids:
                #to avoid returning all profiles
                return Profile.objects.none()
        except ValueError:
            user_ids = []
        return Profile.objects.filter(appuser__id__in=user_ids)


#find organisation in the database, which may return a collection. generics.RetrieveAPIView is not suitable as we will give a partial keyword DRF will then return a collection of related companies. I need to override, so generics + mixins is better.
class SearchOrgView(generics.GenericAPIView, mixins.ListModelMixin):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsVerified]
    serializer_class = OrganisationSerializer

    def get_queryset(self):
        #e.g. /?q=google
        #shouldnt be ("q", None) as this would return all records
        org_name = self.request.query_params.get("q", "").strip()
        #icontains is case insenstiive search
        queryset = Organisation.objects.filter(name__icontains=org_name)
        return queryset


    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    #how .list works internally https://www.cdrf.co/3.14/rest_framework.mixins/ListModelMixin.html#list:
    # def list(self, request, *args, **kwargs):
    #     queryset = self.filter_queryset(self.get_queryset())

    #     page = self.paginate_queryset(queryset)
    #     if page is not None:
    #         serializer = self.get_serializer(page, many=True)
    #         return self.get_paginated_response(serializer.data)

    #     serializer = self.get_serializer(queryset, many=True)
    #     return Response(serializer.data)

class AddRequestView(generics.GenericAPIView, mixins.CreateModelMixin):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsVerified]
    serializer_class = AddRequestSerializer

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


class ShowSentRequestsView(generics.GenericAPIView, mixins.ListModelMixin):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsVerified]
    serializer_class = AddRequestSerializer

    #get data source
    def get_queryset(self):
        return AddRequest.objects.filter(user_to=self.request.user)

    #get is executed and called by GenericAPIVIew. .get then calls get_queryset() to get the data source. /list is provided by mixins.ListModelMixin
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)








    

    





        

        













            

            