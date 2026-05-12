"""
Provide urlresolver functions that return fully qualified URLs or view names
"""
from django.urls import NoReverseMatch
from django.urls import reverse as django_reverse
from django.utils.functional import lazy

from rest_framework.settings import api_settings
from rest_framework.utils.urls import replace_query_param


def preserve_builtin_query_params(url, request=None):
    """
    Given an incoming request, and an outgoing URL representation,
    append the value of any built-in query parameters.
    """
    if request is None:
        return url

    overrides = [
        api_settings.URL_FORMAT_OVERRIDE,
    ]

    for param in overrides:
        if param and (param in request.GET):
            value = request.GET[param]
            url = replace_query_param(url, param, value)

    return url


def reverse(viewname, args=None, kwargs=None, request=None, format=None, **extra):
    """
    If versioning is being used then we pass any `reverse` calls through
    to the versioning scheme instance, so that the resulting URL
    can be modified if needed.
    """
    scheme = getattr(request, 'versioning_scheme', None)
    if scheme is not None:
        try:
            url = scheme.reverse(viewname, args, kwargs, request, format, **extra)
        except NoReverseMatch:
            # In case the versioning scheme reversal fails, fallback to the
            # default implementation
            url = _reverse(viewname, args, kwargs, request, format, **extra)
    else:
        url = _reverse(viewname, args, kwargs, request, format, **extra)

    return preserve_builtin_query_params(url, request)


def _reverse(viewname, args=None, kwargs=None, request=None, format=None, **extra):
    """
    Same as `django.urls.reverse`, but optionally takes a request
    and returns a fully qualified URL, using the request to get the base URL.
    """
    if format is not None:
        kwargs = kwargs or {}
        kwargs['format'] = format
    url = django_reverse(viewname, args=args, kwargs=kwargs, **extra)
    if request:
        return request.build_absolute_uri(url)
    return url


reverse_lazy = lazy(reverse, str)
