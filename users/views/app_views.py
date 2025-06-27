from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework import mixins
from users.serializers.app_serializers import *
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


#view to check whether the user's profile is complete or not (all required fields are filled in)
class CheckProfileCompleteView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsVerified]

    def get(self, request, *args, **kwargs):
        #get the profile for the user
        profile, isCreated = Profile.objects.get_or_create(appuser=request.user)

        return Response(
            {"profile_complete": profile.required_complete},
            status=status.HTTP_200_OK
        )

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

    #ListAPIView inherits from ListModelMixin, which provides the .list() method. .get() → calls .list():
    # def get(self, request, *args, **kwargs):
    #     return self.list(request, *args, **kwargs)
    #and inside list(), the first thing it does is:
    #queryset = self.filter_queryset(self.get_queryset()). We ovverride this as we need to deal with the array of user_ids passed in the query params.

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

class ShowAllCountriesView(generics.ListAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsVerified]
    serializer_class = CountrySerializer

    #no need to override get_queryset() as we just want to return all countries, straightforward
    queryset = Country.objects.all().order_by("name")


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
