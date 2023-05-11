from __future__ import absolute_import, unicode_literals
from celery import shared_task
from common.grpc.actions.user_client import getUserInfo
from consultation.models import Appointment
from consultation.helper import (
    send_appointment_email,
    generate_zoom_meeting,
    get_alert_notification_payload,
    get_staff_email_payload,
    get_user_email_payload,
    getAppointmentActionPayload,
    getAppointmenReschedulePayload,
    getEndUserAppointmenReschedulePayload,
    getEndUserAppointmenReschedulePayloadForStaff,
    get_invoice_payload,
    get_lead_payload,
    get_recepients,
    makeUserInfoAPICall,
    makeEndUserUserInfoAPICall,
)
from common.publisher import publish_event
from worke_consultation_service.config import config as cfg
import asyncio
import logging
from consultation_celery import app


# @shared_task(bind=True, track_started=True)
@app.task(queue=cfg.get("celery", "CELERY_QUEUE"))
def appointment_background_task(
    appointment_id, organisation, admin_id, token, user_type
):
    try:
        logging.error(f"In appointment_background_task:", exc_info=True)
        logging.info("In appointment_background_task")
        logging.info(f"appointment_id ---> {appointment_id}")
        logging.info(f"token ---> {token}")
        logging.info(f"admin_id ---> {admin_id}")
        appointment = Appointment.objects.get(
            id=appointment_id, organisation=organisation, is_active=True
        )
        logging.error(f"appointment_id ---> {appointment_id}", exc_info=True)
        if appointment.meeting_type == Appointment.ConsultationModeTypes.ON_LINE:
            logging.error(f"meeting_type ==   ON_LINE", exc_info=True)
            # Generate zoom meeting url here
            logging.info("In online meeting")
            meeting_info = generate_zoom_meeting(
                "veman",  # Staff details should be passed here to fetch zoom keys
                appointment.consultation_id.name,
                appointment.consultation_id.duration,
                appointment.date,
                appointment.slot,
                organisation,
            )
            if meeting_info is None or "join_url" not in meeting_info:
                logging.info(f"In If")
                # Don't delete the appointment instead add retry mechanism
                # appointment.delete()
                # Send email regarding Appointment is cancelled
            else:
                logging.info(f"In Else")
                join_url = str(meeting_info["join_url"])
                logging.info(f"join_url ---> {join_url}")
                appointment.meeting_info = meeting_info
                appointment.save()
        elif appointment.meeting_type == Appointment.ConsultationModeTypes.OFF_LINE:
            logging.info("In offline meeting")

        elif appointment.meeting_type == Appointment.ConsultationModeTypes.DOOR_STEP:
            logging.info("In door step meeting")

        logging.info("before event")
        # Note: If user_info or staff_info None means something wrong with the ids or grpc server is down Handle the case
        user_info = getUserInfo(appointment.customer_id)
        # Comment the above line and un comment the below line to avoid grpc call
        # user_info = None
        if user_info is None:
            # Make http call here
            if user_type != "END_USER":
                user_info = makeUserInfoAPICall(appointment.customer_id, token)
            else:
                user_info = makeEndUserUserInfoAPICall(
                    appointment.customer_id, appointment.organisation
                )
            if user_info is None:
                # Handle the case failed to fetch user info
                pass
        logging.error(f"user_info ---> {user_info}", exc_info=True)
        # if appointment.staff_id is not None:
        staff_info = getUserInfo(appointment.staff_id)
        # Comment the above line and un comment the below line to avoid grpc call
        # staff_info = None
        if staff_info is None:
            # Make http call here
            if user_type != "END_USER":
                staff_info = makeUserInfoAPICall(appointment.staff_id, token)
            else:
                staff_info = makeEndUserUserInfoAPICall(
                    appointment.staff_id, appointment.organisation
                )
                print("staff_info --->", staff_info)
            if staff_info is None:
                # Handle the case failed to fetch user info
                pass
        logging.error(f"staff_info ---> {staff_info}", exc_info=True)
        event_status = publish_event(
            get_user_email_payload(appointment, user_info, staff_info, token),
            cfg.get("events", "EMAIL_SERVICE_EXCHANGE"),
            cfg.get("events", "APPOINTMENT_CREATE_ROUTING_KEY"),
        )
        if event_status is None:
            pass
        if appointment.staff_id is not None:
            event_status = publish_event(
                get_staff_email_payload(appointment, user_info, staff_info, token),
                cfg.get("events", "EMAIL_SERVICE_EXCHANGE"),
                cfg.get("events", "APPOINTMENT_CREATE_ROUTING_KEY"),
            )
            if event_status is None:
                pass
        event_status = publish_event(
            get_alert_notification_payload(appointment, admin_id, token),
            cfg.get("events", "NOTIFICAION_SERVICE_EXCHANGE"),
            cfg.get("events", "APPOINTMENT_CREATE_ROUTING_KEY"),
        )
        if event_status is None:
            pass
        event_status = publish_event(
            get_invoice_payload(appointment, token),
            cfg.get("events", "DOCUMENT_SERVICE_EXCHANGE"),
            cfg.get("events", "APPOINTMENT_CREATE_ROUTING_KEY"),
        )
        if event_status is None:
            pass
        # publish_event(get_lead_payload(appointment), "LEAD")
        logging.info("after event")
    except Exception as err:
        logging.info(f"appointment_background_task exception{err}")
        logging.error(
            f"appointment_background_task exception ---> {err}", exc_info=True
        )
        pass


