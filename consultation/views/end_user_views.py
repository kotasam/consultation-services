from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.pagination import PageNumberPagination
from consultation.models import Consultation, Appointment, Category
from consultation.serializers import (
    AppointmentSerializer,
    ConsultationSerializer,
    CategorySerializer,
)
from consultation.helper import (
    check_appointment_payload,
    generate_booking_id,
    check_slot,
    get_end_user_payable,
)
from consultation.tasks import (
    appointment_background_task,
    endUserAppointmentRescheduleBackgroundTask,
)
from common.swagger.custom_documentation import (
    organisation,
    category_id,
    swagger_wrapper,
    page_param,
    offset_param,
    consultation_id,
)
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from worke_consultation_service.config import config as cfg
from math import ceil
import logging


class EndUserCategoryApi(viewsets.ViewSet):
    permission_classes = (AllowAny,)
    serializer_class = CategorySerializer
    http_method_names = ["get", "head", "options"]

    @swagger_auto_schema(
        manual_parameters=[
            organisation,
        ]
    )
    def list(self, request, *args, **kwargs):
        organisation = self.request.query_params.get("organisation")
        if organisation is None:
            return Response(
                {
                    "status": 400,
                    "message": "Invalid organisation",
                    "data": [],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        categories_list = Category.objects.filter(
            organisation=organisation, is_active=True, status=True
        )
        return Response(
            {
                "status": 200,
                "message": "categories info",
                "data": self.serializer_class(categories_list, many=True).data,
            },
            status=status.HTTP_200_OK,
        )


class EndUserConsultationApi(viewsets.ViewSet):
    permission_classes = (AllowAny,)
    serializer_class = ConsultationSerializer
    http_method_names = ["get", "head", "options"]

    @swagger_auto_schema(manual_parameters=[organisation, category_id])
    def list(self, request, *args, **kwargs):
        organisation = self.request.query_params.get("organisation", None)
        category_id = self.request.query_params.get("category_id", None)
        if organisation is None:
            return Response(
                {
                    "status": 400,
                    "message": "Invalid organisation",
                    "data": [],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if category_id is None:
            consultations_list = Consultation.objects.filter(
                organisation=organisation,
                is_active=True,
                status=True,
            )
        else:
            consultations_list = Consultation.objects.filter(
                category_id=category_id,
                organisation=organisation,
                is_active=True,
                status=True,
            )
        return Response(
            {
                "status": 200,
                "message": "consultations info",
                "data": self.serializer_class(consultations_list, many=True).data,
            },
            status=status.HTTP_200_OK,
        )


class EndUserConsultationByIdApi(viewsets.ViewSet):
    permission_classes = (AllowAny,)
    serializer_class = ConsultationSerializer
    http_method_names = ["get", "head", "options"]

    @swagger_auto_schema(manual_parameters=[organisation, consultation_id])
    def list(self, request, *args, **kwargs):
        try:
            organisation = self.request.query_params.get("organisation", None)
            consultation_id = self.request.query_params.get("consultation_id", None)
            if organisation is None:
                return Response(
                    {
                        "status": 400,
                        "message": "Invalid organisation",
                        "data": [],
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if consultation_id is None:
                return Response(
                    {
                        "status": 400,
                        "message": "Invalid consultation",
                        "data": [],
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            consultation = Consultation.objects.get(
                id=consultation_id,
                organisation=organisation,
                is_active=True,
                status=True,
            )
            return Response(
                {
                    "status": 200,
                    "message": "consultation info",
                    "data": self.serializer_class(consultation).data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as err:
            logging.error(f"EndUserConsultationApi retrieve: {err}", exc_info=True)
            return Response(
                {"status": 400, "message": "Consultation not found", "data": []},
                status=status.HTTP_400_BAD_REQUEST,
            )


class EndUserAppointmentsApi(viewsets.ViewSet):
    serializer_class = AppointmentSerializer
    http_method_names = ["get", "post", "put", "head", "options"]

    @swagger_auto_schema(manual_parameters=[page_param, offset_param])
    def list(self, request, *args, **kwargs):
        appointments_list = Appointment.objects.filter(
            customer_id=request.data.get("user_id", None),
            organisation=request.data.get("organisation", None),
            is_active=True,
        ).order_by("-created_at")
        page = int(self.request.query_params.get(page_param.name, 0))
        offset = int(self.request.query_params.get(offset_param.name, 10))
        if page > 0:
            pagination = PageNumberPagination()
            pagination.page_size = offset
            pagination.page_query_param = cfg.get("common", "PAGE")
            query_set = pagination.paginate_queryset(
                queryset=appointments_list, request=request
            )
            appointments_serializer = self.serializer_class(query_set, many=True)
            pagination_response = pagination.get_paginated_response(
                appointments_serializer.data
            )
            pagination_response.data["count"] = ceil(
                pagination_response.data["count"] / offset
            )
            pagination_response.data["status"] = 200
            pagination_response.data["message"] = "Appointments info"
            pagination_response.data["data"] = pagination_response.data["results"]
            pagination_response.data["page"] = page
            del pagination_response.data["results"]
            return pagination_response
        return Response(
            {
                "status": 200,
                "message": "appointments info",
                "data": self.serializer_class(appointments_list, many=True).data,
            },
            status=status.HTTP_200_OK,
        )

    @swagger_wrapper(
        {
            # "customer_name": openapi.TYPE_STRING,
            # "email": openapi.TYPE_STRING,
            # "phone_number": openapi.TYPE_STRING,,
            "consultation_id": openapi.TYPE_STRING,
            "staff_id": openapi.TYPE_STRING,
            "date": openapi.TYPE_STRING,
            "slot": openapi.TYPE_STRING,
            "meeting_type": openapi.TYPE_STRING,
            "customer_address_id": openapi.TYPE_STRING,
            "org_address_id": openapi.TYPE_STRING,
            "notes": openapi.TYPE_STRING,
            "payment_mode": openapi.TYPE_STRING,
            "is_paid": openapi.TYPE_BOOLEAN,
            "terms_conditions": openapi.TYPE_BOOLEAN,
        }
    )
    def create(self, request, *args, **kwargs):
        if request.data.get("consultation_id") is None:
            return Response(
                {
                    "status": 400,
                    "message": "Please provide consultation_id",
                    "data": [],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            consultation = Consultation.objects.get(
                id=request.data.get("consultation_id"),
                organisation=request.data.get("organisation", None),
                is_active=True,
            )
        except Exception:
            return Response(
                {"status": 400, "message": "Invalid consultation", "data": []},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Slot availability check Pending
        error = check_slot(
            request.data.get("staff_id"),
            request.data.get("date"),
            request.data.get("slot"),
            request.data.get("organisation"),
        )
        if error:
            return Response(
                {"status": 400, "message": f"{error}", "data": []},
                status=status.HTTP_400_BAD_REQUEST,
            )

        error = check_appointment_payload(request.data, consultation)
        if error:
            return Response(
                {"status": 400, "message": f"{error}", "data": []},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # TODO when Appointment is created from client portal always cod?
        if request.data.get("payment_mode") == Appointment.PaymentModeTypes.COD:
            is_paid = False
        elif request.data.get("payment_mode") == Appointment.PaymentModeTypes.ON_LINE:
            # TODO: check the payment status
            is_paid = True

        amount = get_end_user_payable(
            consultation, request.data.get("staff_id"), request.data.get("meeting_type")
        )
        if amount is None:
            return Response(
                {"status": 400, "message": "Invalid consultation", "data": []},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not request.data.get("terms_conditions", False):
            return Response(
                {
                    "status": 400,
                    "message": "Please accept terms & conditions",
                    "data": [],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        appointment = Appointment(
            consultation_id=consultation,
            staff_id=request.data.get("staff_id"),
            customer_id=request.data.get("user_id"),
            date=request.data.get("date"),
            slot=request.data.get("slot"),
            appointment_status=Appointment.AppointmentStatusTypes.HOLD,
            meeting_type=request.data.get("meeting_type"),
            customer_address_id=request.data.get("customer_address_id"),
            org_address_id=request.data.get("org_address_id"),
            notes=request.data.get("notes"),
            display_booking_id=generate_booking_id(request.data.get("organisation")),
            payment_mode=request.data.get("payment_mode"),
            is_paid=is_paid,
            amount=amount,
            organisation=request.data.get("organisation"),
            created_by=request.data.get("user_id"),
        )
        appointment.save()

        # Celery Task
        # Note : Fetch end_user, staff, company_name info from user service
        appointment_background_task.delay(
            str(appointment.id),
            request.data.get("organisation", None),
            str(request.data["admin_id"]),
            request.headers.get("Authorization"),
            "END_USER",
        )
        return Response(
            {
                "status": 201,
                "message": "Appointment created successfully",
                "data": self.serializer_class(appointment).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @swagger_wrapper(
        {
            "date": openapi.TYPE_STRING,
            "slot": openapi.TYPE_STRING,
        }
    )
    def update(self, request, *args, **kwargs):
        try:
            appointment = Appointment.objects.get(
                id=kwargs.get("pk", None),
                is_active=True,
                organisation=request.data.get("organisation", None),
                customer_id=request.data.get("user_id"),
            )
            # Slot availability check Pending

            error = check_slot(
                appointment.staff_id,
                request.data.get("date"),
                request.data.get("slot"),
                request.data.get("organisation"),
            )
            if error:
                return Response(
                    {"status": 400, "message": f"{error}", "data": []},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            previous_date = appointment.date
            previous_slot = appointment.slot

            appointment.date = request.data.get("date")
            appointment.slot = request.data.get("slot")
            appointment.updated_by = request.data.get("user_id")
            appointment.save()

            # Celery Task
            # Note : Fetch end_user, staff, company_name info from user service
            endUserAppointmentRescheduleBackgroundTask.delay(
                str(appointment.id),
                request.data.get("organisation", None),
                previous_date,
                previous_slot,
                str(request.data["admin_id"]),
                request.headers.get(
                    "Authorization"
                ),  # getJWTToken(request.headers.get("Authorization"))
                "END_USER",
            )
            return Response(
                {
                    "status": 200,
                    "message": "Appointment Reschedule completed",
                    "data": [],
                },
                status=status.HTTP_200_OK,
            )
        except Exception as err:
            logging.error(f"EndUserAppointmentsApi update: {err}", exc_info=True)
            return Response(
                {"status": 400, "message": "Appointment not found", "data": []},
                status=status.HTTP_400_BAD_REQUEST,
            )
