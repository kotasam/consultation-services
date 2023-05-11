from rest_framework import viewsets, status
from rest_framework.response import Response
from consultation.models import Category
from consultation.serializers import CategorySerializer, CategoryListSerializer
from consultation.helper import get_deleted_time, getSerializerError, check_name
from common.swagger.custom_documentation import swagger_wrapper
from drf_yasg import openapi
import logging


class CategoryApi(viewsets.ViewSet):
    serializer_class = CategorySerializer
    http_method_names = ["post", "get", "delete", "put", "head", "options"]

    def list(self, request, *args, **kwargs):
        categories_list = Category.objects.filter(
            organisation=request.data.get("organisation", None), is_active=True
        )
        return Response(
            {
                "status": 200,
                "message": "categories info",
                "data": CategoryListSerializer(categories_list, many=True).data,
            },
            status=status.HTTP_200_OK,
        )

    @swagger_wrapper(
        {
            "name": openapi.TYPE_STRING,
            "description": openapi.TYPE_STRING,
            "image": openapi.TYPE_STRING,
        }
    )
    def create(self, request, *args, **kwargs):
        try:
            Category.objects.get(
                name=request.data["name"],
                organisation=request.data.get("organisation"),
                is_active=True,
            )
            return Response(
                {
                    "status": 400,
                    "message": "Category already exixts",
                    "data": "",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as err:
            pass

        error = check_name(request.data.get("name"))
        if error:
            return Response(
                {"status": 400, "message": "Invalid name", "data": []},
                status=status.HTTP_400_BAD_REQUEST,
            )

        request.data["created_by"] = request.data.get("user_id")
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "status": 201,
                    "message": "Category created",
                    "data": serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(
            {
                "status": 400,
                "message": getSerializerError(serializer.errors),
                "data": "",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    @swagger_wrapper(
        {
            "name": openapi.TYPE_STRING,
            "description": openapi.TYPE_STRING,
            "image": openapi.TYPE_STRING,
        }
    )
    def update(self, request, *args, **kwargs):
        try:
            category = Category.objects.get(
                id=kwargs.get("pk"),
                organisation=request.data.get("organisation", None),
                is_active=True,
            )
            if "name" in request.data:
                try:
                    category_obj = Category.objects.get(
                        name=request.data["name"],
                        organisation=request.data.get("organisation"),
                        is_active=True,
                    )
                    if category.id != category_obj.id:
                        return Response(
                            {"error": "Category already exixts"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                except Exception:
                    pass

            request.data["updated_by"] = request.data.get("user_id")
            serializer_data = self.serializer_class(
                category, request.data, partial=True
            )
            if serializer_data.is_valid():
                serializer_data.save()
                return Response(
                    {
                        "status": 200,
                        "message": "category info updated",
                        "data": serializer_data.data,
                    },
                    status=status.HTTP_200_OK,
                )
            return Response(
                {
                    "status": 400,
                    "message": "Invalid payload",
                    "data": getSerializerError(serializer_data.errors),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as err:
            logging.error(f"CategoryApi update: {err}", exc_info=True)
            return Response(
                {"status": 400, "message": "category not found", "data": []},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def destroy(self, request, *args, **kwargs):
        try:
            category = Category.objects.get(
                id=kwargs.get("pk"),
                organisation=request.data.get("organisation", None),
                is_active=True,
            )
            category.is_active = False
            category.deleted_by = request.data.get("user_id")
            category.deleted_at = get_deleted_time()
            category.save()
            return Response(
                {"status": 200, "message": "category deleted", "data": []},
                status=status.HTTP_200_OK,
            )
        except Exception as err:
            logging.error(f"CategoryApi destroy: {err}", exc_info=True)
            return Response(
                {"status": 400, "message": "category not found", "data": []},
                status=status.HTTP_400_BAD_REQUEST,
            )