# @shared_task(bind=True, track_started=True)
@app.task(queue=cfg.get("celery", "CELERY_QUEUE"))
def appointment_reschedule_background_task(
    appointment_id,
    organisation,
    previous_date,
    previous_slot,
    admin_id,
    token,
    user_type,
):
    try:
        logging.info("In appointment_reschedule_background_task")
        appointment = Appointment.objects.get(
            id=appointment_id, organisation=organisation, is_active=True
        )
        # Note: If user_info or staff_info None means something wrong with the ids or grpc server is down Handle the case
        user_info = getUserInfo(appointment.customer_id)
        # Comment the above line and un comment the below line to avoid grpc call
        # user_info = None
        if user_info is None:
            # Make http call here
            if user_type != "END_USER":
                user_info = makeUserInfoAPICall(appointment.customer_id, token)
            else:
                user_info = makeEndUserUserInfoAPICall(
                    appointment.customer_id, appointment.organisation
                )
            if user_info is None:
                # Handle the case failed to fetch user info
                pass
        # if appointment.staff_id is not None:
        staff_info = getUserInfo(appointment.staff_id)
        # Comment the above line and un comment the below line to avoid grpc call
        # staff_info = None
        if staff_info is None:
            # Make http call here
            if user_type != "END_USER":
                staff_info = makeUserInfoAPICall(appointment.staff_id, token)
            else:
                staff_info = makeEndUserUserInfoAPICall(
                    appointment.staff_id, appointment.organisation
                )
            if staff_info is None:
                # Handle the case failed to fetch user info
                pass
        event_status = publish_event(
            getAppointmenReschedulePayload(
                appointment, user_info, staff_info, previous_date, previous_slot, token
            ),
            cfg.get("events", "EMAIL_SERVICE_EXCHANGE"),
            cfg.get("events", "APPOINTMENT_RESCHEDULE_ROUTING_KEY"),
        )
        if event_status is None:
            pass
    except Exception:
        pass


