from django.contrib import admin

# Register your models here.

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import AppUser

class CustomUserAdmin(UserAdmin):
    model = AppUser

    #what fields to display
    list_display = ('email', 'username', 'firstname', 'lastname', 'is_staff', 'is_active')

    #what fields to filter by in the admin panel
    list_filter = ('is_staff', 'is_active')

    #searchable fields in the admin panel
    search_fields = ('email', 'username', 'firstname', 'lastname')

    #specify the ordering of users
    ordering = ('email',)

admin.site.register(AppUser, CustomUserAdmin)
