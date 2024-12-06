from django.shortcuts import render


from rest_framework.views import APIView
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import ObjectDoesNotExist 
from django.shortcuts import get_object_or_404
from rest_framework import mixins
from django.core.exceptions import PermissionDenied
from django.http import Http404

from .models import *
from .serializers import *

#note juman, change all of these to ModelViewSet

# Following code is written by me
# Create your views here.

#class for registering users
class Register(APIView):

    def post(self, request, format='json'):
        #this serializer_class is NOT the built in one, its a variable defined by myself, unlike the serializer_class used in GenericAPIView. This is APIView, so serializer_class is not applicable, this needs to be done differently.
        serializer_class = RegisterSerializer(data=request.data)



        #is_valid() will return true if valid. If any errors, is_valid() will return false. 
        if serializer_class.is_valid():

            #save this instance
            serializer_class.save()

            #response code as per django rest framework documentation: https://www.django-rest-framework.org/tutorial/2-requests-and-responses/
            return Response(serializer_class.data, status=status.HTTP_201_CREATED)

        return Response(serializer_class.errors, status=status.HTTP_400_BAD_REQUEST)


#view for add a friend. The reason why mixins.RetrieveModelMixin is not required here is because I am not performing a standard CRUD operation here. Rather, I am doing a very specific action adding a friend which involves a complex set of operations. This is not a basic retrieve a model or update a model that the standard mixins allows one to quickly perform. Cuz of the complexity, I did this manually. 

#In AddFriend view, this is not performing a standard CRUD operation. Instead, its performing a very specific action, adding a friend, which involves a more complex workflow. It's not a basic "Retrieve a model" or "Update a model" operation, so a mixin isn't needed or particularly useful.
class AddFriend(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request, format='json'):

        #get the from_user id, which is the client sending the data. Since the user is authenticated, we can just do the following to get their id. On a side note, the to_user id is obtained from the client side. The client side requests from the api and get the user_to id, then send it to here. 
        userFromID = request.user.id

        clientPayload = request.data

        userToID = clientPayload.get('user_to', None)

        #test to see if it already exists
        try:
            AppUser.objects.get(id=userToID)
        except ObjectDoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        
        clientPayload['user_from'] = userFromID

        print("clientpayload")

        print(clientPayload)

        serializer_class = AddRequestSerializer(data=clientPayload)

        if serializer_class.is_valid():
            serializer_class.save()
            return Response(serializer_class.data, status=status.HTTP_201_CREATED)

        return Response(serializer_class.errors, status=status.HTTP_400_BAD_REQUEST)

#view for retrieving friendlist. generics.ListAPIView is a subclass of ListAPIView, which is for handling GET requests to retrieve a list of resources.
class FriendList(generics.ListAPIView):

    permission_classes = [IsAuthenticated]

    serializer_class = AppUserSerializer 

    #This queryset is redundant because I already have the get_queryset method, so I have commented out. The get_queryset method overrides the queryset attribute. So in this case, the queryset = AppUser.objects.all() line can be removed because it is not being used, the queryset is determined by the logic in the get_queryset method. The queryset is a class attribute that provides the initial queryset that the view will operate on. When using class-based views in Django, like ListAPIView, this attribute is used to specify what records are retrieved from the database by default. The get_queryset method allows dynamically customise this queryset. When defining get_queryset, it replaces the static queryset attribute. So whatever it returns from get_queryset becomes the new queryset that the view will use. This allows for more dynamic behavior, like filtering records based on the logged-in user. So if I define both queryset and get_queryset, Django will use get_queryset and ignore queryset. Which means it is actually redundant, therefore I have commented it out.

    # queryset = AppUser.objects.all()

    def get_queryset(self):

        #self.request.user will give us the authenticated user sending the request. This is an instance of the AppUSer and contains all of the fields defined in models.py

        authenticatedUser = self.request.user

        try:
            friendships = Friendship.objects.get(appuser=authenticatedUser)
            return friendships.appfriends.all()
        except Friendship.DoesNotExist:
            return AppUser.objects.none()  



#Accept friend request. This can only be used by the receiving party.
class AcceptRequest(APIView):

    permission_classes = [IsAuthenticated]

    #Because serialisers are more for validating and transforming complex data types like querysets and model instances into JSON data, for straightforward tasks like creating or updating a single object based on simple conditions, using serialisers might be overkill. So, only some simple logic here will do.

    def post(self, request, format='json'):

        #get the user to data from client
        userToID = request.user.id

        #get the id of the authenticated user
        userFromID = request.data.get('user_from')

        #get appuser instances
        userFromInstance = get_object_or_404(AppUser, id=userFromID)
        userToInstance = get_object_or_404(AppUser, id=userToID)

        #test if it exists, if exists, get it, otherwise, raise 404 error and stop
        addRequestInstance = get_object_or_404(AddRequest, user_from=userFromInstance, user_to_id=userToInstance)

        #create the friendship (and then link) for the associated appuser instances.
        userFromFriendshipInstance, isUserFromFriendshipCreated = Friendship.objects.get_or_create(appuser=userFromInstance)
        userToFriendshipInstance, isUserToFriendshipCreated = Friendship.objects.get_or_create(appuser=userToInstance)


        #add the appfriends
        #The .add() is used to add record in a many-to-many relationship. In this case, it will add the friendship instances to the appfriends ManyToManyField. This operation creates a new row in the underlying join table that establishes the many-to-many link. 
        userFromFriendshipInstance.appfriends.add(userToInstance)
        userToFriendshipInstance.appfriends.add(userFromInstance)


        #then delete the add request record as it is no longer needed.
        addRequestInstance.delete()

        return Response({"status": "Friend is added"}, status=status.HTTP_200_OK)

