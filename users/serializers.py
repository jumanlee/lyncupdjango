from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import *
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError


#ths RegisterSerializer code is originally written by me but taken from my own project for Advanced Web Develoopment
class RegisterSerializer(serializers.ModelSerializer):

    #write only ensures the field can only be written in but not read from. This is to ensure security
    #by default, become required
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

        #password2 not needed, destroy it
        validated_data.pop('password2', None)

        password = validated_data.pop('password')

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

    def validate_password(self, value):

        try:
            #user can be None or actual user if needed
            validate_password(value, user=None)  
        except DjangoValidationError as exc:
            #frontend expects "detail" key, added to the error message
            raise serializers.ValidationError(exc.messages)
        return value

    def validate_email(self, email):
        return email.strip().lower()

    def validate(self, attrs):
        #cross-field check
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({
                'detail': 'Passwords must match.'
            })
        return attrs


class EmailSerializer(serializers.Serializer):
    email = serializers.EmailField()

class PasswordResetConfirmSerializer(serializers.Serializer):
    #field-level validation, runs Django's AUTH_PASSWORD_VALIDATORS.
    #any failures raise a ValidationError with a list of messages.

    uidb64 = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(
        min_length=8,
        write_only=True,
        error_messages={
            'min_length': 'Password must be at least 8 characters long.'
        }
    )

    #Field-level validation runs first. DRF calls any validate_<fieldname>(…) methods and checks built-in validators (e.g. new_password = serializers.CharField as defined above) on each field (e.g  validate_new_password)
    #CharField is checked first, then validate_new_password is called.
    #Once every field is individually valid, DRF collects them into a single dictionary attrs
    #DRF then calls validate(self, attrs) with that dict, attrs is that dict.

    def validate_new_password(self, value):
        #don’t need to manually redo the CharField checks (like min_length) inside custom validate_new_password() method because DRF runs them automatically before calling that method
        try:
            #user can be None or actual user if needed
            validate_password(value, user=None)  
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)
        return value
    
    ##optional, def validate method can be commented out, unless we need to do someting with the attrs dict like corss field validation
    # def validate(self, attrs):
    #     return attrs

class ChangePasswordAuthenticatedSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value

    def validate_new_password(self, value):
        user = self.context['request'].user
        try:
            validate_password(value, user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)
        return value

    def validate(self, attrs):
        #cross-field check
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({
                'detail': 'Passwords must match.'
            })
        #remove confirm_password from attrs dict, as we don't want to save it in the database, keeping  it from reaching view, keeping it tidy.
        attrs.pop("confirm_password", None) 
        return attrs

    

#for use in SIMPLE_JWT["TOKEN_OBTAIN_SERIALIZER"] in settings.py
#in DRF serializers, attrs is just the dictionary of input fields after they’ve passed individual field validation. In the case of the token-obtain endpoint, those fields are credentials e.g. an email/username and a password.
class VerifiedTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        if not self.user.is_verified:
            raise serializers.ValidationError("Email not verified.")
        return data


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

        fields = ["firstname", "lastname", "aboutme", 'citytown', 'country_id', 'country_name', 'age', 'gender', "organisation_id", "organisation_name"]

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
        return super().update(instance, validated_data)

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
        fields = ["user_id", "firstname", "lastname", "aboutme", 'citytown', 'country_id', 'country_name', 'age', 'gender', "organisation_id", "organisation_name"]

class AddRequestSerializer(serializers.ModelSerializer):
        class Meta:
            model = AddRequest
            fields = ["user_from", "user_to"]
        


















