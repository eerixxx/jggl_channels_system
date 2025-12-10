"""Account models - extends Django's built-in User model if needed."""

from django.contrib.auth.models import AbstractUser
from django.db import models


# If you need custom user model, uncomment and modify:
# class User(AbstractUser):
#     """
#     Custom user model for the application.
#     """
#     pass

# For now, we use Django's built-in User model
# from django.contrib.auth.models import User