#decline add request. This can only be used by the receiving party.
class DeclineRequest(APIView):

    permission_classes = [IsAuthenticated]

    #Because serialisers are more for validating and transforming complex data types like querysets and model instances into JSON data, for straightforward tasks like creating or updating a single object based on simple conditions, using serialisers might be overkill. So, only some simple logic here will do.


    def post(self, request, format='json'):

        #get the user to data from client
        userToID = request.user.id

        #get the id of the authenticated user
        userFromID = request.data.get('user_from')

        #get appuser instances
        userFromInstance = get_object_or_404(AppUser, id=userFromID)
        userToInstance = get_object_or_404(AppUser, id=userToID)

        #test if it exists, if exists, get it, otherwise, raise 404 error and stop
        addRequestInstance = get_object_or_404(AddRequest, user_from=userFromInstance, user_to_id=userToInstance)

        #then delete the add request record as it is no longer needed.
        addRequestInstance.delete()

        return Response({"status": "Friend request is declined!"}, status=status.HTTP_200_OK)


#Cancel add request. This can only be used by the sending party.
class CancelRequest(APIView):

    permission_classes = [IsAuthenticated]

    #Because serialisers are more for validating and transforming complex data types like querysets and model instances into JSON data, for straightforward tasks like creating or updating a single object based on simple conditions, using serialisers might be overkill. So only some simple logic here will do.


    def post(self, request, format='json'):

        #get the user to data from client
        userToID = request.data.get('user_to')

        #get the id of the authenticated user
        userFromID = request.user.id

        #get appuser instances
        userFromInstance = get_object_or_404(AppUser, id=userFromID)
        userToInstance = get_object_or_404(AppUser, id=userToID)

        #test if it exists, if exists, get it, otherwise, raise 404 error and stop
        addRequestInstance = get_object_or_404(AddRequest, user_from=userFromInstance, user_to_id=userToInstance)

        #then delete the add request record as it is no longer needed.
        addRequestInstance.delete()

        return Response({"status": "Friend request is deleted!"}, status=status.HTTP_200_OK)

#search user functionality
class SearchUser(generics.ListAPIView):

    permission_classes = [IsAuthenticated]

    #this serializer is so that the view knows how to serialise the queryset into JSON back to the client.
    serializer_class = SearchUserSerializer

    #the logic of filtering must be in get_queryset and NOT serializer! The serializer's is meant to transform complex data types like querysets into JSON data that can be rendered into content types. The logic for what data to work with of filtering based on first name and last name should be in the view's get_queryset. 
    def get_queryset(self):

        #in this case, get_object_or_404 shjould not be used because we are dealing with a list of objects and not a single object. e.g. it would raise a 404 error if more than one object matches the query or if no objects match.
        #'' is a default value created if none is found. This will then go into the search filtering which will return empty set. Note that I am sending in via url, not body, as this is a get request. That's why request.data is not used. 
        firstname = self.request.query_params.get('firstname', '')
        lastname = self.request.query_params.get('lastname', '')

        if firstname and lastname:
            return AppUser.objects.filter(firstname=firstname, lastname=lastname)
        else:
            return AppUser.objects.none()


#functionality to update status, Here I am using generics.UpdateAPIView, unlike in above classes. This handles PUT request.
class UpdateStatus(generics.UpdateAPIView):

    #no need to manually handle the updated text from the client as this is already handled by generics.UpdateAPIView and the serializer. Specifically UpdateStatus receives the put requests and uses get_object to find the relevant profile object. Then the DRF generics.UpdateAPIView takes the data from the request.data body and pass it to the serializer. If all is valid, then it saves the updated data into the Profile object obtained by get_object.
    serializer_class = UpdateStatusSerializer
    permission_classes = [IsAuthenticated]

    #get_object is a method that returns the object that the view will display or modify. But here we are overriding it. get_object looks up a single object based on the urls primary key argument. But can override get_object to customise the behavior. The get_object method returns the object to generics.UpdateAPIView. It doesn't send it back to the client. The object is then used by the update method to perform the update operation based on the request data. After the update is complete, a response is sent back to the client. get_object returns straight to generics.UpdateAPIView. The serializer comes into play when the update method takes the request.data and validates or serializes it using the specified serializer_class. After serialization and validation, the object returned by get_object is updated.
    def get_object(self):
        #in case the profile is not created, this will create it. Better than using create or 404 just in case.
        profile, isCreated = Profile.objects.get_or_create(appuser=self.request.user)
        return profile


