from rest_framework import status
from rest_framework.response import Response
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from consultation.models import Consultation, ConsultationStaff, Appointment
from worke_consultation_service.settings import DEFAULT_REPLY_EMAIL, DEFAULT_FROM_EMAIL
from worke_consultation_service.config import config as cfg
from settings.models import Zoom
import uuid
import jwt
from time import time
import pytz
from datetime import datetime, date, timedelta
import logging
import requests
import string
import random
import re


def get_organisation():
    pass


def check_consultation(name, organisation):
    try:
        Consultation.objects.get(name=name, is_active=True, organisation=organisation)
        return Response(
            {"status": 400, "message": "consultation already exists", "data": []},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception:
        pass


def check_consultation_payload(data):
    print("In check_consultation_payload")
    discount_type = data.get("discount_type")
    discount_value = data.get("discount_value")
    price = data.get("price")
    if discount_type not in [
        ConsultationStaff.DiscountTypes.AMOUNT,
        ConsultationStaff.DiscountTypes.PERCENTAGE,
        None,
        "",
    ]:
        return "Invalid discount type"

    if discount_type == ConsultationStaff.DiscountTypes.AMOUNT:
        if discount_value >= price:
            return "Discount value shouldn't be greater than or equal price"
        if discount_value < 0:
            return "Discount value cannot be less than 0"

    if (
        discount_type == ConsultationStaff.DiscountTypes.PERCENTAGE
        and discount_value not in range(1, 99)
    ):
        return "Discount value should be in between 1 and 99"

    if data.get("mode", None) not in [
        ConsultationStaff.ConsultationModeTypes.ON_LINE,
        ConsultationStaff.ConsultationModeTypes.OFF_LINE,
        ConsultationStaff.ConsultationModeTypes.DOOR_STEP,
    ]:
        return "Invalid consultation type"

    if price < 0:
        return "Price cannot be less than 0"


def check_consultation_staff_payload(data, consultation):
    # if data.get("mode", None) not in [
    #     ConsultationStaff.ConsultationModeTypes.ON_LINE,
    #     ConsultationStaff.ConsultationModeTypes.OFF_LINE,
    #     ConsultationStaff.ConsultationModeTypes.DOOR_STEP,
    # ]:
    #     return "Invalid staff consultation type"

    consultation_modes = list(
        ConsultationStaff.objects.filter(
            consultation_id=consultation,
            is_active=True,
            organisation=consultation.organisation,
        ).values_list("mode", flat=True)
    )
    if data.get("mode", None) not in consultation_modes:
        print("In staff payload")
        return "Invalid meeting type"

    # Check staff is active or not from user service ---> Pending
    try:
        if data.get("staff_id") is None or data.get("staff_id") == "":
            return "Invalid staff"
    except Exception:
        return "Invalid staff"

    try:
        if (
            data.get("staff_special_price") is None
            or data.get("staff_special_price") < 0
        ):
            return "Invalid staff special price"
    except Exception:
        return "Invalid staff special price"


def get_final_price(discount_type, discount_value, price):
    if discount_type in [None, ""]:
        return int(price)
    if discount_type == ConsultationStaff.DiscountTypes.AMOUNT:
        discounted_price = price - discount_value
    elif discount_type == ConsultationStaff.DiscountTypes.PERCENTAGE:
        discounted_price = price - ((discount_value / 100) * price)
    return int(discounted_price)


def check_appointment_payload(data, consultation):
    consultation_modes = list(
        ConsultationStaff.objects.filter(
            consultation_id=consultation,
            is_active=True,
            organisation=data.get("organisation", None),
        ).values_list("mode", flat=True)
    )
    if data.get("meeting_type", None) not in consultation_modes:
        return "Invalid meeting type"

    if data.get("meeting_type", None) == Appointment.ConsultationModeTypes.ON_LINE:
        data["customer_address_id"] = None
        data["org_address_id"] = None

    elif data.get("meeting_type", None) == Appointment.ConsultationModeTypes.OFF_LINE:
        # TODO : verify org address from user service
        data["customer_address_id"] = None

    # How about using else here
    elif data.get("meeting_type", None) == Appointment.ConsultationModeTypes.DOOR_STEP:
        # TODO : verify user address from user service
        data["org_address_id"] = None

    if data.get("payment_mode", None) not in [
        Appointment.PaymentModeTypes.COD,
        Appointment.PaymentModeTypes.ON_LINE,
    ]:
        return "Invalid payment method"

    if consultation.is_staff_enabled:
        staffs_list = list(
            ConsultationStaff.objects.filter(
                consultation_id=consultation,
                staff_id=data.get("staff_id"),
                is_active=True,
                status=True,
                is_staff_enabled=True,
                organisation=data.get("organisation", None),
            ).values_list("staff_id", flat=True)
        )
        if data.get("staff_id") not in staffs_list:
            return "Invalid staff"
    # Can we just use else here?
    elif not consultation.is_staff_enabled:
        data["staff_id"] = None

    # Checking for previus date validation(TODO Modify date Format from user service)
    try:
        current_date = date.today().strftime("%d-%m-%Y")
        current_date_obj = datetime.strptime(current_date, "%d-%m-%Y")
        appointment_date_obj = datetime.strptime(data.get("date", None), "%d-%m-%Y")
        if not appointment_date_obj >= current_date_obj:
            return "Invalid date"
    except Exception:
        return "Invalid date"

    # Checking for previous time slots


def check_slot(staff_id, date, slot, organisation):
    # TODO is consultation is required???
    appointments = Appointment.objects.filter(
        staff_id=staff_id,
        date=date,
        status=True,
        is_active=True,
        slot=slot,
        organisation=organisation,
    )
    if len(appointments) != 0:
        return "Slot is not available"


def generate_booking_id(organisation):
    return "OR-" + str(random.randint(00000, 99999))


def send_appointment_email(
    to_email,
    template,
    subject,
    staff_name,
    customer_name,
    meeting_url,
    address,
    consultation_name,
    appointment_date,
    appointment_time_slot,
    company_name,
    booking_url,
):
    try:
        logging.info(f"In send_appointment_email")
        payload = {
            "staff": staff_name,
            "user": customer_name,
            "url": meeting_url,
            "address": address,
            "service_name": consultation_name,
            "slot_date": appointment_date,
            "parent_slot_time": appointment_time_slot,
            "company_name": company_name,
            "booking_url": booking_url,
            "return_query_email": DEFAULT_REPLY_EMAIL,
        }
        html_content = render_to_string(template, payload)
        msg = EmailMultiAlternatives(
            subject,
            "",
            DEFAULT_FROM_EMAIL,
            [to_email],
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        logging.info(f"after sending mail")
    except Exception:
        pass


def get_zoom_token(organisation):
    try:
        # Fetch zoom api keys
        zoom = Zoom.objects.get(organisation=organisation)
        payload = {
            "iss": zoom.api_key,  # static Zoom API key
            "exp": int(time()) + 3600,
        }
        return jwt.encode(payload, zoom.secret_key)

        # payload = {
        #     "iss": "FZlT3hXTS3KDNmXJH3POzw",  # static Zoom API key
        #     "exp": int(time()) + 3600,
        # }
        # return jwt.encode(
        #     payload, "5S1AmrHnsJ2fAOnKtUZkjv6mHK37LC4TgsSm"
        # )  # static Zoom API secret key
    except Exception:
        return None


def get_zoom_id(organisation):
    try:
        # If zoom id in staff external_ids field return that
        # if "zoom" in staff.external_ids:
        #     return staff.external_ids["zoom"]

        # If no zoom id in staff external_ids generate zoom id
        payload = {
            "token": get_zoom_token(organisation),
            # "email": staff.email,
            "email": "dileep@syoft.com",  # static staff email
        }
        zoom_id = ""
        try:
            url = f"https://api.zoom.us/v2/users?status=active"
            token = payload["token"]
            headers = {"Authorization": f"Bearer {token}"}
            zoom_api_response = requests.get(url, headers=headers).json()
            for zoom_user in zoom_api_response["users"]:
                zoom_id = zoom_user["id"]
        except Exception as err:
            logging.info(f"In Second Exception")
            logging.info(f"Exception ---> {err}")
            return None

        # By here zoom id will be generated and save that in external_ids field
        # staff.external_ids["zoom"] = zoom_id
        # staff.save()
        return zoom_id
    except Exception as err:
        logging.info(f"In First Exception")
        logging.info(f"Exception ---> {err}")
        return None


def generate_zoom_meeting(
    staff,
    consultation_name,
    duration,
    appointment_date,
    appointment_time_slot,
    organisation,
):
    try:
        zoom_user_id = get_zoom_id(organisation)
        token = get_zoom_token(organisation)
        logging.info(f"zoom_user_id ---> {zoom_user_id}")
        logging.info(f"token ---> {token}")
        if zoom_user_id is None or token is None:
            return None
        logging.info(f"After If")

        staff_first_name = "Veman"  # static staff first name
        staff_last_name = "Peddapalli"  # static staff last_name
        # me = "me"
        url = f"https://api.zoom.us/v2/users/{zoom_user_id}/meetings"
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "topic": f"Appointment for the service {consultation_name} with {staff_first_name} {staff_last_name}",
            "type": 2,
            "start_time": f"{appointment_date}T{appointment_time_slot}:00",
            "duration": int(duration),
            "settings": {
                "join_before_host": False,
                "jbh_time": 5,
                "auto_recording": "cloud",
            },
        }
        logging.info(f"Before Api Call")
        logging.error(f"url  ---> {url}", exc_info=True)
        logging.error(f"headers  ---> {headers}", exc_info=True)
        zoom_api_response = requests.post(url, json=payload, headers=headers)
        logging.info(f"After Api Call")
        logging.info(f"zoom_api_response ---> {zoom_api_response}")
        if zoom_api_response.status_code != 201:
            logging.info(f"After Api Call")
            return None
        zoom_api_json_response = zoom_api_response.json()
        logging.info(f"zoom_api_json_response ---> {zoom_api_json_response}")
        # zoom_api_json_response["type"] = "zoom"
        return zoom_api_json_response
    except Exception as err:
        logging.info(f"In generate_zoom_meeting Exception")
        logging.info(f"Exception ---> {err}")
        return None


def get_deleted_time():
    # In future get timezone from Company settings
    time_zone = pytz.timezone(cfg.get("common", "TIME_ZONE"))
    return datetime.now(time_zone)


def get_end_user_payable(consultation, staff_id, meeting_type):
    try:
        consultation_data = ConsultationStaff.objects.get(
            consultation_id=consultation,
            staff_id=None,
            status=True,
            is_staff_enabled=False,
            is_active=True,
            organisation=consultation.organisation,
            mode=meeting_type,
        )
    except Exception as err:
        logging.error(f"get_end_user_payable first exception: {err}", exc_info=True)
        return None

    if consultation.is_staff_enabled:
        try:
            consultation_staff = ConsultationStaff.objects.get(
                consultation_id=consultation,
                staff_id=staff_id,
                status=True,
                is_staff_enabled=True,
                is_active=True,
                organisation=consultation.organisation,
                mode=meeting_type,
            )
            return (
                consultation_data.final_price + consultation_staff.staff_special_price
            )
        except Exception as err:
            logging.error(
                f"get_end_user_payable second exception: {err}", exc_info=True
            )
            return None

    # Can we use just elase here?
    elif not consultation.is_staff_enabled:
        return consultation_data.final_price


def check_name(name):
    name = name.strip()
    elements = name.split(" ")
    for element in elements:
        if not bool(re.match("^[a-zA-Z0-9]", element)):
            return True
    return False


def check_duration(duration):
    try:
        int(duration)
    except Exception:
        return "Invalid duration"


def get_recepients(appointment, admin_id):
    return [
        str(appointment.customer_id),
        str(appointment.staff_id),
        str(admin_id),
        # str(appointment.organisation),
    ]


def get_staff_email_payload(appointment, user_info, staff_info, token):
    subject = f"Appointment Booked {appointment.date} {appointment.slot}"
    if appointment.meeting_type == Appointment.ConsultationModeTypes.ON_LINE:
        body = f"""
            Dear {staff_info["fname"]} {staff_info["lname"]},

            This is to inform you that an appointment has been booked for you with {user_info["fname"]} {user_info["lname"]}.

            The details of the appointment are as follows:

            Date: {appointment.date}

            Time: {appointment.slot}

            Mode: {appointment.meeting_type}

            Meeting URL: {appointment.meeting_info["start_url"]}

            Thank you
        """
    else:
        body = f"""
            Dear {staff_info["fname"]} {staff_info["lname"]},

            This is to inform you that an appointment has been booked for you with {user_info["fname"]} {user_info["lname"]}.

            The details of the appointment are as follows:

            Date: {appointment.date}

            Time: {appointment.slot}

            Mode: {appointment.meeting_type}

            Thank you
        """
    return {
        "type": "EMAIL",  # email,calendar,both
        "message": {
            "to": [staff_info["email"]],
            "from": "",
            "subject": subject,
            "body": body,
        },
        "media_url": "",
        "organisation": appointment.organisation,
        "source_type": "APPOINTMENTS",  # Activity,Form Builder,Appointments,Order,User
        "source_id": str(appointment.id),
        "start_time": "",  # down 3 fields are required when type is calender invite
        "end_time": "",
        "time_zone": "",
        "info": "",
        "token": token,
    }


def getAppointmenReschedulePayload(
    appointment, user_info, staff_info, previous_date, previous_slot, token
):
    subject = f"Rescheduling Your Appointment"
    body = f"""
        Dear {user_info["fname"]} {user_info["lname"]},

        We regret to inform you that your appointment with [Staff name] staff scheduled for {previous_date} {previous_slot} has been rescheduled to {appointment.date} & {appointment.slot}. We apologise for the inconvenience caused.

        Please let us know if this rescheduled time work for you. If not we will be happy to reschedule it again.

        If you have any questions or concerns, please do not hesitate
    """
    return {
        "type": "EMAIL",  # email,calendar,both
        "message": {
            "to": [user_info["email"]],
            "from": "",
            "subject": subject,
            "body": body,
        },
        "media_url": appointment.meeting_info["join_url"],
        "organisation": appointment.organisation,
        "source_type": "APPOINTMENTS",  # Activity,Form Builder,Appointments,Order,User
        "source_id": str(appointment.id),
        "start_time": "",  # down 3 fields are required when type is calender invite
        "end_time": "",
        "time_zone": "",
        "info": "",
        "token": token,
    }


def getEndUserAppointmenReschedulePayloadForStaff(
    appointment, user_info, staff_info, previous_date, previous_slot, token
):
    subject = f"Appointment Rescheduled {appointment.date} {appointment.slot}"
    if appointment.meeting_type == Appointment.ConsultationModeTypes.ON_LINE:
        body = f"""
            Dear {staff_info["fname"]} {staff_info["lname"]},

            This is to inform you that an appointment scheduled for you with {user_info["fname"]} {user_info["lname"]} on {previous_date} {previous_slot} has been rescheduled to {appointment.date} {appointment.slot}.

            The details of the appointment are as follows:

            Date: {appointment.date}

            Time: {appointment.slot}

            Mode: {appointment.meeting_type}

            Meeting URL: {appointment.meeting_info["start_url"]}

            Thank you
        """
    else:
        body = f"""
            Dear {staff_info["fname"]} {staff_info["lname"]},

            This is to inform you that an appointment scheduled for you with {user_info["fname"]} {user_info["lname"]} on {previous_date} {previous_slot} has been rescheduled to {appointment.date} {appointment.slot}.

            The details of the appointment are as follows:

            Date: {appointment.date}

            Time: {appointment.slot}

            Mode: {appointment.meeting_type}

            Thank you
        """
    return {
        "type": "EMAIL",  # email,calendar,both
        "message": {
            "to": [staff_info["email"]],
            "from": "",
            "subject": subject,
            "body": body,
        },
        "media_url": appointment.meeting_info["join_url"],
        "organisation": appointment.organisation,
        "source_type": "APPOINTMENTS",  # Activity,Form Builder,Appointments,Order,User
        "source_id": str(appointment.id),
        "start_time": "",  # down 3 fields are required when type is calender invite
        "end_time": "",
        "time_zone": "",
        "info": "",
        "token": token,
    }


def getEndUserAppointmenReschedulePayload(
    appointment, user_info, staff_info, previous_date, previous_slot, token
):
    subject = f"Reschedule Confirmation {appointment.date} {appointment.slot}"
    if appointment.meeting_type == Appointment.ConsultationModeTypes.ON_LINE:
        if appointment.staff_id is not None:
            body = f"""
                Dear {user_info["fname"]} {user_info["lname"]},

                As requested, your appointment scheduled for {previous_date} {previous_slot} has been rescheduled.

                Details of your appointment are as follows:

                Date: {appointment.date} 

                Time: {appointment.slot}

                Staff Name: {staff_info["fname"]} {staff_info["lname"]}

                Mode: {appointment.meeting_type}

                Meeting URL: {appointment.meeting_info["join_url"]}

                If you need to cancel or reschedule your appointment, please contact us at least {{hours}} hours in advance.

                We look forward to see you soon.

                NOTE:
                If you opt for Offline Appointment, please arrive at least 15 minutes before your appointment time.
            """
        else:
            body = f"""
                Dear {user_info["fname"]} {user_info["lname"]},

                As requested, your appointment scheduled for {previous_date} {previous_slot} has been rescheduled.

                Details of your appointment are as follows:

                Date: {appointment.date} 

                Time: {appointment.slot}

                Mode: {appointment.meeting_type}

                Meeting URL: {appointment.meeting_info["join_url"]}

                If you need to cancel or reschedule your appointment, please contact us at least {{hours}} hours in advance.

                We look forward to see you soon.

                NOTE:
                If you opt for Offline Appointment, please arrive at least 15 minutes before your appointment time.
            """
    else:
        if appointment.staff_id is not None:
            body = f"""
                Dear {user_info["fname"]} {user_info["lname"]},

                As requested, your appointment scheduled for {previous_date} {previous_slot} has been rescheduled.

                Details of your appointment are as follows:

                Date: {appointment.date} 

                Time: {appointment.slot}

                Staff Name: {staff_info["fname"]} {staff_info["lname"]}

                Mode: {appointment.meeting_type}

                If you need to cancel or reschedule your appointment, please contact us at least {{hours}} hours in advance.

                We look forward to see you soon.

                NOTE:
                If you opt for Offline Appointment, please arrive at least 15 minutes before your appointment time.
            """
        else:
            body = f"""
                Dear {user_info["fname"]} {user_info["lname"]},

                As requested, your appointment scheduled for {previous_date} {previous_slot} has been rescheduled.

                Details of your appointment are as follows:

                Date: {appointment.date} 

                Time: {appointment.slot}

                Mode: {appointment.meeting_type}

                If you need to cancel or reschedule your appointment, please contact us at least {{hours}} hours in advance.

                We look forward to see you soon.

                NOTE:
                If you opt for Offline Appointment, please arrive at least 15 minutes before your appointment time.
            """

    return {
        "type": "EMAIL",  # email,calendar,both
        "message": {
            "to": [user_info["fname"]],
            "from": "",
            "subject": subject,
            "body": body,
        },
        "media_url": appointment.meeting_info["join_url"],
        "organisation": appointment.organisation,
        "source_type": "APPOINTMENTS",  # Activity,Form Builder,Appointments,Order,User
        "source_id": str(appointment.id),
        "start_time": "",  # down 3 fields are required when type is calender invite
        "end_time": "",
        "time_zone": "",
        "info": "",
        "token": token,
    }


def getAppointmentActionPayload(appointment, user_info, staff_info, token):
    # Add online offline conditions
    subject = f"Appointment Rejected: {appointment.date} {appointment.slot}"
    if appointment.meeting_type == Appointment.ConsultationModeTypes.ON_LINE:
        body = f"""
            Dear {user_info["fname"]} {user_info["lname"]},

            Thank you for your request to schedule an appointment. Unfortunately, we are unable to accommodate your request at this time.

            We apologise for the inconvenience caused. If you have any further questions or would like to reschedule, please do not hesitate to contact us.

            Thank you for your understanding.
        """
    else:
        body = f"""
            Dear {user_info["fname"]} {user_info["lname"]},

            Thank you for your request to schedule an appointment. Unfortunately, we are unable to accommodate your request at this time.

            We apologise for the inconvenience caused. If you have any further questions or would like to reschedule, please do not hesitate to contact us.

            Thank you for your understanding.
        """
    return {
        "type": "EMAIL",  # email,calendar,both
        "message": {
            "to": [user_info["email"]],
            "from": "",
            "subject": subject,
            "body": body,
        },
        "media_url": "",
        "organisation": appointment.organisation,
        "source_type": "APPOINTMENTS",  # Activity,Form Builder,Appointments,Order,User
        "source_id": str(appointment.id),
        "start_time": "",  # down 3 fields are required when type is calender invite
        "end_time": "",
        "time_zone": "",
        "info": "",
        "token": token,
    }


def get_user_email_payload(appointment, user_info, staff_info, token):
    subject = f"Appointment Confirmed: {appointment.date} {appointment.slot}"
    if appointment.meeting_type == Appointment.ConsultationModeTypes.ON_LINE:
        if appointment.staff_id is not None:
            body = f"""
                Dear {user_info["fname"]} {user_info["lname"]},

                We are pleased to confirm that your appointment has been confirmed.
                Details of your appointment are as follows:

                Date: {appointment.date}

                Time: {appointment.slot}

                Staff Name: {staff_info["fname"]} {staff_info["lname"]}

                Mode: {appointment.meeting_type}

                Meeting URL: {appointment.meeting_info["join_url"]}

                If you need to cancel or reschedule your appointment, please contact us at least {{hours}} hours in advance.

                We look forward to see you soon.

                NOTE:
                If you opt for Offline Appointment, please arrive at least 15 minutes before your appointment time.
            """
        else:
            body = f"""
                Dear {user_info["fname"]} {user_info["lname"]},

                We are pleased to confirm that your appointment has been confirmed.
                Details of your appointment are as follows:

                Date: {appointment.date}

                Time: {appointment.slot}

                Mode: {appointment.meeting_type}

                Meeting URL: {appointment.meeting_info["join_url"]}

                If you need to cancel or reschedule your appointment, please contact us at least {{hours}} hours in advance.

                We look forward to see you soon.

                NOTE:
                If you opt for Offline Appointment, please arrive at least 15 minutes before your appointment time.
            """
    else:
        if appointment.staff_id is not None:
            body = f"""
                Dear {user_info["fname"]} {user_info["lname"]},

                We are pleased to confirm that your appointment has been confirmed.
                Details of your appointment are as follows:

                Date: {appointment.date}

                Time: {appointment.slot}

                Staff Name: {staff_info["fname"]} {staff_info["lname"]}

                Mode: {appointment.meeting_type}

                If you need to cancel or reschedule your appointment, please contact us at least {{hours}} hours in advance.

                We look forward to see you soon.

                NOTE:
                If you opt for Offline Appointment, please arrive at least 15 minutes before your appointment time.
            """
        else:
            body = f"""
                Dear [Name],

                We are pleased to confirm that your appointment has been confirmed.
                Details of your appointment are as follows:

                Date: {appointment.date}

                Time: {appointment.slot}

                Mode: {appointment.meeting_type}

                If you need to cancel or reschedule your appointment, please contact us at least {{hours}} hours in advance.

                We look forward to see you soon.

                NOTE:
                If you opt for Offline Appointment, please arrive at least 15 minutes before your appointment time.
            """
    return {
        "type": "EMAIL",  # email,calendar,both
        "message": {
            "to": [user_info["email"]],
            "from": "",
            "subject": subject,
            "body": body,
        },
        "media_url": "",
        "organisation": appointment.organisation,
        "source_type": "APPOINTMENTS",  # Activity,Form Builder,Appointments,Order,User
        "source_id": str(appointment.id),
        "start_time": "",  # down 3 fields are required when type is calender invite
        "end_time": "",
        "time_zone": "",
        "info": "",
        "token": token,
    }


def get_alert_notification_payload(appointment, admin_id, token):
    logging.info(f"In get_alert_notification_payload")
    time_str = appointment.slot
    logging.info(f"time_str: {time_str}")
    date_format_str = "%H:%M"
    given_time = datetime.strptime(time_str, date_format_str)
    logging.info(f"given_time: {given_time}")
    final_time = given_time + timedelta(
        minutes=int(appointment.consultation_id.duration)
    )
    logging.info(f"final_time: {final_time}")
    final_time_str = final_time.strftime("%H:%M")
    logging.info(f"final_time_str: {final_time_str}")
    return {
        "recipients": get_recepients(appointment, admin_id),
        "source_id": str(appointment.id),
        "title": "Message",
        "description": "This is the new message",
        "department": appointment.organisation,
        "organisation": appointment.organisation,
        "created_by": appointment.created_by,
        "initial_time": appointment.slot,
        "duration": appointment.consultation_id.duration,
        "final_time": final_time_str,
        "token": token,
    }


def get_invoice_payload(appointment, token):
    try:
        consultation_data = ConsultationStaff.objects.get(
            consultation_id=appointment.consultation_id,
            staff_id=appointment.staff_id,
            mode=appointment.meeting_type,
            organisation=appointment.organisation,
        )
        if appointment.consultation_id.is_staff_enabled:
            staff_data = ConsultationStaff.objects.get(
                consultation_id=appointment.consultation_id,
                staff_id=appointment.staff_id,
                mode=appointment.meeting_type,
                organisation=appointment.organisation,
            )
            price = consultation_data.price + staff_data.staff_special_price
        else:
            price = consultation_data.price
    except Exception:
        # Handle the case failed task
        pass

    billing_address_id = ""
    if appointment.meeting_type == Appointment.ConsultationModeTypes.DOOR_STEP:
        billing_address_id = appointment.customer_address_id

    return {
        "organisation": appointment.organisation,
        "user_id": appointment.customer_id,
        "source_id": str(appointment.id),
        "department": "",
        "appointment_type": appointment.meeting_type,
        "billing_address_id": billing_address_id,
        "source_type": "APPOINTMENT",
        "items": [
            {
                "item_name": appointment.consultation_id.name,
                "price": price,
                "discount": consultation_data.discount_value,
                "tax": "",
                "quantity": 1,
            }
        ],
        "total": appointment.amount,
        "recipients": [],
        "info": "",
        "token": token,
    }


def get_lead_payload(appointment):
    return {
        "organisation": appointment.organisation,
        "user_id": appointment.customer_id,
        "source_id": str(appointment.id),
        "source_type": "APPOINTMENT",
        "staff_id": appointment.staff_id,
        "consultation_id": str(appointment.consultation_id.id),
        "recipients": [],
    }


def getSerializerError(errors):
    for error in errors["non_field_errors"]:
        return error
    return "Something went wrong"


def getJWTToken(headers):
    if headers is None or type(headers) != str:
        return None
    else:
        token = headers.split(" ")
        return token[1]


def makeUserInfoAPICall(user_id, token):
    try:
        headers = {"Authorization": token}
        base_url = cfg.get("http", "USER_INFO")
        url = f"{base_url}{user_id}/"
        api_response = requests.get(url, headers=headers)
        if api_response.status_code != 200:
            return None
        json_response = api_response.json()
        return {
            "email": json_response["data"]["email"],
            "fname": json_response["data"]["fname"],
            "lname": json_response["data"]["lname"],
        }
    except Exception as err:
        logging.error(f"makeUserInfoAPICall Exception: {err}", exc_info=True)
        return None


def makeEndUserUserInfoAPICall(customer_id, organisation):
    try:
        base_url = cfg.get("http", "USER_INFO_FOR_ENDUSER")
        url = f"{base_url}org={organisation}&staff_id={customer_id}"
        api_response = requests.get(url)
        if api_response.status_code != 200:
            return None
        json_response = api_response.json()
        return {
            "email": json_response["data"]["email"],
            "fname": json_response["data"]["fname"],
            "lname": json_response["data"]["lname"],
        }
    except Exception as err:
        logging.error(f"makeUserInfoAPICall Exception: {err}", exc_info=True)
        return None
