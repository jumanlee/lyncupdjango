from django.contrib import admin

# Register your models here.

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import *

class CustomUserAdmin(UserAdmin):
    model = AppUser

    #what fields to display
    list_display = ('id', 'email', 'username', 'firstname', 'lastname', 'is_staff', 'is_active')

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

admin.site.register(AppUser, CustomUserAdmin)
admin.site.register(Like, LikeAdmin)
