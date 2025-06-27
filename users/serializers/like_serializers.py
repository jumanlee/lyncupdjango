from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from users.models import *
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

class LikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Like
        #we only need the person that is liked. 
        fields = ['user_to']