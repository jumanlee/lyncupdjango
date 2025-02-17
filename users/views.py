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


from .models import *
from .serializers import *

#no need for Login view as we're using JWT and it's already handled by djangorestframework-simplejwt. see main lyncup folder's urls.py

#register users
class Register(generics.GenericAPIView, mixins.CreateModelMixin):

    #serializer_class comes from GenericAPIView
    serializer_class = RegisterSerializer

    def post(self, request, *args, **kwargs):
        #.create comes from Mixin
        return self.create(request, *args, **kwargs)

# class AddFriend(generics.GenericAPIVIew, mixins.CreateModelMixin):

#     serializer_class = AddRequestSerializer

# #override perform_Create to prevent duplicate!

class LikeView(APIView):

    # serializer_class = LikeSerializer
    permission_classes = [IsAuthenticated]

    #we are using APIVIew here instead of (generics.GenericAPIView, mixins.CreateModelMixin) because the like instance is often not unique (e.g if the row already exists, we need to increment the value of like count). unique_together that is enforced inside serializer.is_valid, called by .create (from mixins.CreateModelMixin would prevent that) Hence we need to use custom APIView instead, much easier to handle it this way. That means we don't need to define a serializer class (serializer_class = LikeSerializer) here and can just bypass serializer. But we still need serializer in place to ensure that the incoming request is in the right format.

    #we write our own post:
    def post(self, request, *args, **kwargs):
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










            

            