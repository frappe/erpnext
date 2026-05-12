"""
The most important decorator in this module is `@api_view`, which is used
for writing function-based views with REST framework.

There are also various decorators for setting the API policies on function
based views, as well as the `@action` decorator, which is used to annotate
methods on viewsets that should be included by routers.
"""
import types

from django.forms.utils import pretty_name

from rest_framework.views import APIView


def api_view(http_method_names=None):
    """
    Decorator that converts a function-based view into an APIView subclass.
    Takes a list of allowed methods for the view as an argument.
    """
    http_method_names = ['GET'] if (http_method_names is None) else http_method_names

    def decorator(func):

        WrappedAPIView = type(
            'WrappedAPIView',
            (APIView,),
            {'__doc__': func.__doc__}
        )

        # Note, the above allows us to set the docstring.
        # It is the equivalent of:
        #
        #     class WrappedAPIView(APIView):
        #         pass
        #     WrappedAPIView.__doc__ = func.doc    <--- Not possible to do this

        # api_view applied without (method_names)
        assert not(isinstance(http_method_names, types.FunctionType)), \
            '@api_view missing list of allowed HTTP methods'

        # api_view applied with eg. string instead of list of strings
        assert isinstance(http_method_names, (list, tuple)), \
            '@api_view expected a list of strings, received %s' % type(http_method_names).__name__

        allowed_methods = set(http_method_names) | {'options'}
        WrappedAPIView.http_method_names = [method.lower() for method in allowed_methods]

        def handler(self, *args, **kwargs):
            return func(*args, **kwargs)

        for method in http_method_names:
            setattr(WrappedAPIView, method.lower(), handler)

        WrappedAPIView.__name__ = func.__name__
        WrappedAPIView.__module__ = func.__module__

        WrappedAPIView.renderer_classes = getattr(func, 'renderer_classes',
                                                  APIView.renderer_classes)

        WrappedAPIView.parser_classes = getattr(func, 'parser_classes',
                                                APIView.parser_classes)

        WrappedAPIView.authentication_classes = getattr(func, 'authentication_classes',
                                                        APIView.authentication_classes)

        WrappedAPIView.throttle_classes = getattr(func, 'throttle_classes',
                                                  APIView.throttle_classes)

        WrappedAPIView.permission_classes = getattr(func, 'permission_classes',
                                                    APIView.permission_classes)

        WrappedAPIView.schema = getattr(func, 'schema',
                                        APIView.schema)

        return WrappedAPIView.as_view()

    return decorator


def renderer_classes(renderer_classes):
    def decorator(func):
        func.renderer_classes = renderer_classes
        return func
    return decorator


def parser_classes(parser_classes):
    def decorator(func):
        func.parser_classes = parser_classes
        return func
    return decorator


def authentication_classes(authentication_classes):
    def decorator(func):
        func.authentication_classes = authentication_classes
        return func
    return decorator


def throttle_classes(throttle_classes):
    def decorator(func):
        func.throttle_classes = throttle_classes
        return func
    return decorator


def permission_classes(permission_classes):
    def decorator(func):
        func.permission_classes = permission_classes
        return func
    return decorator


def schema(view_inspector):
    def decorator(func):
        func.schema = view_inspector
        return func
    return decorator


def action(methods=None, detail=None, url_path=None, url_name=None, **kwargs):
    """
    Mark a ViewSet method as a routable action.

    `@action`-decorated functions will be endowed with a `mapping` property,
    a `MethodMapper` that can be used to add additional method-based behaviors
    on the routed action.

    :param methods: A list of HTTP method names this action responds to.
                    Defaults to GET only.
    :param detail: Required. Determines whether this action applies to
                   instance/detail requests or collection/list requests.
    :param url_path: Define the URL segment for this action. Defaults to the
                     name of the method decorated.
    :param url_name: Define the internal (`reverse`) URL name for this action.
                     Defaults to the name of the method decorated with underscores
                     replaced with dashes.
    :param kwargs: Additional properties to set on the view.  This can be used
                   to override viewset-level *_classes settings, equivalent to
                   how the `@renderer_classes` etc. decorators work for function-
                   based API views.
    """
    methods = ['get'] if methods is None else methods
    methods = [method.lower() for method in methods]

    assert detail is not None, (
        "@action() missing required argument: 'detail'"
    )

    # name and suffix are mutually exclusive
    if 'name' in kwargs and 'suffix' in kwargs:
        raise TypeError("`name` and `suffix` are mutually exclusive arguments.")

    def decorator(func):
        func.mapping = MethodMapper(func, methods)

        func.detail = detail
        func.url_path = url_path if url_path else func.__name__
        func.url_name = url_name if url_name else func.__name__.replace('_', '-')

        # These kwargs will end up being passed to `ViewSet.as_view()` within
        # the router, which eventually delegates to Django's CBV `View`,
        # which assigns them as instance attributes for each request.
        func.kwargs = kwargs

        # Set descriptive arguments for viewsets
        if 'name' not in kwargs and 'suffix' not in kwargs:
            func.kwargs['name'] = pretty_name(func.__name__)
        func.kwargs['description'] = func.__doc__ or None

        return func
    return decorator


class MethodMapper(dict):
    """
    Enables mapping HTTP methods to different ViewSet methods for a single,
    logical action.

    Example usage:

        class MyViewSet(ViewSet):

            @action(detail=False)
            def example(self, request, **kwargs):
                ...

            @example.mapping.post
            def create_example(self, request, **kwargs):
                ...
    """

    def __init__(self, action, methods):
        self.action = action
        for method in methods:
            self[method] = self.action.__name__

    def _map(self, method, func):
        assert method not in self, (
            "Method '%s' has already been mapped to '.%s'." % (method, self[method]))
        assert func.__name__ != self.action.__name__, (
            "Method mapping does not behave like the property decorator. You "
            "cannot use the same method name for each mapping declaration.")

        self[method] = func.__name__

        return func

    def get(self, func):
        return self._map('get', func)

    def post(self, func):
        return self._map('post', func)

    def put(self, func):
        return self._map('put', func)

    def patch(self, func):
        return self._map('patch', func)

    def delete(self, func):
        return self._map('delete', func)

    def head(self, func):
        return self._map('head', func)

    def options(self, func):
        return self._map('options', func)

    def trace(self, func):
        return self._map('trace', func)
