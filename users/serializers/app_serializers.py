from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from users.models import *
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError


class OrganisationSerializer(serializers.ModelSerializer):
    class Meta: 
        model = Organisation
        fields = ["id", "name"]

class AppUserNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppUser
        fields = ["firstname", "lastname"]

class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ["id", "name"]


class UpdateProfileOrgSerializer(serializers.ModelSerializer):
    
    #this retrieves the organisation instance based on the organisation id feeds in as input in the field. Organisation.objects.all() is just saying retrieve from this set. required means user MUST provide the id. 
    #nutshell: queryset=Organisation.objects.all() is a matter with Organisation model, whereas source="appuser.organisation" is a matter with Profile.
    #organisation is an PrimaryKeyRelatedField instance. organisation is a PrimaryKeyRelatedField instance, which is a special DRF field that serializes an Organisation instance to just its id or deserializes an id to an Organisation instance. This field allows the user to update or change their associated company.
    #Note if there's no such organisation_id, DRF automatically raises a validation error before reaching the update() method
    organisation_id = serializers.PrimaryKeyRelatedField(
        queryset=Organisation.objects.all(),
        required=False,
        #commented out write_only cuz we want it to be read and write allowed as user needs to be able to see it! React side needs the repsonse data!
        # write_only=True
        allow_null=True
    )

    country_id = serializers.PrimaryKeyRelatedField(
        source="country",
        queryset=Country.objects.all(),
        required=False,
        allow_null=True
    )

    #it's important to include write_only=True as we are going to pop these from validated_data (because those fields do not belong to the Profile model), by specifying its write_only, DRF return super().update(instance, validated_data) will not throw an error when these are not in validated_data. REMEMBER first/last names are able to be edited by the user. write_only will not include these fields in the output response, so we need to override to_representation() to include them in the output.
    firstname = serializers.CharField(required=True, write_only=True)
    lastname = serializers.CharField(required=True, write_only=True)

    #we don’t need to pop("organisation_name") because read-only fields never make it into validated_data, unlike firstname and lastname, users are NOT supposed to edit this, therefore read_only.
    organisation_name = serializers.CharField(source="appuser.organisation.name", read_only=True, required=False, allow_null=True)

    #when serializing this Profile, look at profile.country (the related object), go into its .name field, and include it in the output under the key country_name
    country_name = serializers.CharField(source="country.name", read_only=True, required=False, allow_null=True)

    class Meta:
        model = Profile

        fields = ["firstname", "lastname", "aboutme", 'country_id', 'country_name', 'age', 'gender', "organisation_id", "organisation_name"]

    #Note: both PUT (full update) and PATCH (partial update) use the same update() method in the serializer. This is called within perform_update in views, UpdateMixin. 
    #overriding this is to allow the user to change their associated orgniasaitoin if they want to. 
    #instance is the profile instance here.
    def update(self, instance, validated_data):
        #remember validated_data["organisation_id"] is not an id, its an instance! DRF already resolved it to the instance, so there is no need to fetch it manually

        #important to have this safeguard to protect against null value or no organisation field in the request, causing a null value to be updated accidentally in the backend!
        #here it's important to use serializers.empty instead of None, cuz if the organisation_id field is not passed in, it will just remove organisation_id from validated data rather than putting a null value in that field, causing an accidental update to None!
        org_field = validated_data.get("organisation_id", serializers.empty)

        #track AppUser update:
        appUserUpdated = False

        if org_field is not serializers.empty and org_field is not None:
            #whether it's an Organisation instance or None, assign it
            instance.appuser.organisation = org_field
            appUserUpdated = True 

        #we need to single out these updates as these are not Profile related updates, these are on AppUser.
        if "firstname" in validated_data or "lastname" in validated_data:
            if "firstname" in validated_data:
                instance.appuser.firstname = validated_data.pop("firstname")
            if "lastname" in validated_data:
                instance.appuser.lastname = validated_data.pop("lastname")
            appUserUpdated = True 
                
        if appUserUpdated:
            instance.appuser.save()

        validated_data.pop("organisation_id", None)
            
        #we need to call thye parent ModelSerializer.update() to save all fields for Profile. Even if validated_data still includes AppUser's model's firstname, etc., they will be silently ignored
        #here, the update has already been implemented
        profile = super().update(instance, validated_data)

        #now check each “required” field manually
        fields_ok = [
            profile.aboutme is not None and profile.aboutme != "",
            profile.country is not None,
            profile.age is not None,
            profile.gender is not None and profile.gender != "NA",
            profile.appuser.firstname is not None and profile.appuser.firstname != "",
            profile.appuser.lastname is not None and profile.appuser.lastname != "",
            #organisation is optional, so no need to check it
        ]

        #all(iterable) returns True only if every item in the iterable (e.g. list) is True
        if all(fields_ok):
            profile.required_complete = True
        else:
            profile.required_complete = False

        profile.save()

        #here, we're just returning the updated profile instance, which will be serialized by DRF, go through to_representation, and returned in the response.
        return profile

    #DRF’s ModelSerializer.to_representation() just takes the model fields defined in fields and runs their serializer fields’ .to_representation() methods to build the response.
    #as we define write only for firstname and lastname, the response data would'nt include those, so we need to override to_representation to include:
    def to_representation(self, instance):
        res = super().to_representation(instance)
        #add firstname and lastname from the related AppUser to the output.
        res["firstname"] = instance.appuser.firstname
        res["lastname"] = instance.appuser.lastname
        return res


#read-only show profile
class ShowProfileOrgSerializer(serializers.ModelSerializer):

    # appuser_name = AppUserNameSerializer(source="appuser", read_only=True)
    firstname = serializers.CharField(source="appuser.firstname", read_only=True)
    lastname = serializers.CharField(source="appuser.lastname", read_only=True)
    user_id = serializers.IntegerField(source="appuser.id", read_only=True)

    organisation_id = serializers.IntegerField(source="appuser.organisation.id", read_only=True)
    organisation_name = serializers.CharField(source="appuser.organisation.name", read_only=True)

    country_id = serializers.IntegerField(source="country.id", read_only=True)
    country_name = serializers.CharField(source="country.name", read_only=True)

    class Meta:
        model = Profile
        fields = ["user_id", "firstname", "lastname", "aboutme", 'country_id', 'country_name', 'age', 'gender', "organisation_id", "organisation_name"]

class AddRequestSerializer(serializers.ModelSerializer):
        class Meta:
            model = AddRequest
            fields = ["user_from", "user_to"]
        