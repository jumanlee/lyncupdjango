from rest_framework import serializers
from .models import *

#ths RegisterSerializer code is originally written by me but taken from my own project for Advanced Web Develoopment
class RegisterSerializer(serializers.ModelSerializer):

    #write only ensures the field can only be written in but not read from. This is to ensure security
    password = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)

    # #the serializer will take that id, find the corresponding Organisation in the database and assign it to the AppUser
    # organisation_id = serializers.PrimaryKeyRelatedField(
    #     queryset=Organisation.objects.all(),
    #     required=False,
    #     write_only=True
    # )

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

        #Don't retain the password, handle this separately, as we need to hash it.
        password = validated_data.pop('password')

        if not password or not password2:
            raise serializers.ValidationError({"password": "No password entered!"})

        if password != password2:
            raise serializers.ValidationError({"password2": "Passwords do not match!"})

        # the objects attribute is a manager object that is automatically created for every model. The objects attribute provides a set of methods that can be used to query the database for objects of the model.
        # create_user() method is not a built-in Django method, but rather a custom method that is defined in the AppUserManager class.
        #can't do appuser = AppUser.objects.create_user(**validated_data) as we've already popped the password, hence need to manually input:
        appuser = AppUser.objects.create_user(
            email=validated_data["email"],
            username=validated_data['username'],
            #password doesn't need set_password to hash as AppUserManager's create_user already does it for us. set_password is only needed if we save password outside create_user
            password=password,
            firstname=validated_data['firstname'],
            lastname=validated_data['lastname'],
        )

        #the below not needed anymore as we are putting it in create_user above
        # #properly hash password
        # appuser.set_password(password)
        # appuser.save()

        #now create the associated profile object
        Profile.objects.create(appuser=appuser)

        return appuser


class LikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Like
        #we only need the person that is liked. 
        fields = ['user_to']


class OrganisationSerializer(serializers.ModelSerializer):
    class Meta: 
        model = Organisation
        fields = ["id", "name"]

class AppUserNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppUser
        fields = ["firstname", "lastname"]


class UpdateProfileOrgSerializer(serializers.ModelSerializer):
    
    #this retrieves the organisation instance based on the organisation id feeds in as input in the field. Organisation.objects.all() is just saying retrieve from this set. required means user MUST provide the id. 
    #nutshell: queryset=Organisation.objects.all() is a matter with Organisation model, whereas source="appuser.organisation" is a matter with Profile.
    #organisation is an PrimaryKeyRelatedField instance. organisation is a PrimaryKeyRelatedField instance, which is a special DRF field that serializes an Organisation instance to just its id or deserializes an id to an Organisation instance. This field allows the user to update or change their associated company.
    #Note if there's no such organisation_id, DRF automatically raises a validation error before reaching the update() method
    organisation_id = serializers.PrimaryKeyRelatedField(
        queryset=Organisation.objects.all(),
        required=False,
        #commented out write_only cuz we want it to be read and write allowed as user needs to be able to see it!
        # write_only=True
    )

    firstname = serializers.CharField(required=True)
    lastname = serializers.CharField(required=True)

    organisation_name = serializers.CharField(source="appuser.organisation.name", read_only=True)

    class Meta:
        model = Profile

        fields = ["firstname", "lastname", "aboutme", 'citytown', 'country', 'age', 'gender', "organisation_id", "organisation_name"]

    #Note: both PUT (full update) and PATCH (partial update) use the same update() method in the serializer. This is called within perform_update in views, UpdateMixin. 
    #overriding this is to allow the user to change their associated orgniasaitoin if they want to. 
    #instance is the profile instance here.
    def update(self, instance, validated_data):
        if "organisation_id" in validated_data:
            try:
                #remember validated_data["organisation_id"] is not an id, its an instance! DRF already resolved it to the instance, so there is no need to fetch it manually
                instance.appuser.organisation = validated_data["organisation_id"]
                instance.appuser.save()
            except Organisation.DoesNotExist:
                raise serializers.ValidationError({"organisation_id": "Invalid organisation ID"})

        if "firstname" in validated_data or "lastname" in validated_data:
            if "firstname" in validated_data:
                instance.appuser.firstname = validated_data["firstname"]
            if "lastname" in validated_data:
                instance.appuser.lastname = validated_data["lastname"]
            instance.appuser.save()
            
        #we need to call thye parent ModelSerializer.update() to save all fields, not just the organisation saved above!
        return super().update(instance, validated_data)

#read-only show profile
class ShowProfileOrgSerializer(serializers.ModelSerializer):

    # organisation_details = OrganisationSerializer(source="appuser.organisation", read_only=True)

    # appuser_name = AppUserNameSerializer(source="appuser", read_only=True)
    firstname = serializers.CharField(source="appuser.firstname", read_only=True)
    lastname = serializers.CharField(source="appuser.lastname", read_only=True)

    organisation_id = serializers.IntegerField(source="appuser.organisation.id", read_only=True)
    organisation_name = serializers.CharField(source="appuser.organisation.name", read_only=True)


    class Meta:
        model = Profile
        fields = ["firstname", "lastname", "aboutme", 'citytown', 'country', 'age', 'gender', "organisation_id", "organisation_name"]
















