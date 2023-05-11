from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.response import Response
from consultation.models import Category, Consultation, ConsultationStaff
from consultation.serializers import ConsultationSerializer, ConsultationStaffSerializer
from consultation.helper import (
    get_final_price,
    check_consultation_payload,
    check_consultation_staff_payload,
    check_consultation,
    get_deleted_time,
    check_duration,
    check_name,
)
from drf_yasg.utils import swagger_auto_schema
from common.swagger.custom_documentation import (
    consultation_api_documentation,
    category_id,
)
import uuid
import logging


class ConsultationApi(viewsets.ViewSet):
    serializer_class = ConsultationSerializer
    http_method_names = ["post", "get", "delete", "put", "head", "options"]

    @swagger_auto_schema(manual_parameters=[category_id])
    def list(self, request, *args, **kwargs):
        category_id = self.request.query_params.get("category_id")
        if category_id != None:
            consultations_list = Consultation.objects.filter(
                category_id=category_id,
                organisation=request.data.get("organisation", None),
                is_active=True,
            )
            return Response(
                {
                    "status": 200,
                    "message": "consultations info",
                    "data": self.serializer_class(consultations_list, many=True).data,
                },
                status=status.HTTP_200_OK,
            )

        consultations_list = Consultation.objects.filter(
            organisation=request.data.get("organisation", None), is_active=True
        )
        return Response(
            {
                "status": 200,
                "message": "consultations info",
                "data": self.serializer_class(consultations_list, many=True).data,
            },
            status=status.HTTP_200_OK,
        )

    @consultation_api_documentation
    def create(self, request, *args, **kwargs):
        if request.data.get("category_id") is None:
            return Response(
                {"status": 400, "message": "Please provide category id", "data": []},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            Consultation.objects.get(
                name=request.data.get("name"),
                is_active=True,
                organisation=request.data.get("organisation"),
            )
            return Response(
                {"status": 400, "message": "Consultation already exist", "data": []},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception:
            pass

        try:
            category = Category.objects.get(
                id=request.data.get("category_id", None),
                is_active=True,
                organisation=request.data.get("organisation", None),
            )
        except Exception:
            return Response(
                {"status": 400, "message": "Invalid category", "data": []},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not len(request.data.get("consultation_data", None)) <= 3:
            return Response(
                {"status": 400, "message": "Invalid consultation data", "data": []},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(request.data.get("consultation_data")) == 0:
            return Response(
                {"status": 400, "message": "Select atleast one mode", "data": []},
                status=status.HTTP_400_BAD_REQUEST,
            )
        error = check_name(request.data.get("name"))
        if error:
            return Response(
                {"status": 400, "message": "Invalid name", "data": []},
                status=status.HTTP_400_BAD_REQUEST,
            )

        error = check_duration(request.data.get("duration"))
        if error:
            return error

        with transaction.atomic():
            consultation = Consultation(
                name=request.data.get("name"),
                description=request.data.get("description"),
                category_id=category,
                image=request.data.get("image"),
                duration=request.data.get("duration"),
                is_staff_enabled=request.data.get("is_staff_enabled"),
                organisation=request.data.get("organisation"),
                created_by=request.data.get("user_id"),
            )
            consultation.save()
            consultation_data_list = []
            for data in request.data.get("consultation_data", None):
                error = check_consultation_payload(data)
                if error:
                    consultation.delete()
                    return Response(
                        {"status": 400, "message": f"{error}", "data": []},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                consultation_data_list.append(
                    ConsultationStaff(
                        consultation_id=consultation,
                        # staff_id=data.get("staff_id"),
                        mode=data.get("mode"),
                        discount_type=data.get("discount_type"),
                        discount_value=data.get("discount_value"),
                        price=data.get("price"),
                        final_price=get_final_price(
                            data.get("discount_type"),
                            data.get("discount_value"),
                            data.get("price"),
                        ),
                        organisation=request.data.get("organisation"),
                        created_by=request.data.get("user_id"),
                    )
                )
            ConsultationStaff.objects.bulk_create(consultation_data_list)
            consultation_staff_list = []
            if request.data.get("is_staff_enabled"):
                for data in request.data.get("staff_data", None):
                    error = check_consultation_staff_payload(data, consultation)
                    if error:
                        consultation.delete()
                        ConsultationStaff.objects.filter(
                            consultation_id=consultation,
                            organisation=request.data.get("organisation"),
                        ).delete()
                        return Response(
                            {"status": 400, "message": f"{error}", "data": []},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    consultation_staff_list.append(
                        ConsultationStaff(
                            consultation_id=consultation,
                            staff_id=data.get("staff_id"),
                            mode=data.get("mode"),
                            is_staff_enabled=True,
                            staff_special_price=data.get("staff_special_price"),
                            organisation=request.data.get("organisation"),
                            created_by=request.data.get("user_id"),
                        )
                    )
            ConsultationStaff.objects.bulk_create(consultation_staff_list)
        return Response(
            {
                "status": 201,
                "message": "Consultation created",
                "data": self.serializer_class(consultation).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @consultation_api_documentation
    def update(self, request, *args, **kwargs):
        try:
            consultation = Consultation.objects.get(
                id=kwargs.get("pk", None),
                is_active=True,
                organisation=request.data.get("organisation"),
            )
            request.data["updated_by"] = request.data.get("user_id")
            serializer_data = self.serializer_class(
                consultation, request.data, partial=True
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
            if not len(request.data.get("consultation_data")) <= 3:
                return Response(
                    {"status": 400, "message": "Invalid consultation data", "data": []},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            existing_consultation_modes = list(
                ConsultationStaff.objects.filter(
                    consultation_id=consultation,
                    organisation=request.data.get("organisation"),
                    status=True,
                    is_active=True,
                    staff_id=None,
                ).values_list("id", flat=True)
            )
            existing_consultation_modes = list(map(str, existing_consultation_modes))
            cosnulation_ids = []
            for data in request.data.get("consultation_data", None):
                try:
                    error = check_consultation_payload(data)
                    if error:
                        return Response(
                            {"status": 400, "message": f"{error}", "data": []},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    if data.get("id") != "":
                        cosnulation_ids.append(data.get("id"))
                        consultation_staff = ConsultationStaff.objects.get(
                            id=data.get("id"),
                            is_active=True,
                            organisation=request.data.get("organisation"),
                        )

                        data["updated_by"] = request.data.get("user_id")
                        data["final_price"] = get_final_price(
                            data.get("discount_type"),
                            data.get("discount_value"),
                            data.get("price"),
                        )
                        serializer_data = ConsultationStaffSerializer(
                            consultation_staff, data, partial=True
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
                    else:
                        consultation_staff = ConsultationStaff(
                            consultation_id=consultation,
                            # staff_id=data.get("staff_id"),
                            mode=data.get("mode"),
                            discount_type=data.get("discount_type"),
                            discount_value=data.get("discount_value"),
                            price=data.get("price"),
                            final_price=get_final_price(
                                data.get("discount_type"),
                                data.get("discount_value"),
                                data.get("price"),
                            ),
                            organisation=request.data.get("organisation"),
                            created_by=request.data.get("user_id"),
                        )
                        consultation_staff.save()
                except Exception as err:
                    logging.error(f"ConsultationApi update: {err}", exc_info=True)
                    return Response(
                        {"status": 400, "message": "Invalid data", "data": []},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            removed_consultations = list(
                set(existing_consultation_modes) - set(cosnulation_ids)
            )
            for id in removed_consultations:
                try:
                    consultation_obj = ConsultationStaff.objects.get(
                        id=id,
                        organisation=request.data.get("organisation"),
                        is_active=True,
                    )
                    consultation_obj.status = False
                    consultation_obj.save()
                except Exception as err:
                    logging.error(
                        f"ConsultationApi update line no 300: {err}", exc_info=True
                    )

            # Delete exiting staff data
            if not request.data.get("is_staff_enabled"):
                ConsultationStaff.objects.filter(
                    is_staff_enabled=True,
                    consultation_id=consultation,
                    organisation=request.data.get("organisation"),
                ).update(
                    is_active=False,
                    is_staff_enabled=False,
                    updated_by=request.data.get("user_id"),
                )
                consultation.is_staff_enabled = False
                consultation.save()

            existing_staffs_data = list(
                ConsultationStaff.objects.filter(
                    consultation_id=consultation,
                    organisation=request.data.get("organisation"),
                    status=True,
                    is_active=True,
                )
                .exclude(staff_id=None)
                .values_list("id", flat=True)
            )
            existing_staffs_data = list(map(str, existing_staffs_data))
            staff_ids = []
            for data in request.data.get("staff_data", None):
                try:
                    error = check_consultation_staff_payload(data, consultation)
                    if error:
                        return Response(
                            {"status": 400, "message": f"{error}", "data": []},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    if data.get("id") != "":
                        staff_ids.append(data.get("id"))
                        consultation_staff = ConsultationStaff.objects.get(
                            id=data.get("id"),
                            is_active=True,
                            organisation=request.data.get("organisation"),
                        )

                        data["updated_by"] = request.data.get("user_id")
                        serializer_data = ConsultationStaffSerializer(
                            consultation_staff, data, partial=True
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
                    else:
                        consultation_staff = ConsultationStaff(
                            consultation_id=consultation,
                            staff_id=data.get("staff_id"),
                            mode=data.get("mode"),
                            is_staff_enabled=True,
                            staff_special_price=data.get("staff_special_price"),
                            organisation=request.data.get("organisation"),
                            created_by=request.data.get("user_id"),
                        )
                        consultation_staff.save()
                except Exception as err:
                    logging.error(f"ConsultationApi update: {err}", exc_info=True)
                    return Response(
                        {"status": 400, "message": "Invalid data", "data": []},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            removed_staffs = list(set(existing_staffs_data) - set(staff_ids))
            for id in removed_staffs:
                try:
                    consultation_obj = ConsultationStaff.objects.get(
                        id=id,
                        organisation=request.data.get("organisation"),
                        is_active=True,
                    )
                    consultation_obj.status = False
                    consultation_obj.save()
                except Exception as err:
                    logging.error(
                        f"ConsultationApi update line no 392: {err}", exc_info=True
                    )

            return Response(
                {
                    "status": 200,
                    "message": "Consultation updated",
                    "data": self.serializer_class(consultation).data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as err:
            logging.error(f"ConsultationApi update: {err}", exc_info=True)
            return Response(
                {"status": 400, "message": "Consultation not found", "data": []},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def retrieve(self, request, *args, **kwargs):
        try:
            consultation = Consultation.objects.get(
                id=kwargs.get("pk", None),
                is_active=True,
                organisation=request.data.get("organisation", None),
            )
            return Response(
                {
                    "status": 200,
                    "message": "consultations info",
                    "data": self.serializer_class(consultation).data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as err:
            logging.error(f"ConsultationApi retrieve: {err}", exc_info=True)
            return Response(
                {"status": 400, "message": "Consultation not found", "data": []},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def destroy(self, request, *args, **kwargs):
        try:
            consultation = Consultation.objects.get(
                id=kwargs.get("pk", None),
                is_active=True,
                organisation=request.data.get("organisation", None),
            )
            consultation.is_active = False
            consultation.deleted_by = request.data.get("user_id")
            consultation.deleted_at = get_deleted_time()
            consultation.save()
            return Response(
                {"status": 200, "message": "Consultation deleted", "data": []},
                status=status.HTTP_200_OK,
            )
        except Exception as err:
            logging.error(f"ConsultationApi destroy: {err}", exc_info=True)
            return Response(
                {"status": 400, "message": "Consultation not found", "data": []},
                status=status.HTTP_400_BAD_REQUEST,
            )
