"""
Handled exceptions raised by REST framework.

In addition, Django's built in 403 and 404 exceptions are handled.
(`django.http.Http404` and `django.core.exceptions.PermissionDenied`)
"""
import math

from django.http import JsonResponse
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

from rest_framework import status
from rest_framework.utils.serializer_helpers import ReturnDict, ReturnList


def _get_error_details(data, default_code=None):
    """
    Descend into a nested data structure, forcing any
    lazy translation strings or strings into `ErrorDetail`.
    """
    if isinstance(data, (list, tuple)):
        ret = [
            _get_error_details(item, default_code) for item in data
        ]
        if isinstance(data, ReturnList):
            return ReturnList(ret, serializer=data.serializer)
        return ret
    elif isinstance(data, dict):
        ret = {
            key: _get_error_details(value, default_code)
            for key, value in data.items()
        }
        if isinstance(data, ReturnDict):
            return ReturnDict(ret, serializer=data.serializer)
        return ret

    text = force_str(data)
    code = getattr(data, 'code', default_code)
    return ErrorDetail(text, code)


def _get_codes(detail):
    if isinstance(detail, list):
        return [_get_codes(item) for item in detail]
    elif isinstance(detail, dict):
        return {key: _get_codes(value) for key, value in detail.items()}
    return detail.code


def _get_full_details(detail):
    if isinstance(detail, list):
        return [_get_full_details(item) for item in detail]
    elif isinstance(detail, dict):
        return {key: _get_full_details(value) for key, value in detail.items()}
    return {
        'message': detail,
        'code': detail.code
    }


class ErrorDetail(str):
    """
    A string-like object that can additionally have a code.
    """
    code = None

    def __new__(cls, string, code=None):
        self = super().__new__(cls, string)
        self.code = code
        return self

    def __eq__(self, other):
        result = super().__eq__(other)
        if result is NotImplemented:
            return NotImplemented
        try:
            return result and self.code == other.code
        except AttributeError:
            return result

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return NotImplemented
        return not result

    def __repr__(self):
        return 'ErrorDetail(string=%r, code=%r)' % (
            str(self),
            self.code,
        )

    def __hash__(self):
        return hash(str(self))


class APIException(Exception):
    """
    Base class for REST framework exceptions.
    Subclasses should provide `.status_code` and `.default_detail` properties.
    """
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = _('A server error occurred.')
    default_code = 'error'

    def __init__(self, detail=None, code=None):
        if detail is None:
            detail = self.default_detail
        if code is None:
            code = self.default_code

        self.detail = _get_error_details(detail, code)

    def __str__(self):
        return str(self.detail)

    def get_codes(self):
        """
        Return only the code part of the error details.

        Eg. {"name": ["required"]}
        """
        return _get_codes(self.detail)

    def get_full_details(self):
        """
        Return both the message & code parts of the error details.

        Eg. {"name": [{"message": "This field is required.", "code": "required"}]}
        """
        return _get_full_details(self.detail)


# The recommended style for using `ValidationError` is to keep it namespaced
# under `serializers`, in order to minimize potential confusion with Django's
# built in `ValidationError`. For example:
#
# from rest_framework import serializers
# raise serializers.ValidationError('Value was invalid')

class ValidationError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _('Invalid input.')
    default_code = 'invalid'

    def __init__(self, detail=None, code=None):
        if detail is None:
            detail = self.default_detail
        if code is None:
            code = self.default_code

        # For validation failures, we may collect many errors together,
        # so the details should always be coerced to a list if not already.
        if isinstance(detail, tuple):
            detail = list(detail)
        elif not isinstance(detail, dict) and not isinstance(detail, list):
            detail = [detail]

        self.detail = _get_error_details(detail, code)


class ParseError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _('Malformed request.')
    default_code = 'parse_error'


class AuthenticationFailed(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = _('Incorrect authentication credentials.')
    default_code = 'authentication_failed'


class NotAuthenticated(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = _('Authentication credentials were not provided.')
    default_code = 'not_authenticated'


class PermissionDenied(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = _('You do not have permission to perform this action.')
    default_code = 'permission_denied'


class NotFound(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = _('Not found.')
    default_code = 'not_found'


class MethodNotAllowed(APIException):
    status_code = status.HTTP_405_METHOD_NOT_ALLOWED
    default_detail = _('Method "{method}" not allowed.')
    default_code = 'method_not_allowed'

    def __init__(self, method, detail=None, code=None):
        if detail is None:
            detail = force_str(self.default_detail).format(method=method)
        super().__init__(detail, code)


class NotAcceptable(APIException):
    status_code = status.HTTP_406_NOT_ACCEPTABLE
    default_detail = _('Could not satisfy the request Accept header.')
    default_code = 'not_acceptable'

    def __init__(self, detail=None, code=None, available_renderers=None):
        self.available_renderers = available_renderers
        super().__init__(detail, code)


class UnsupportedMediaType(APIException):
    status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    default_detail = _('Unsupported media type "{media_type}" in request.')
    default_code = 'unsupported_media_type'

    def __init__(self, media_type, detail=None, code=None):
        if detail is None:
            detail = force_str(self.default_detail).format(media_type=media_type)
        super().__init__(detail, code)


class Throttled(APIException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = _('Request was throttled.')
    extra_detail_singular = _('Expected available in {wait} second.')
    extra_detail_plural = _('Expected available in {wait} seconds.')
    default_code = 'throttled'

    def __init__(self, wait=None, detail=None, code=None):
        if detail is None:
            detail = force_str(self.default_detail)
        if wait is not None:
            wait = math.ceil(wait)
            detail = ' '.join((
                detail,
                force_str(ngettext(self.extra_detail_singular.format(wait=wait),
                                   self.extra_detail_plural.format(wait=wait),
                                   wait))))
        self.wait = wait
        super().__init__(detail, code)


def server_error(request, *args, **kwargs):
    """
    Generic 500 error handler.
    """
    data = {
        'error': 'Server Error (500)'
    }
    return JsonResponse(data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def bad_request(request, exception, *args, **kwargs):
    """
    Generic 400 error handler.
    """
    data = {
        'error': 'Bad Request (400)'
    }
    return JsonResponse(data, status=status.HTTP_400_BAD_REQUEST)
