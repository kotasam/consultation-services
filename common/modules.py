CATEGORY = "category"
CONSULTATION = "consultation"
APPOINTMENT = "appointment"
APPOINTMENT_RESCHEDULE = "appointment_reschedule"
END_USER = "end_user"


def end_user_permission_modules(permission_type, request_method):
    if permission_type not in [APPOINTMENT, APPOINTMENT_RESCHEDULE]:
        return False
    if permission_type == APPOINTMENT:
        if request_method in ["DELETE", "PUT"]:
            return False
    return True
