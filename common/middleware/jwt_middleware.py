from django.http import HttpResponseBadRequest
import time
from rest_framework_simplejwt.backends import TokenBackend
from worke_consultation_service.settings import JWT_SECRET
import logging


class JWTMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self.check_url(request.path):
            response = self.get_response(request)
            return response

        auth_header = self.get_auth_header(request)
        if not isinstance(auth_header, str):
            return HttpResponseBadRequest(
                '{"status": 400, "message": "token must be provided", "data":[]}',
                status=400,
            )

        token = self.get_raw_token(auth_header)
        if not isinstance(token, str):
            return HttpResponseBadRequest(
                '{"status": 400, "message": "Invalid token format", "data":[]}',
                status=400,
            )

        (verified, payload) = self.get_token_validated(token)

        if not verified and self.check_token_expired(token):
            return HttpResponseBadRequest(
                '{"status": 403, "message": "Token expired", "data":[]}', status=403
            )
        elif not verified:
            return HttpResponseBadRequest(
                '{"status": 400, "message": "Invalid token provided", "data":[]}',
                status=400,
            )
        response = self.get_response(request)
        return response

    def get_auth_header(self, request):
        header = request.headers.get("Authorization", None)
        if not isinstance(header, str):
            return None
        return header

    def get_raw_token(self, header):
        parts = header.split()
        if len(parts) != 2 and parts[0] != "Bearer":
            return None

        return parts[1]

    def get_token_validated(self, token):
        verified = False
        try:
            payload = TokenBackend(algorithm="HS256", signing_key=JWT_SECRET).decode(
                token, verify=True
            )
            verified = True
        except Exception as err:
            logging.error(f"JWTMiddleware get_token_validated: {err}", exc_info=True)
            payload = []
        return (verified, payload)

    def epoch_time(self):
        return int(time.time())

    def check_token_expired(self, token):
        try:
            payload = TokenBackend(algorithm="HS256", signing_key=JWT_SECRET).decode(
                token, verify=False
            )
            if "exp" in payload and payload["exp"] < self.epoch_time():
                return True
        except Exception as err:
            logging.error(f"JWTMiddleware check_token_expired: {err}", exc_info=True)
            pass

        return False

    def check_url(self, path):
        if path in [
            "/",
            "/consultations/docs/",
            "/consultations/end_user/category/",
            "/consultations/end_user/consultations/",
            "/consultations/end_user/consultation/",
            "/consultations/silk/",
            "/consultations/silk/requests/",
            "/consultations/prometheus-xyzabc/",
            "/consultations/prometheus-worke/metrics",
        ]:
            return True