# @shared_task(bind=True, track_started=True)
@app.task(queue=cfg.get("celery", "CELERY_QUEUE"))
def endUserAppointmentRescheduleBackgroundTask(
    appointment_id,
    organisation,
    previous_date,
    previous_slot,
    admin_id,
    token,
    user_type,
):
    try:
        logging.info("In appointment_reschedule_background_task")
        appointment = Appointment.objects.get(
            id=appointment_id, organisation=organisation, is_active=True
        )
        # Note: If user_info or staff_info None means something wrong with the ids or grpc server is down Handle the case
        user_info = getUserInfo(appointment.customer_id)
        # Comment the above line and un comment the below line to avoid grpc call
        # user_info = None
        # if appointment.staff_id is not None:
        if user_info is None:
            # Make http call here
            if user_type != "END_USER":
                user_info = makeUserInfoAPICall(appointment.customer_id, token)
            else:
                user_info = makeEndUserUserInfoAPICall(
                    appointment.customer_id, appointment.organisation
                )
            if user_info is None:
                # Handle the case failed to fetch user info
                pass
        staff_info = getUserInfo(appointment.staff_id)
        # Comment the above line and un comment the below line to avoid grpc call
        # staff_info = None
        if staff_info is None:
            # Make http call here
            if user_type != "END_USER":
                staff_info = makeUserInfoAPICall(appointment.staff_id, token)
            else:
                staff_info = makeEndUserUserInfoAPICall(
                    appointment.staff_id, appointment.organisation
                )
            if staff_info is None:
                # Handle the case failed to fetch user info
                pass
        event_status = publish_event(
            getEndUserAppointmenReschedulePayload(
                appointment, user_info, staff_info, previous_date, previous_slot, token
            ),
            cfg.get("events", "EMAIL_SERVICE_EXCHANGE"),
            cfg.get("events", "APPOINTMENT_RESCHEDULE_ROUTING_KEY"),
        )
        if event_status is None:
            # Handle the case failed to fetch user info
            pass
        if appointment.staff_id is not None:
            event_status = publish_event(
                getEndUserAppointmenReschedulePayloadForStaff(
                    appointment,
                    user_info,
                    staff_info,
                    previous_date,
                    previous_slot,
                    token,
                ),
                cfg.get("events", "EMAIL_SERVICE_EXCHANGE"),
                cfg.get("events", "APPOINTMENT_RESCHEDULE_ROUTING_KEY"),
            )
            if event_status is None:
                # Handle the case failed to fetch user info
                pass
    except Exception:
        pass


# @shared_task(bind=True, track_started=True)
@app.task(queue=cfg.get("celery", "CELERY_QUEUE"))
def appointment_update_background_task(
    appointment_id, organisation, admin_id, token, user_type
):
    try:
        logging.info("In appointment_update_background_task")
        appointment = Appointment.objects.get(
            id=appointment_id, organisation=organisation, is_active=True
        )
        # GRPC Calls
        # Note: If user_info or staff_info None means something wrong with the ids or grpc server is down Handle the case
        user_info = getUserInfo(appointment.customer_id)
        # Comment the above line and un comment the below line to avoid grpc call
        # user_info = None
        if user_info is None:
            # Make http call here
            if user_type != "END_USER":
                user_info = makeUserInfoAPICall(appointment.customer_id, token)
            else:
                user_info = makeEndUserUserInfoAPICall(
                    appointment.customer_id, appointment.organisation
                )
            if user_info is None:
                # Handle the case failed to fetch user info
                pass
        logging.error(f"user_info ---> {user_info}", exc_info=True)
        staff_info = getUserInfo(appointment.staff_id)
        # Comment the above line and un comment the below line to avoid grpc call
        # staff_info = None
        if staff_info is None:
            # Make http call here
            if user_type != "END_USER":
                staff_info = makeUserInfoAPICall(appointment.staff_id, token)
            else:
                staff_info = makeEndUserUserInfoAPICall(
                    appointment.staff_id, appointment.organisation
                )
            if staff_info is None:
                # Handle the case failed to fetch user info
                pass
        logging.error(f"staff_info ---> {staff_info}", exc_info=True)

        if (
            appointment.appointment_status
            == Appointment.AppointmentStatusTypes.ACCEPTED
        ):
            # routing_key = "Consultation.Booking.Accepted"
            pass
        elif (
            appointment.appointment_status
            == Appointment.AppointmentStatusTypes.COMPLETED
        ):
            # routing_key = "Consultation.Booking.Completed"
            pass
        elif (
            appointment.appointment_status
            == Appointment.AppointmentStatusTypes.REJECTED
        ):
            appointment.status = False
            appointment.save()
            event_status = publish_event(
                getAppointmentActionPayload(appointment, user_info, staff_info, token),
                cfg.get("events", "EMAIL_SERVICE_EXCHANGE"),
                cfg.get("events", "APPOINTMENT_REJECT_ROUTING_KEY"),
            )
            if event_status is None:
                # Handle the case
                pass
        # publish_event(getAppointmentActionPayload(appointment), routing_key)
    except Exception:
        pass
