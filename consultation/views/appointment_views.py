from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from consultation.models import Consultation, Appointment
from consultation.serializers import AppointmentSerializer, AppointmentUpdateSerializer
from consultation.helper import (
    check_appointment_payload,
    generate_booking_id,
    get_organisation,
    get_deleted_time,
    get_end_user_payable,
    check_slot,
    getJWTToken,
)
from consultation.tasks import (
    appointment_background_task,
    appointment_reschedule_background_task,
    appointment_update_background_task,
)
from common.swagger.custom_documentation import (
    swagger_wrapper,
    page_param,
    offset_param,
)
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from worke_consultation_service.config import config as cfg
from math import ceil
import logging


class AppointmentApi(viewsets.ViewSet):
    serializer_class = AppointmentSerializer
    http_method_names = ["post", "get", "delete", "put", "head", "options"]

    @swagger_auto_schema(manual_parameters=[page_param, offset_param])
    def list(self, request, *args, **kwargs):
        appointments_list = Appointment.objects.filter(
            organisation=request.data.get("organisation", None), is_active=True
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
                "message": "Appointments info",
                "data": self.serializer_class(appointments_list, many=True).data,
            },
            status=status.HTTP_200_OK,
        )

    @swagger_wrapper(
        {
            # "customer_name": openapi.TYPE_STRING,
            # "email": openapi.TYPE_STRING,
            # "phone_number": openapi.TYPE_STRING,
            "customer_id": openapi.TYPE_STRING,
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
                id=request.data.get("consultation_id", None),
                organisation=request.data.get("organisation", None),
                is_active=True,
            )
        except Exception as err:
            logging.error(f"AppointmentApi create: {err}", exc_info=True)
            return Response(
                {"status": 400, "message": "Invalid consultation", "data": []},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Slot availability check from calander ---> Pending
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

        if request.data.get("payment_mode") == Appointment.PaymentModeTypes.COD:
            is_paid = False
        elif request.data.get("payment_mode") == Appointment.PaymentModeTypes.ON_LINE:
            # TODO: check the payment status
            is_paid = True

        amount = get_end_user_payable(
            consultation,
            request.data.get("staff_id"),
            request.data.get("meeting_type"),
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
            # customer_id = request.data.get("customer_id", None), Get it from user service
            customer_id=request.data.get("customer_id"),
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
            created_by=request.data.get("customer_id"),
            terms_conditions=True,
        )
        appointment.save()

        # Celery Task
        # Note : Fetch end_user, staff, company_name info from user service
        appointment_background_task.delay(
            str(appointment.id),
            request.data.get("organisation", None),
            str(request.data["admin_id"]),
            request.headers.get(
                "Authorization"
            ),  # getJWTToken(request.headers.get("Authorization"))
            "ADMIN",
        )
        return Response(
            {
                "status": 201,
                "message": "Appointment created",
                "data": self.serializer_class(appointment).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @swagger_wrapper(
        {
            "appointment_status": openapi.TYPE_STRING,
            "notes": openapi.TYPE_STRING,
            "payment_mode": openapi.TYPE_STRING,
            "staff_id": openapi.TYPE_STRING,
        }
    )
    def update(self, request, *args, **kwargs):
        try:
            appointment = Appointment.objects.get(
                id=kwargs.get("pk", None),
                is_active=True,
                organisation=request.data.get("organisation", None),
            )
            appointment_status = appointment.appointment_status
            request.data["updated_by"] = request.data.get("user_id")
            serializer_data = AppointmentUpdateSerializer(
                appointment, request.data, partial=True
            )
            if not serializer_data.is_valid():
                return Response(
                    {
                        "status": 400,
                        "message": "Invalid data",
                        "data": serializer_data.errors,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            serializer_data.save()
            if (
                "appointment_status" in request.data
                and appointment_status != request.data.get("appointment_status")
            ):
                appointment_update_background_task.delay(
                    str(appointment.id),
                    request.data.get("organisation", None),
                    str(request.data["admin_id"]),
                    request.headers.get(
                        "Authorization"
                    ),  # getJWTToken(request.headers.get("Authorization"))
                    "ADMIN",
                )

            # if (
            #     request.data.get("staff_id") is not None
            #     and request.data.get("staff_id") != appointment.staff_id
            # ):
            #     # TODO: Check staff existance and notifications
            #     appointment.staff_id = request.data.get("staff_id")
            #     appointment.save()
            return Response(
                {"status": 200, "message": "appointment updated", "data": []},
                status=status.HTTP_200_OK,
            )
        except Exception as err:
            logging.error(f"AppointmentApi destroy: {err}", exc_info=True)
            return Response(
                {"status": 400, "message": "Appointment not found", "data": []},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def destroy(self, request, *args, **kwargs):
        try:
            appointment = Appointment.objects.get(
                id=kwargs.get("pk", None),
                is_active=True,
                organisation=request.data.get("organisation", None),
            )
            appointment.is_active = False
            appointment.deleted_by = request.data.get("user_id")
            appointment.deleted_at = get_deleted_time()
            appointment.save()
            return Response(
                {"status": 200, "message": "Appointment deleted", "data": []},
                status=status.HTTP_200_OK,
            )
        except Exception as err:
            logging.error(f"AppointmentApi destroy: {err}", exc_info=True)
            return Response(
                {"status": 400, "message": "Appointment not found", "data": []},
                status=status.HTTP_400_BAD_REQUEST,
            )


class AppointmentRescheduleApi(viewsets.ViewSet):
    serializer_class = AppointmentSerializer
    http_method_names = ["put", "head", "options"]

    @swagger_wrapper(
        {
            "date": openapi.TYPE_STRING,
            "slot": openapi.TYPE_STRING,
        }
    )
    def update(self, request, *args, **kwargs):
        try:
            appointment = Appointment.objects.get(
                id=kwargs.get("pk"),
                is_active=True,
                organisation=request.data.get("organisation"),
            )
            # Slot availability check from calander ---> Pending
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
            appointment_reschedule_background_task.delay(
                str(appointment.id),
                request.data.get("organisation"),
                previous_date,
                previous_slot,
                str(request.data["admin_id"]),
                request.headers.get(
                    "Authorization"
                ),  # getJWTToken(request.headers.get("Authorization"))
                "ADMIN",
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
            logging.error(f"AppointmentApi update: {err}", exc_info=True)
            return Response(
                {"status": 400, "message": "Appointment not found", "data": []},
                status=status.HTTP_400_BAD_REQUEST,
            )
