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

#no need for Login view as we're using JWT and it's already handled by djangorestframework-simplejwt. see main lyncup folder's urls.py

#this is just a class for frontend users to test if the API service can be accessed with their authenticated token.
class TestApi(APIView):
    #DRF automatically handles authentication errors when IsAuthenticated is used, don't need to write it myself.
    # permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        return Response({"message": "API access successful!"}, status=200) 

#register users
class Register(generics.GenericAPIView, mixins.CreateModelMixin):

    #serializer_class comes from GenericAPIView
    serializer_class = RegisterSerializer

    def post(self, request, *args, **kwargs):
        #.create comes from Mixin
        return self.create(request, *args, **kwargs)


class LikeView(APIView):

    permission_classes = [IsAuthenticated]

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

    permission_classes = [IsAuthenticated]

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
    permission_classes = [IsAuthenticated]
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
    
    permission_classes = [IsAuthenticated]

    serializer_class = ShowProfileOrgSerializer
    queryset = Profile.objects.all()
    #DRF should try to match this field. The model field that should be used for performing object lookup of individual model instances. Defaults to 'pk', see https://www.django-rest-framework.org/api-guide/generic-views/
    lookup_field = "appuser"

    #this field is what's in the url, this will be used to lookup appuser in lookup_field. See documentation.
    lookup_url_kwarg = "appuser_id"

#to query multiple profiles
class ShowMultiProfilesView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
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
    permission_classes = [IsAuthenticated]
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








    

    





        

        













            

            