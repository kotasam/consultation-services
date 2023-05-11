from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


def swagger_wrapper(fields):
    documentation = swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={field: openapi.Schema(type=fields[field]) for field in fields},
        )
    )
    return documentation


# Swagger documentation for consultation creation :
consultation_api_documentation = swagger_auto_schema(
    operation_description="Consultation Create/Update API",
    responses={400: "Bad Request", 200: "Success"},
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "name": openapi.Schema(type=openapi.TYPE_STRING),
            "description": openapi.Schema(type=openapi.TYPE_STRING),
            "image": openapi.Schema(type=openapi.TYPE_STRING),
            "duration": openapi.Schema(type=openapi.TYPE_STRING),
            "is_staff_enabled": openapi.Schema(type=openapi.TYPE_BOOLEAN),
            "category_id": openapi.Schema(type=openapi.TYPE_STRING),
            "consultation_data": openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Items(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "id": openapi.Schema(type=openapi.TYPE_STRING),
                        "mode": openapi.Schema(type=openapi.TYPE_STRING),
                        "price": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "discount_type": openapi.Schema(type=openapi.TYPE_STRING),
                        "discount_value": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "status": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    },
                ),
            ),
            "staff_data": openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Items(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "id": openapi.Schema(type=openapi.TYPE_STRING),
                        "staff_id": openapi.Schema(type=openapi.TYPE_STRING),
                        "mode": openapi.Schema(type=openapi.TYPE_STRING),
                        "staff_special_price": openapi.Schema(
                            type=openapi.TYPE_INTEGER
                        ),
                        "status": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    },
                ),
            ),
        },
    ),
)

# Swagger documentation for organisation query param
organisation = openapi.Parameter(
    "organisation", openapi.IN_QUERY, type=openapi.TYPE_STRING
)

# Swagger documentation for category_id query param
category_id = openapi.Parameter(
    "category_id", openapi.IN_QUERY, type=openapi.TYPE_STRING
)

# Swagger documentation for category_id query param
consultation_id = openapi.Parameter(
    "consultation_id", openapi.IN_QUERY, type=openapi.TYPE_STRING
)

# Swagger documentation for Pagination
page_param = openapi.Parameter("page", openapi.IN_QUERY, type=openapi.TYPE_INTEGER)
offset_param = openapi.Parameter("offset", openapi.IN_QUERY, type=openapi.TYPE_INTEGER)
