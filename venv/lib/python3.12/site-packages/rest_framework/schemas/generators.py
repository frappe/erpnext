"""
generators.py   # Top-down schema generation

See schemas.__init__.py for package overview.
"""
import re
from importlib import import_module

from django.conf import settings
from django.contrib.admindocs.views import simplify_regex
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.urls import URLPattern, URLResolver

from rest_framework import exceptions
from rest_framework.request import clone_request
from rest_framework.settings import api_settings
from rest_framework.utils.model_meta import _get_pk


def get_pk_name(model):
    meta = model._meta.concrete_model._meta
    return _get_pk(meta).name


def is_api_view(callback):
    """
    Return `True` if the given view callback is a REST framework view/viewset.
    """
    # Avoid import cycle on APIView
    from rest_framework.views import APIView
    cls = getattr(callback, 'cls', None)
    return (cls is not None) and issubclass(cls, APIView)


def endpoint_ordering(endpoint):
    path, method, callback = endpoint
    method_priority = {
        'GET': 0,
        'POST': 1,
        'PUT': 2,
        'PATCH': 3,
        'DELETE': 4
    }.get(method, 5)
    return (method_priority,)


_PATH_PARAMETER_COMPONENT_RE = re.compile(
    r'<(?:(?P<converter>[^>:]+):)?(?P<parameter>\w+)>'
)


class EndpointEnumerator:
    """
    A class to determine the available API endpoints that a project exposes.
    """
    def __init__(self, patterns=None, urlconf=None):
        if patterns is None:
            if urlconf is None:
                # Use the default Django URL conf
                urlconf = settings.ROOT_URLCONF

            # Load the given URLconf module
            if isinstance(urlconf, str):
                urls = import_module(urlconf)
            else:
                urls = urlconf
            patterns = urls.urlpatterns

        self.patterns = patterns

    def get_api_endpoints(self, patterns=None, prefix=''):
        """
        Return a list of all available API endpoints by inspecting the URL conf.
        """
        if patterns is None:
            patterns = self.patterns

        api_endpoints = []

        for pattern in patterns:
            path_regex = prefix + str(pattern.pattern)
            if isinstance(pattern, URLPattern):
                path = self.get_path_from_regex(path_regex)
                callback = pattern.callback
                if self.should_include_endpoint(path, callback):
                    for method in self.get_allowed_methods(callback):
                        endpoint = (path, method, callback)
                        api_endpoints.append(endpoint)

            elif isinstance(pattern, URLResolver):
                nested_endpoints = self.get_api_endpoints(
                    patterns=pattern.url_patterns,
                    prefix=path_regex
                )
                api_endpoints.extend(nested_endpoints)

        return sorted(api_endpoints, key=endpoint_ordering)

    def get_path_from_regex(self, path_regex):
        """
        Given a URL conf regex, return a URI template string.
        """
        # ???: Would it be feasible to adjust this such that we generate the
        # path, plus the kwargs, plus the type from the convertor, such that we
        # could feed that straight into the parameter schema object?

        path = simplify_regex(path_regex)

        # Strip Django 2.0 convertors as they are incompatible with uritemplate format
        return re.sub(_PATH_PARAMETER_COMPONENT_RE, r'{\g<parameter>}', path)

    def should_include_endpoint(self, path, callback):
        """
        Return `True` if the given endpoint should be included.
        """
        if not is_api_view(callback):
            return False  # Ignore anything except REST framework views.

        if callback.cls.schema is None:
            return False

        if 'schema' in callback.initkwargs:
            if callback.initkwargs['schema'] is None:
                return False

        if path.endswith('.{format}') or path.endswith('.{format}/'):
            return False  # Ignore .json style URLs.

        return True

    def get_allowed_methods(self, callback):
        """
        Return a list of the valid HTTP methods for this endpoint.
        """
        if hasattr(callback, 'actions'):
            actions = set(callback.actions)
            http_method_names = set(callback.cls.http_method_names)
            methods = [method.upper() for method in actions & http_method_names]
        else:
            methods = callback.cls().allowed_methods

        return [method for method in methods if method not in ('OPTIONS', 'HEAD')]


class BaseSchemaGenerator:
    endpoint_inspector_cls = EndpointEnumerator

    # 'pk' isn't great as an externally exposed name for an identifier,
    # so by default we prefer to use the actual model field name for schemas.
    # Set by 'SCHEMA_COERCE_PATH_PK'.
    coerce_path_pk = None

    def __init__(self, title=None, url=None, description=None, patterns=None, urlconf=None, version=None):
        if url and not url.endswith('/'):
            url += '/'

        self.coerce_path_pk = api_settings.SCHEMA_COERCE_PATH_PK

        self.patterns = patterns
        self.urlconf = urlconf
        self.title = title
        self.description = description
        self.version = version
        self.url = url
        self.endpoints = None

    def _initialise_endpoints(self):
        if self.endpoints is None:
            inspector = self.endpoint_inspector_cls(self.patterns, self.urlconf)
            self.endpoints = inspector.get_api_endpoints()

    def _get_paths_and_endpoints(self, request):
        """
        Generate (path, method, view) given (path, method, callback) for paths.
        """
        paths = []
        view_endpoints = []
        for path, method, callback in self.endpoints:
            view = self.create_view(callback, method, request)
            path = self.coerce_path(path, method, view)
            paths.append(path)
            view_endpoints.append((path, method, view))

        return paths, view_endpoints

    def create_view(self, callback, method, request=None):
        """
        Given a callback, return an actual view instance.
        """
        view = callback.cls(**getattr(callback, 'initkwargs', {}))
        view.args = ()
        view.kwargs = {}
        view.format_kwarg = None
        view.request = None
        view.action_map = getattr(callback, 'actions', None)

        actions = getattr(callback, 'actions', None)
        if actions is not None:
            if method == 'OPTIONS':
                view.action = 'metadata'
            else:
                view.action = actions.get(method.lower())

        if request is not None:
            view.request = clone_request(request, method)

        return view

    def coerce_path(self, path, method, view):
        """
        Coerce {pk} path arguments into the name of the model field,
        where possible. This is cleaner for an external representation.
        (Ie. "this is an identifier", not "this is a database primary key")
        """
        if not self.coerce_path_pk or '{pk}' not in path:
            return path
        model = getattr(getattr(view, 'queryset', None), 'model', None)
        if model:
            field_name = get_pk_name(model)
        else:
            field_name = 'id'
        return path.replace('{pk}', '{%s}' % field_name)

    def get_schema(self, request=None, public=False):
        raise NotImplementedError(".get_schema() must be implemented in subclasses.")

    def has_view_permissions(self, path, method, view):
        """
        Return `True` if the incoming request has the correct view permissions.
        """
        if view.request is None:
            return True

        try:
            view.check_permissions(view.request)
        except (exceptions.APIException, Http404, PermissionDenied):
            return False
        return True
