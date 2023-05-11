from common.modules import end_user_permission_modules
from worke_consultation_service.config import config as cfg


"""
Pending ---> For staff fetch staff permissions from user service
"""


def get_type(path):
    permission_type = path.split("/")[1]
    return permission_type


def check_end_user_permissions(request):
    print("request ")
    if request.method in ["OPTIONS", "HEAD"]:
        return True

    # if end_user_permission_modules(get_type(request.path), request.method):
    #     return True
    # return False
    return True


def check_staff_permissions(request):
    if request.method in ["OPTIONS", "HEAD"]:
        return True
    if request.data.get("role") == cfg.get("user_types", "ADMIN"):
        if request.method in ["POST", "GET", "PUT", "PATCH", "DELETE"]:
            return True
        return False
    elif request.data.get("role") == cfg.get("user_types", "MANAGER"):
        if request.method in ["POST", "GET", "PUT", "PATCH"]:
            return True
        return False
    elif request.data.get("role") == cfg.get("user_types", "STAFF"):
        if request.method in ["GET"]:
            return True
        return False
    elif request.data.get("role") == cfg.get("user_types", "AGENT"):
        if request.method in ["GET"]:
            return True
        return False
