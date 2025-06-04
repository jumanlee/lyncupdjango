from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from users.models import *
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




















