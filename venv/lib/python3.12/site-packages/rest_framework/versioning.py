import re

from django.utils.translation import gettext_lazy as _

from rest_framework import exceptions
from rest_framework.compat import unicode_http_header
from rest_framework.reverse import _reverse
from rest_framework.settings import api_settings
from rest_framework.templatetags.rest_framework import replace_query_param
from rest_framework.utils.mediatypes import _MediaType


class BaseVersioning:
    default_version = api_settings.DEFAULT_VERSION
    allowed_versions = api_settings.ALLOWED_VERSIONS
    version_param = api_settings.VERSION_PARAM

    def determine_version(self, request, *args, **kwargs):
        msg = '{cls}.determine_version() must be implemented.'
        raise NotImplementedError(msg.format(
            cls=self.__class__.__name__
        ))

    def reverse(self, viewname, args=None, kwargs=None, request=None, format=None, **extra):
        return _reverse(viewname, args, kwargs, request, format, **extra)

    def is_allowed_version(self, version):
        if not self.allowed_versions:
            return True
        return ((version is not None and version == self.default_version) or
                (version in self.allowed_versions))


class AcceptHeaderVersioning(BaseVersioning):
    """
    GET /something/ HTTP/1.1
    Host: example.com
    Accept: application/json; version=1.0
    """
    invalid_version_message = _('Invalid version in "Accept" header.')

    def determine_version(self, request, *args, **kwargs):
        media_type = _MediaType(request.accepted_media_type)
        version = media_type.params.get(self.version_param, self.default_version)
        version = unicode_http_header(version)
        if not self.is_allowed_version(version):
            raise exceptions.NotAcceptable(self.invalid_version_message)
        return version

    # We don't need to implement `reverse`, as the versioning is based
    # on the `Accept` header, not on the request URL.


class URLPathVersioning(BaseVersioning):
    """
    To the client this is the same style as `NamespaceVersioning`.
    The difference is in the backend - this implementation uses
    Django's URL keyword arguments to determine the version.

    An example URL conf for two views that accept two different versions.

    urlpatterns = [
        re_path(r'^(?P<version>[v1|v2]+)/users/$', users_list, name='users-list'),
        re_path(r'^(?P<version>[v1|v2]+)/users/(?P<pk>[0-9]+)/$', users_detail, name='users-detail')
    ]

    GET /1.0/something/ HTTP/1.1
    Host: example.com
    Accept: application/json
    """
    invalid_version_message = _('Invalid version in URL path.')

    def determine_version(self, request, *args, **kwargs):
        version = kwargs.get(self.version_param, self.default_version)
        if version is None:
            version = self.default_version

        if not self.is_allowed_version(version):
            raise exceptions.NotFound(self.invalid_version_message)
        return version

    def reverse(self, viewname, args=None, kwargs=None, request=None, format=None, **extra):
        if request.version is not None:
            kwargs = {} if (kwargs is None) else kwargs
            kwargs[self.version_param] = request.version

        return super().reverse(
            viewname, args, kwargs, request, format, **extra
        )


class NamespaceVersioning(BaseVersioning):
    """
    To the client this is the same style as `URLPathVersioning`.
    The difference is in the backend - this implementation uses
    Django's URL namespaces to determine the version.

    An example URL conf that is namespaced into two separate versions

    # users/urls.py
    urlpatterns = [
        path('/users/', users_list, name='users-list'),
        path('/users/<int:pk>/', users_detail, name='users-detail')
    ]

    # urls.py
    urlpatterns = [
        path('v1/', include('users.urls', namespace='v1')),
        path('v2/', include('users.urls', namespace='v2'))
    ]

    GET /1.0/something/ HTTP/1.1
    Host: example.com
    Accept: application/json
    """
    invalid_version_message = _('Invalid version in URL path. Does not match any version namespace.')

    def determine_version(self, request, *args, **kwargs):
        resolver_match = getattr(request, 'resolver_match', None)
        if resolver_match is None or not resolver_match.namespace:
            return self.default_version

        # Allow for possibly nested namespaces.
        possible_versions = resolver_match.namespace.split(':')
        for version in possible_versions:
            if self.is_allowed_version(version):
                return version
        raise exceptions.NotFound(self.invalid_version_message)

    def reverse(self, viewname, args=None, kwargs=None, request=None, format=None, **extra):
        if request.version is not None:
            viewname = self.get_versioned_viewname(viewname, request)
        return super().reverse(
            viewname, args, kwargs, request, format, **extra
        )

    def get_versioned_viewname(self, viewname, request):
        return request.version + ':' + viewname


class HostNameVersioning(BaseVersioning):
    """
    GET /something/ HTTP/1.1
    Host: v1.example.com
    Accept: application/json
    """
    hostname_regex = re.compile(r'^([a-zA-Z0-9]+)\.[a-zA-Z0-9]+\.[a-zA-Z0-9]+$')
    invalid_version_message = _('Invalid version in hostname.')

    def determine_version(self, request, *args, **kwargs):
        hostname, separator, port = request.get_host().partition(':')
        match = self.hostname_regex.match(hostname)
        if not match:
            return self.default_version
        version = match.group(1)
        if not self.is_allowed_version(version):
            raise exceptions.NotFound(self.invalid_version_message)
        return version

    # We don't need to implement `reverse`, as the hostname will already be
    # preserved as part of the REST framework `reverse` implementation.


class QueryParameterVersioning(BaseVersioning):
    """
    GET /something/?version=0.1 HTTP/1.1
    Host: example.com
    Accept: application/json
    """
    invalid_version_message = _('Invalid version in query parameter.')

    def determine_version(self, request, *args, **kwargs):
        version = request.query_params.get(self.version_param, self.default_version)
        if not self.is_allowed_version(version):
            raise exceptions.NotFound(self.invalid_version_message)
        return version

    def reverse(self, viewname, args=None, kwargs=None, request=None, format=None, **extra):
        url = super().reverse(
            viewname, args, kwargs, request, format, **extra
        )
        if request.version is not None:
            return replace_query_param(url, self.version_param, request.version)
        return url
