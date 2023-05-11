import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "worke_consultation_service.settings")

import django

django.setup()


import pika, json
from worke_consultation_service.config import config as cfg
from consultation.models import Appointment
from consultation.tasks import appointment_background_task
import logging


def paymentServiceCallback(ch, method, properties, body):
    try:
        json_body = json.loads(body)
        appointment = Appointment.objects.get(
            id=json_body["source_id"],
            status=True,
            is_active=True,
            organisation=json_body["organisation"],
        )
        if json_body["is_success"]:
            appointment.payment_status = Appointment.PaymentStatusTypes.SUCCESS
            appointment.save()
            appointment_background_task.delay(
                str(appointment.id), json_body["organisation"]
            )
        else:
            pass
    except Exception as err:
        logging.error(f"paymentServiceCallback exception: {err}", exc_info=True)
        pass


try:
    credentials = pika.PlainCredentials(
        cfg.get("rabbit_mq", "USER_NAME"), cfg.get("rabbit_mq", "PASSWORD")
    )
    parameters = pika.ConnectionParameters(
        host=cfg.get("rabbit_mq", "HOST"),
        virtual_host=cfg.get("rabbit_mq", "VIRTUAL_HOST"),
        credentials=credentials,
        frame_max=int(cfg.get("rabbit_mq", "FRAME_MAX")),
        heartbeat=int(cfg.get("rabbit_mq", "HEART_BEAT")),
        connection_attempts=int(cfg.get("rabbit_mq", "CONNECTION_ATTEMPTS")),
    )
    conn = pika.BlockingConnection(parameters)
    logging.info(f"conn: {conn}")
    channel = conn.channel()
    channel.exchange_declare(exchange="PAYMENT", exchange_type="topic")

    result = channel.queue_declare("APPOINTMENT", durable=True)
    queue_name = result.method.queue
    channel.queue_bind(
        exchange="PAYMENT", queue=queue_name, routing_key="Payment.Payment.Success"
    )
except Exception as err:
    logging.error(
        f"Worke consultation service consumer exception: {err}", exc_info=True
    )
    pass


channel.basic_consume(
    queue=queue_name, on_message_callback=paymentServiceCallback, auto_ack=True
)

print("Started consuming......")
channel.start_consuming()
