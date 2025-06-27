from django.contrib import admin

# Register your models here.

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import *

class CustomUserAdmin(UserAdmin):
    model = AppUser

    list_display = (
        'id', 'email', 'username', 'firstname', 'lastname',
        'organisation', 'is_staff', 'is_active', 'is_verified'
    )
    list_filter = ('is_staff', 'is_active', 'is_verified')
    search_fields = ('email', 'username', 'firstname', 'lastname')
    ordering = ('email',)

    #override add_fieldsets, used when creating a new user
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'username', 'firstname', 'lastname',
                'password1', 'password2',
                'is_staff', 'is_active', 'is_verified',
            ),
        }),
    )

    #override fieldsetsused when editing an existing user
    fieldsets = (
        (None, {
            'fields': ('email', 'password'),
        }),
        ('Personal info', {
            'fields': ('username', 'firstname', 'lastname'),
        }),
        ('Permissions', {
            'fields': (
                'is_active', 'is_staff', 'is_superuser', 'is_verified', 
                'groups', 'user_permissions',
            ),
        }),
        ('Important dates', {
            'fields': ('last_login',),
        }),
    )

class LikeAdmin(admin.ModelAdmin):
    model = Like
    list_display = ('id', 'user_from', 'user_to', 'like_count', 'last_like_date') 
    list_filter = ('last_like_date',) 
    search_fields = ('user_from__email', 'user_to__email')  

class ProfileAdmin(admin.ModelAdmin):
    model = Profile
    list_display = ('id', 'appuser', "aboutme", 'country', 'age', 'gender', 'required_complete')
    list_filter = ('gender', 'country')
    search_fields = ('appuser__email', 'appuser__username', 'country')

class OrganisationAdmin(admin.ModelAdmin):
    model = Organisation
    list_display = ('id', 'name', 'country', 'date_created')
    search_fields = ('name', 'country')

class CountryAdmin(admin.ModelAdmin):
    model = Country
    list_display = ('id', 'name')
    search_fields = ('name',)


admin.site.register(AppUser, CustomUserAdmin)
admin.site.register(Like, LikeAdmin)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(Organisation, OrganisationAdmin)
admin.site.register(Country, CountryAdmin)
