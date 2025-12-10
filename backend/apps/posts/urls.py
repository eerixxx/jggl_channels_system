"""Posts URL configuration."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ChannelPostViewSet, MultiChannelPostViewSet

app_name = "posts"

router = DefaultRouter()
router.register(r"multi", MultiChannelPostViewSet, basename="multi-post")
router.register(r"channel", ChannelPostViewSet, basename="channel-post")

urlpatterns = [
    path("", include(router.urls)),
]

