from django.contrib import admin

# Register your models here.

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import *

class CustomUserAdmin(UserAdmin):
    model = AppUser

    #what fields to display
    list_display = ('id', 'email', 'username', 'firstname', 'lastname', 'organisation', 'is_staff', 'is_active')

    #what fields to filter by in the admin panel
    list_filter = ('is_staff', 'is_active')

    #searchable fields in the admin panel
    search_fields = ('email', 'username', 'firstname', 'lastname')

    #specify the ordering of users
    ordering = ('email',)

class LikeAdmin(admin.ModelAdmin):
    model = Like
    list_display = ('id', 'user_from', 'user_to', 'like_count', 'last_like_date') 
    list_filter = ('last_like_date',) 
    search_fields = ('user_from__email', 'user_to__email')  

class ProfileAdmin(admin.ModelAdmin):
    model = Profile
    list_display = ('id', 'appuser', "citytown", "aboutme", 'country', 'age', 'gender')
    list_filter = ('gender', 'country')
    search_fields = ('appuser__email', 'appuser__username', 'citytown', 'country')

class OrganisationAdmin(admin.ModelAdmin):
    model = Organisation
    list_display = ('id', 'name', 'citytown', 'country', 'date_created')
    search_fields = ('name', 'citytown', 'country')


admin.site.register(AppUser, CustomUserAdmin)
admin.site.register(Like, LikeAdmin)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(Organisation, OrganisationAdmin)
