import jwt
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.backends import TokenBackend
from common.helper import check_end_user_permissions, check_staff_permissions
from worke_consultation_service.settings import JWT_SECRET
import logging


class IsAuthenticatedOverride(IsAuthenticated):
    message = {"error": "You don't have permission to perform this action"}

    def has_permission(self, request, view):
        try:
            user_type = self.get_user_type(request)
            if type(user_type) == bool:
                return False
            if user_type in [
                "ADMIN",
                "SUPERADMIN",
            ]:
                return True
            elif user_type == "ENDUSER":
                return check_end_user_permissions(request)
                pass
            elif user_type == "STAFF":
                # return check_end_user_permissions(request)
                return check_staff_permissions(request)
                # return True
            return False
        except Exception as err:
            logging.error(
                f"IsAuthenticatedOverride has_permission: {err}", exc_info=True
            )
            return False

    def get_user_type(self, request):
        try:
            header = request.headers["Authorization"]
            token = header.split(" ")[1]
            # token_info = jwt.decode(token, options={"verify_signature": False})
            token_info = TokenBackend(algorithm="HS256", signing_key=JWT_SECRET).decode(
                token, verify=True
            )
            # Adding organisation in request payload
            request.data["organisation"] = token_info.get("organisation")
            request.data["user_id"] = token_info.get("id")
            request.data["dept"] = token_info.get("dept")
            request.data["role"] = token_info.get("role")
            request.data["permissions"] = token_info.get("permissions")
            request.data["admin_id"] = token_info.get("admin_id")
            return token_info.get("utype")
        except Exception as err:
            logging.error(
                f"IsAuthenticatedOverride get_user_type: {err}", exc_info=True
            )
            return True
