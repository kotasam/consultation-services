from django.urls import path, include
from rest_framework.routers import DefaultRouter
from consultation.views.category_views import CategoryApi
from consultation.views.consultation_views import ConsultationApi
from consultation.views.appointment_views import (
    AppointmentApi,
    AppointmentRescheduleApi,
)
from consultation.views.end_user_views import (
    EndUserAppointmentsApi,
    EndUserCategoryApi,
    EndUserConsultationApi,
    EndUserConsultationByIdApi,
)


router = DefaultRouter()
router.register("category", CategoryApi, "Category")
router.register("consultations", ConsultationApi, "Consultation")
router.register("appointments", AppointmentApi, "Appointment")
router.register(
    "appointments/reschedule", AppointmentRescheduleApi, "Appointment Reschedule"
)


end_user_router = DefaultRouter()
end_user_router.register("category", EndUserCategoryApi, "Category")
end_user_router.register("consultations", EndUserConsultationApi, "Consultations")
end_user_router.register("appointments", EndUserAppointmentsApi, "Appointment")
end_user_router.register("consultation", EndUserConsultationByIdApi, "Consultation")


urlpatterns = [
    path("consultations/", include(router.urls)),
    path("consultations/end_user/", include(end_user_router.urls)),
]
