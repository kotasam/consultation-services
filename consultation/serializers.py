from rest_framework import serializers
from consultation.models import Category, Consultation, ConsultationStaff, Appointment


class CategoryListSerializer(serializers.ModelSerializer):
    count = serializers.SerializerMethodField("get_consultations_count")

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "description",
            "image",
            "organisation",
            "created_by",
            "status",
            "is_active",
            "count",
        ]

    def get_consultations_count(self, obj):
        return Consultation.objects.filter(
            category_id=obj, is_active=True, organisation=obj.organisation
        ).count()


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "description",
            "image",
            "organisation",
            "created_by",
            "status",
            "is_active",
        ]


class ConsultationStaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsultationStaff
        fields = "__all__"


class ConsultationPlainSerializer(serializers.ModelSerializer):
    class Meta:
        model = Consultation
        fields = "__all__"


class ConsultationSerializer(serializers.ModelSerializer):
    consultation_data = serializers.SerializerMethodField("get_consultation_data")
    staff_data = serializers.SerializerMethodField("get_staff_data")

    class Meta:
        model = Consultation
        exclude = ["is_staff_enabled"]

    def get_consultation_data(self, obj):
        consultation_staff = ConsultationStaff.objects.filter(
            consultation_id=obj,
            is_active=True,
            organisation=obj.organisation,
            staff_id=None,
            status=True,
        )
        return ConsultationStaffSerializer(consultation_staff, many=True).data

    def get_staff_data(self, obj):
        consultation_staff = ConsultationStaff.objects.filter(
            consultation_id=obj,
            is_active=True,
            organisation=obj.organisation,
            status=True,
        ).exclude(staff_id=None)
        return ConsultationStaffSerializer(consultation_staff, many=True).data


class AppointmentSerializer(serializers.ModelSerializer):
    consultation_id = ConsultationPlainSerializer(read_only=True)

    class Meta:
        model = Appointment
        fields = "__all__"


class AppointmentUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = ["appointment_status", "notes", "updated_by"]
