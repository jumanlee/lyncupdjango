from rest_framework import serializers
from .models import *

#Code written by me
class RegisterSerializer(serializers.ModelSerializer):

    #write only ensures the field can only be written in but not read from. This is to ensure security
    password = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = AppUser

        fields = ['email', 'username', 'firstname', 'lastname', 'password', 'password2']

        #make them all required
        extra_kwargs = {
            'firstname': {'required': True},
            'lastname': {'required': True},
            'username': {'required': True},
            'email': {'required': True},
        }

    def create(self, validated_data):

        #after .pop(), validated_data doesn't contain the password2 property anymore, instead it's been moved to the password2 variable.
        password2 = validated_data.pop('password2')

        #I want to retain password because this argument needs to be passed in to create_user, which will run set_password(passed password) within it. 
        password = validated_data.get('password')

        if password == None or password2 == None:
            raise ValueError("No password entered!")

        if password != password2:
            raise ValueError("passwords do not match!")

        # the objects attribute is a manager object that is automatically created for every model. The objects attribute provides a set of methods that can be used to query the database for objects of the model.
        # create_user() method is not a built-in Django method, but rather a custom method that is defined in the AppUserManager class.
        appuser = AppUser.objects.create_user(**validated_data)
        # appuser.set_password(password)
        appuser.save()

        #now create the associated profile object
        profile = Profile.objects.create(appuser=appuser)

        return appuser
   
class AddRequestSerializer(serializers.ModelSerializer):

    class Meta:
        model = AddRequest

        #Note that when working with ForeignKeys, e.g. 'user_to', they are represented as model instances in python code. But when you serialise a model, the ForeignKey is usually serialised to the ID of the related object.

        #Note even though I don't plan for the client to send "user from" id from the client react app, (this is handled dynamically in the views.py component), this field is still necessary because the serialiser needs to know it should look for it in the data dictionary when saving the model.

        fields = ['user_from' , 'user_to']

        def create(self, validated_data):
            addRequest = AddRequest.objects.create(**validated_data)
            addRequest.save()
            return addRequest


class AppUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppUser
        fields = ['id', 'firstname', 'lastname']

class AddRequestListSerializer(serializers.ModelSerializer):

    user_from = serializers.SerializerMethodField()

    class Meta:
        model = AddRequest

        fields = ['user_from', 'date_time']

    def get_user_from(self, obj):

        user_from_instance = AppUser.objects.filter(id=obj.user_from.id)
        return AppUserSerializer(user_from_instance, many=True).data


class FriendListSerializer(serializers.ModelSerializer):

    #it's necessary to include many=True to signal to DRF that we are expecting a list of data (many). And I only want it to be read only for security reasons!
    appfriends = AppUserSerializer(many=True, read_only=True)

    class Meta:
        model = Friendship
        fields = ['appfriends']

class SearchUserSerializer(serializers.ModelSerializer):

    class Meta:
        model = AppUser
        fields = ['id', 'firstname', 'lastname']


class UpdateStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['status']


class UpdateBioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['aboutme', 'citytown', 'country', 'age', 'gender']


class GetProfileSerializer(serializers.ModelSerializer):

    appuser = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ['appuser', 'status', 'aboutme', 'citytown', 'country', 'age', 'gender']


    def get_appuser(self, obj):

        user_instance = AppUser.objects.filter(id=obj.appuser.id)
        return AppUserSerializer(user_instance, many=True).data

# class LikeSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Like
#         fields = ['user_from', 'user_to', 'like_count', 'last_like_date']

#my code ends here