class UpdateBio(generics.UpdateAPIView):

    #no need to manually handle the updated text from the client as this is already handled by generics.UpdateAPIView and the serializer. Specifically UpdateStatus receives the put requests and uses get_object to find the relevant profile object. Then the DRF generics.UpdateAPIView takes the data from the request.data body and pass it to the serializer. If all is valid, then it saves the updated data into the Profile object obtained by get_object.
    serializer_class = UpdateBioSerializer
    permission_classes = [IsAuthenticated]

    #get_object is a method that returns the object that the view will display or modify. But here we are overriding it. get_object looks up a single object based on the urls primary key argument. But can override get_object to customise the behavior. The get_object method returns the object to generics.UpdateAPIView. It doesn't send it back to the client. The object is then used by the update method to perform the update operation based on the request data. After the update is complete, a response is sent back to the client. get_object returns straight to generics.UpdateAPIView. The serializer comes into play when the update method takes the request.data and validates or serializes it using the specified serializer_class. After serialisation and validation, the object returned by get_object is updated.
    def get_object(self):
        #in case the profile is not created, this will create it. Better than using create or 404 just in case. This is because when the user first registers, they may not have a profile, so if they update, they are going to update with no profile, so this or_create will resolve that.
        profile, isCreated = Profile.objects.get_or_create(appuser=self.request.user)
        return profile
        

class GetFriendProfile(mixins.RetrieveModelMixin,
                 generics.GenericAPIView):

       permission_classes = [IsAuthenticated]
 
    #    queryset = Profile.objects.all()
       serializer_class = GetProfileSerializer


        #override queryset
       def get_queryset(self):
            user_id = self.kwargs['pk']

            friendsOfSender = Friendship.objects.get(appuser=self.request.user)

            if user_id is None:
                raise PermissionDenied('No user ID!')

            if not friendsOfSender.appfriends.filter(id=user_id).exists():
                raise PermissionDenied('You can only view this profile if you are a friend')

            appuser = AppUser.objects.get(id=user_id)
            profiles = Profile.objects.filter(appuser=appuser)
            return profiles


       def get(self, request, *args, **kwargs):
            return self.retrieve(request, *args, **kwargs)

        #RetrieveModelMixin uses get_object to find just one item. To do this, it needs some help from get_queryset, which is supposed to give it a list of items to choose from, which is the queryset. (It gave me a lot of problems when I didn't override it, cuz get_queryset does give it a list, but the default get_object doesn't know how to pick just one item from that list. To fix this, update get_object so it knows how to pick a single item from the list provided by get_queryset.)
       def get_object(self):

            queryset = self.get_queryset()
            #Get single object from the queryset
            profile = get_object_or_404(queryset)
            return profile

    #    def retrieve(self, request, *args, **kwargs):
    #         print("entered retrieve")
    #         instance = self.get_object()
    #         print("Instance from get_object:", instance)  # Debug line
    #         serializer = self.get_serializer(instance)
    #         return Response(serializer.data)
   
class GetOwnProfile(mixins.RetrieveModelMixin,
                 generics.GenericAPIView):

       permission_classes = [IsAuthenticated]

       serializer_class = GetProfileSerializer

        #override queryset
       def get_queryset(self):
            print("entered get_queryset")
            user_id = self.request.user.id

            print(user_id)

            if user_id is None:
                raise PermissionDenied('No user ID!')

            appuser = AppUser.objects.get(id=user_id)
            profile = Profile.objects.filter(appuser=appuser)
            print(profile)
            if not profile.exists():
                raise Http404("Profile not found")
            return profile


       def get(self, request, *args, **kwargs):
            print("entered get")
            return self.retrieve(request, *args, **kwargs)

        #RetrieveModelMixin uses get_object to find just one item. To do this, it needs some help from get_queryset, which is supposed to give it a list of items to choose from, which is the queryset. (It gave me a lot of problems when I didn't override it, cuz get_queryset does give it a list, but the default get_object doesn't know how to pick just one item from that list. To fix this, update get_object so it knows how to pick a single item from the list provided by get_queryset.)
       def get_object(self):
            print("entered get_object")

            queryset = self.get_queryset()
            #Get single object from the queryset
            profile = get_object_or_404(queryset)
            print(profile)
            return profile


      
class GetAddRequestList(generics.ListAPIView):

        serializer_class = AddRequestListSerializer
        permission_classes = [IsAuthenticated]

        def get_queryset(self):
            user_to = self.request.user

            try:
                requests = AddRequest.objects.filter(user_to=user_to)
                return requests
            except AddRequest.DoesNotExist:
                return AddRequest.objects.none()

#Code written by me ends here

#Extra note:
#for things like def get_(something), define it myself but must follow the get_<field_name> for example def get_protein, naming pattern so that DRF knows to associate it with the associated field. This method is not explicitly called. DRF calls this method automatically when serialising an instance. When serialising an object, DRF looks at each field in the fields list.If the field is a SerializerMethodField, DRF searches for a method with the naming pattern get_<field_name> in the same serializer class. If the method exists, DRF calls it and uses its return value to populate the field.