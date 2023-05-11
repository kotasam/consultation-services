from django.urls import path, include
from rest_framework.routers import DefaultRouter
from settings.views.zoom_views import ZoomApi


router = DefaultRouter()
router.register("consultations/zoom", ZoomApi, "Zoom")


urlpatterns = [path("", include(router.urls))]
