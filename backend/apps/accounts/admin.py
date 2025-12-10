"""Accounts admin configuration."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

# Customize the User admin if needed
# admin.site.unregister(User)
# admin.site.register(User, CustomUserAdmin)

