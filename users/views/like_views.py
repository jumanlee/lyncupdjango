from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework import mixins
from users.serializers.like_serializers import *
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from django.contrib.auth import get_user_model 
from django.core.exceptions import ValidationError
from django.http import Http404
from users.models import *
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
from .aux_views import IsVerified



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