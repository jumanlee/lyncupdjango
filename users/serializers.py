from rest_framework import serializers
from .models import *

#ths RegisterSerializer code is originally written by me but taken from my own project for Advanced Web Develoopment
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

    # .create() method in serializer is called when serializer.save() is executed inside perform_create() in views.py.
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


class LikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Like
        #we only need the person that is liked. 
        fields = ['user_to']


class OrganisationSerializer(serializers.ModelSerializer):
    class Meta: 
        model = Organisation
        fields = ["name", "description"]

class AppUserNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppUser
        fields = ["firstname", "lastname"]


class UpdateProfileOrgSerializer(serializers.ModelSerializer):
    
    #this retrieves the organisation instance based on the organisation id feeds in as input in the field. Organisation.objects.all() is just saying retrieve from this set. required means user MUST provide the id. 
    #nutshell: queryset=Organisation.objects.all() is a matter with Organisation model, whereas source="appuser.organisation" is a matter with Profile.
    #organisation is an PrimaryKeyRelatedField instance. organisation is a PrimaryKeyRelatedField instance, which is a special DRF field that serializes an Organisation instance to just its id or deserializes an id to an Organisation instance. This field allows the user to update or change their associated company.
    organisation_id = serializers.PrimaryKeyRelatedField(
        queryset=Organisation.objects.all(),
        required=False,
        write_only=True
    )

    #read only cuz I don't want users to change the company's details!
    organisation_details = OrganisationSerializer(source="appuser.organisation", read_only=True)

    #appuser is a foreign key field in Profile
    appuser_name = AppUserNameSerializer(source="appuser")

    class Meta:
        model = Profile

        fields = ["appuser_name", "aboutme", 'citytown', 'country', 'age', 'gender', "organisation_id", "organisation_details"]

    #Note: both PUT (full update) and PATCH (partial update) use the same update() method in the serializer. This is called within perform_update in views, UpdateMixin. 
    #overriding this is to allow the user to change their associated orgniasaitoin if they want to. 
    #instance is the profile instance here.
    def update(self, instance, validated_data):
        if "organisation_id" in validated_data:
            # #can just directly assign organisation_id (note, DRF has already resolved organisation_id  to an Organisation instance at this point) cuz remember, this is from validated_data, and organisation_id is a serializers.PrimaryKeyRelatedField, so this has been verified.
            # instance.appuser.organisation = organisation
            instance.appuser.organisation = validated_data["organisation_id"]
            instance.appuser.save()
            
        #we need to call thye parent ModelSerializer.update() to save all fields, not just the organisation saved above!
        return super().update(instance, validated_data)

#read-only show profile
class ShowProfileOrgSerializer(serializers.ModelSerializer):

    organisation_details = OrganisationSerializer(source="appuser.organisation", read_only=True)

    appuser_name = AppUserNameSerializer(source="appuser", read_only=True)

    class Meta:
        model = Profile

        fields = ["appuser_name", "aboutme", 'citytown', 'country', 'age', 'gender', "organisation_details"]
















