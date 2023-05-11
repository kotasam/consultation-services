from django.db import models
from common.models import BaseModel
from django.core.exceptions import ValidationError


def validate_consultation_type(value):
    if value in ["ON_LINE", "OFF_LINE", "DOOR_STEP"]:
        return value
    raise ValidationError("Invalid consultation type")


def validate_discount_type(value):
    if value in ["PERCENTAGE", "AMOUNT", None, ""]:
        return value
    raise ValidationError("Invalid discount type")


def validate_appointment_type(value):
    if value in ["HOLD", "ACCEPTED", "REJECTED", "COMPLETED", "NO_SHOW"]:
        return value
    raise ValidationError("Invalid appointment type")


def validate_payment_mode_type(value):
    if value in ["ON_LINE", "COD"]:
        return value
    raise ValidationError("Invalid payment_mode type")


def validate_payment_type(value):
    if value in ["CASH", "CREDIT_CARD", "DEBIT_CARD", "UPI"]:
        return value
    raise ValidationError("Invalid payment_mode type")


class Category(BaseModel):
    name = models.CharField(max_length=150, blank=False, null=False)
    description = models.CharField(max_length=300, blank=True, null=True)
    image = models.CharField(max_length=150, blank=True, null=True)

    class Meta:
        unique_together = (("name", "organisation", "is_active"),)

    def __str__(self):
        return "{}".format(self.id)


class Consultation(BaseModel):
    name = models.CharField(max_length=150, blank=False, null=False)
    description = models.TextField(blank=True, null=True)
    category_id = models.ForeignKey(
        Category,
        related_name="consultation_category",
        on_delete=models.CASCADE,
        blank=False,
        null=False,
    )
    image = models.CharField(max_length=150, blank=True, null=True)
    duration = models.CharField(max_length=10, blank=True, null=True)
    is_staff_enabled = models.BooleanField(blank=False, null=False, default=True)

    class Meta:
        unique_together = (("name", "organisation", "is_active"),)

    def __str__(self):
        return "{}".format(self.id)


class ConsultationStaff(BaseModel):
    class ConsultationModeTypes(models.TextChoices):
        ON_LINE = "ON_LINE", "on_line"
        OFF_LINE = "OFF_LINE", "off_line"
        DOOR_STEP = "DOOR_STEP", "door_step"

    class DiscountTypes(models.TextChoices):
        PERCENTAGE = "PERCENTAGE", "percentage"
        AMOUNT = "AMOUNT", "amount"

    consultation_id = models.ForeignKey(
        Consultation,
        related_name="consultation_staff_consultation",
        on_delete=models.CASCADE,
        blank=False,
        null=False,
    )
    staff_id = models.CharField(max_length=50, blank=True, null=True)
    mode = models.CharField(
        max_length=20,
        choices=ConsultationModeTypes.choices,
        blank=False,
        null=False,
        validators=[validate_consultation_type],
    )
    discount_type = models.CharField(
        max_length=20,
        choices=DiscountTypes.choices,
        blank=True,
        null=True,
        validators=[validate_discount_type],
    )
    discount_value = models.IntegerField(blank=True, null=True, default=0)
    price = models.IntegerField(blank=True, null=True, default=0)
    final_price = models.IntegerField(blank=False, null=False, default=0)
    is_staff_enabled = models.BooleanField(blank=False, null=False, default=False)
    staff_special_price = models.IntegerField(blank=True, null=True)

    # class Meta:
    #     unique_together = (("mode", "consultation_id", "organisation"),)

    def __str__(self):
        return "{}".format(self.id)


class Appointment(BaseModel):
    class ConsultationModeTypes(models.TextChoices):
        ON_LINE = "ON_LINE", "on_line"
        OFF_LINE = "OFF_LINE", "off_line"
        DOOR_STEP = "DOOR_STEP", "door_step"

    class AppointmentStatusTypes(models.TextChoices):
        HOLD = "HOLD", "hold"
        ACCEPTED = "ACCEPTED", "accepted"
        REJECTED = "REJECTED", "rejected"
        COMPLETED = "COMPLETED", "completed"
        NO_SHOW = "NO_SHOW", "no_show"

    class PaymentModeTypes(models.TextChoices):
        ON_LINE = "ON_LINE", "on_line"
        COD = "COD", "cod"

    class PaymentStatusTypes(models.TextChoices):
        PAYMENT_AWAITED = "PAYMENT_AWAITED", "payment_awaited"
        SUCCESS = "SUCCESS", "success"

    consultation_id = models.ForeignKey(
        Consultation,
        related_name="appointment_consultation",
        on_delete=models.CASCADE,
        blank=False,
        null=False,
    )
    staff_id = models.CharField(max_length=50, blank=True, null=True)
    customer_id = models.CharField(max_length=50, blank=False, null=False)
    date = models.CharField(max_length=20, blank=False, null=False)
    slot = models.CharField(max_length=20, blank=False, null=False)
    appointment_status = models.CharField(
        max_length=20,
        choices=AppointmentStatusTypes.choices,
        blank=False,
        null=False,
        validators=[validate_appointment_type],
    )
    meeting_type = models.CharField(
        max_length=20,
        choices=ConsultationModeTypes.choices,
        blank=False,
        null=False,
        validators=[validate_consultation_type],
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatusTypes.choices,
        blank=False,
        null=False,
        default="PAYMENT_AWAITED"
        # validators=[validate_consultation_type],
    )
    customer_address_id = models.CharField(max_length=50, blank=True, null=True)
    org_address_id = models.CharField(max_length=50, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    display_booking_id = models.CharField(max_length=20, blank=False, null=False)
    meeting_info = models.JSONField(
        "Appointment meeting info", null=False, default=dict
    )
    payment_mode = models.CharField(
        max_length=20,
        choices=PaymentModeTypes.choices,
        blank=False,
        null=False,
        validators=[validate_payment_mode_type],
    )
    amount = models.IntegerField(blank=False, null=False, default=0)
    is_paid = models.BooleanField(blank=False, null=False, default=False)
    terms_conditions = models.BooleanField(default=False)

    def __str__(self):
        return "{}".format(self.id)


class AppointmentPaymentMapping(BaseModel):
    class PaymentTypes(models.TextChoices):
        CASH = "CASH", "cash"
        CREDIT_CARD = "CREDIT_CARD", "credit_card"
        DEBIT_CARD = "DEBIT_CARD", "debit_card"
        UPI = "UPI", "upi"

    appointment_id = models.ForeignKey(
        Appointment,
        related_name="appointment_payment_mapping_appointment",
        on_delete=models.CASCADE,
        blank=False,
        null=False,
    )
    payment_mode = models.CharField(
        max_length=20,
        choices=PaymentTypes.choices,
        blank=False,
        null=False,
        validators=[validate_payment_type],
    )
    payment_transaction_id = models.CharField(max_length=20, blank=False, null=False)

    def __str__(self):
        return "{}".format(self.id)
