from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def customExceptionHandler(exc, context):
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    # Now add the HTTP status code to the response.
    if response is None:
        return Response(
            {"status": 500, "message": "Something went wrong", "data": {}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    else:
        return Response(
            {
                "status": response.status_code,
                "message": response.data["detail"],
                "data": {},
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
