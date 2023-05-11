from rest_framework import viewsets, status
from rest_framework.response import Response
from settings.models import Zoom
from settings.serializers import (
    ZoomSerializer,
    ZoomUpdateSerializer,
    ZoomCreateSerializer,
)
from consultation.helper import get_deleted_time
from common.swagger.custom_documentation import swagger_wrapper
from drf_yasg import openapi
import logging


class ZoomApi(viewsets.ViewSet):
    serializer_class = ZoomSerializer
    http_method_names = ["post", "get", "delete", "put", "head", "options"]

    def list(self, request, *args, **kwargs):
        try:
            zoom = Zoom.objects.get(
                organisation=request.data.get("organisation", None), is_active=True
            )
            return Response(
                {
                    "status": 200,
                    "message": "Zoom keys info",
                    "data": self.serializer_class(zoom).data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as err:
            logging.error(f"ZoomtApi list: {err}", exc_info=True)
            return Response(
                {
                    "status": 200,
                    "message": "Zoom keys info",
                    "data": [],
                },
                status=status.HTTP_200_OK,
            )

    @swagger_wrapper(
        {
            "api_key": openapi.TYPE_STRING,
            "secret_key": openapi.TYPE_STRING,
        }
    )
    def create(self, request, *args, **kwargs):
        if (
            Zoom.objects.filter(
                organisation=request.data.get("organisation"), is_active=True
            ).count()
            >= 1
        ):
            return Response(
                {
                    "status": 400,
                    "message": "Zoom keys already exist",
                    "data": [],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        request.data["created_by"] = request.data.get("user_id")
        serializer = ZoomCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "status": 201,
                    "message": "Zoom keys created",
                    "data": serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {
                "status": 400,
                "message": "Invalid info",
                "data": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    @swagger_wrapper(
        {
            "api_key": openapi.TYPE_STRING,
            "secret_key": openapi.TYPE_STRING,
        }
    )
    def update(self, request, *args, **kwargs):
        try:
            zoom = Zoom.objects.get(
                id=kwargs.get("pk", None),
                organisation=request.data.get("organisation", None),
                is_active=True,
            )
            request.data["updated_by"] = request.data.get("user_id")
            serializer = ZoomUpdateSerializer(zoom, request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(
                    {
                        "status": 200,
                        "message": "Zoom keys updated",
                        "data": serializer.data,
                    },
                    status=status.HTTP_200_OK,
                )
            return Response(
                {
                    "status": 400,
                    "message": "Invalid data",
                    "data": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as err:
            logging.error(f"ZoomtApi update: {err}", exc_info=True)
            return Response(
                {"status": 400, "message": "Zoom keys not found", "data": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def destroy(self, request, *args, **kwargs):
        try:
            zoom = Zoom.objects.get(
                id=kwargs.get("pk", None),
                organisation=request.data.get("organisation", None),
                is_active=True,
            )
            zoom.is_active = False
            zoom.deleted_by = request.data.get("user_id")
            zoom.deleted_at = get_deleted_time()
            zoom.save()
            return Response(
                {"status": 200, "message": "Zoom keys deleted", "data": []},
                status=status.HTTP_200_OK,
            )
        except Exception as err:
            logging.error(f"ZoomtApi destroy: {err}", exc_info=True)
            return Response(
                {"status": 400, "message": "Zoom keys not found", "data": []},
                status=status.HTTP_400_BAD_REQUEST,
            )
