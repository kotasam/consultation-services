"""worke_consultation_service URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from consultation.urls import urlpatterns as consultation_url_pattern
from settings.urls import urlpatterns as settings_url_pattern
from common.swagger.views import schema_view


urlpatterns = (
    [
        # path("admin/", admin.site.urls),
        path(
            "consultations/docs/",
            schema_view.with_ui("swagger", cache_timeout=0),
            name="schema-swagger-ui",
        ),
    ]
    + consultation_url_pattern
    + settings_url_pattern
)

urlpatterns += [path("consultations/silk/", include("silk.urls", namespace="silk"))]
urlpatterns += [
    path("consultations/prometheus-worke/", include("django_prometheus.urls"))
]
