"""Monitoring URL configuration."""

from django.urls import path

from .views import celery_status, health, ready, status_view

app_name = "monitoring"

urlpatterns = [
    path("health/", health, name="health"),
    path("ready/", ready, name="ready"),
    path("status/", status_view, name="status"),
    path("celery/", celery_status, name="celery"),
]

