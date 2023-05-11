import pika, json
from worke_consultation_service.config import config as cfg
import logging


from common.middleware.new_relic_middleware import get_logger


logger = get_logger()


def publish_event(message, exchange_name, routing_key):
    try:
        logging.error(f"message : {message}")
        logging.error(f"routing_key : {routing_key}")
        logging.error(f"exchange_name : {exchange_name}")
        logging.info(f"message : {message}")
        logging.info(f"routing_key : {routing_key}")
        logging.info(f"exchange_name : {exchange_name}")
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
        logging.error(f"connection is established")
        channel = conn.channel()
        channel.exchange_declare(exchange=exchange_name, exchange_type="topic")
        logging.error(f"exchange is declared")
        channel.basic_publish(
            exchange=exchange_name, routing_key=routing_key, body=json.dumps(message)
        )
        logging.error(f"event published")
        conn.close()
        try:
            logger.info(
                "EVENT SUCCESFULLY PUBLISHED TO "
                + exchange_name
                + "\n ROUTING KEY"
                + routing_key
                + "\n CURRENT PAYLOAD \n"
                + str(message)
            )
        except Exception as err:
            logging.error(f"Publishing to new relic exception: {err}")
            pass
    except Exception as err:
        logging.info(f"publish_event exception : {err}")
        return None
