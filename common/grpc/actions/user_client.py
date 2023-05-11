# from common.grpc.protopys import user_pb2, user_pb2_grpc
from common.grpc.protopys import user_service_pb2, user_service_pb2_grpc
import grpc
from worke_consultation_service.config import config as cfg
import logging


def getUserInfo(id):
    try:
        logging.info("In getUserInfo")
        with grpc.insecure_channel(cfg.get("grpc", "USER_SERVICE")) as channel:
            # with grpc.insecure_channel("localhost:1563") as channel:
            stub = user_service_pb2_grpc.UserServicesStub(channel)
            logging.info(f"stub: {stub}")
            user_info_request = user_service_pb2.UserItem(
                id=id,
                organisation=True,
                user_additional=True,
                user_permissions=True,
                user_working_hours=True,
            )
            logging.info(f"user_info_request: {user_info_request}")
            user_info_reply = stub.GetUserData(user_info_request)
            logging.info(f"user_info_reply: {user_info_reply}")
            if not user_info_reply.valid:
                return None
            # logging.info(f"user_info_reply --->{user_info_reply}")
            return {
                "email": user_info_reply.email,
                "fname": user_info_reply.fname,
                "lname": user_info_reply.lname,
            }
    except Exception as err:
        logging.info(f"getUserInfo exception: {err}")
        return None
