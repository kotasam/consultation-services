from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

schema_view = get_schema_view(
    openapi.Info(
        title="Consultation Service API",
        default_version="v1",
        description="Consultation Service API Documentation ",
        terms_of_service="https://www.worke.com/policies/terms/",
        contact=openapi.Contact(email="workathon@snippets.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)
