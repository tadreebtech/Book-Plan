from rest_framework.exceptions import APIException


class SelfAdminDemotionForbidden(APIException):
    status_code = 403
    default_detail = "An administrator cannot remove the administrator role from themselves."
    default_code = "SELF_ADMIN_DEMOTION_FORBIDDEN"
