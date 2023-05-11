from rest_framework import serializers
from settings.models import Zoom


class ZoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Zoom
        fields = ["id", "api_key", "secret_key", "organisation", "status", "is_active"]


class ZoomCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Zoom
        fields = ["api_key", "secret_key", "organisation", "created_by"]


class ZoomUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Zoom
        fields = ["api_key", "secret_key", "status", "updated_by"]
