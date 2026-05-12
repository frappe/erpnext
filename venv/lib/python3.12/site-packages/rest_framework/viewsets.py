"""
ViewSets are essentially just a type of class based view, that doesn't provide
any method handlers, such as `get()`, `post()`, etc... but instead has actions,
such as `list()`, `retrieve()`, `create()`, etc...

Actions are only bound to methods at the point of instantiating the views.

    user_list = UserViewSet.as_view({'get': 'list'})
    user_detail = UserViewSet.as_view({'get': 'retrieve'})

Typically, rather than instantiate views from viewsets directly, you'll
register the viewset with a router and let the URL conf be determined
automatically.

    router = DefaultRouter()
    router.register(r'users', UserViewSet, 'user')
    urlpatterns = router.urls
"""
from collections import OrderedDict
from functools import update_wrapper
from inspect import getmembers

from django.urls import NoReverseMatch
from django.utils.decorators import classonlymethod
from django.views.decorators.csrf import csrf_exempt

from rest_framework import generics, mixins, views
from rest_framework.decorators import MethodMapper
from rest_framework.reverse import reverse


def _is_extra_action(attr):
    return hasattr(attr, 'mapping') and isinstance(attr.mapping, MethodMapper)


def _check_attr_name(func, name):
    assert func.__name__ == name, (
        'Expected function (`{func.__name__}`) to match its attribute name '
        '(`{name}`). If using a decorator, ensure the inner function is '
        'decorated with `functools.wraps`, or that `{func.__name__}.__name__` '
        'is otherwise set to `{name}`.').format(func=func, name=name)
    return func


class ViewSetMixin:
    """
    This is the magic.

    Overrides `.as_view()` so that it takes an `actions` keyword that performs
    the binding of HTTP methods to actions on the Resource.

    For example, to create a concrete view binding the 'GET' and 'POST' methods
    to the 'list' and 'create' actions...

    view = MyViewSet.as_view({'get': 'list', 'post': 'create'})
    """

    @classonlymethod
    def as_view(cls, actions=None, **initkwargs):
        """
        Because of the way class based views create a closure around the
        instantiated view, we need to totally reimplement `.as_view`,
        and slightly modify the view function that is created and returned.
        """
        # The name and description initkwargs may be explicitly overridden for
        # certain route configurations. eg, names of extra actions.
        cls.name = None
        cls.description = None

        # The suffix initkwarg is reserved for displaying the viewset type.
        # This initkwarg should have no effect if the name is provided.
        # eg. 'List' or 'Instance'.
        cls.suffix = None

        # The detail initkwarg is reserved for introspecting the viewset type.
        cls.detail = None

        # Setting a basename allows a view to reverse its action urls. This
        # value is provided by the router through the initkwargs.
        cls.basename = None

        # actions must not be empty
        if not actions:
            raise TypeError("The `actions` argument must be provided when "
                            "calling `.as_view()` on a ViewSet. For example "
                            "`.as_view({'get': 'list'})`")

        # sanitize keyword arguments
        for key in initkwargs:
            if key in cls.http_method_names:
                raise TypeError("You tried to pass in the %s method name as a "
                                "keyword argument to %s(). Don't do that."
                                % (key, cls.__name__))
            if not hasattr(cls, key):
                raise TypeError("%s() received an invalid keyword %r" % (
                    cls.__name__, key))

        # name and suffix are mutually exclusive
        if 'name' in initkwargs and 'suffix' in initkwargs:
            raise TypeError("%s() received both `name` and `suffix`, which are "
                            "mutually exclusive arguments." % (cls.__name__))

        def view(request, *args, **kwargs):
            self = cls(**initkwargs)

            if 'get' in actions and 'head' not in actions:
                actions['head'] = actions['get']

            # We also store the mapping of request methods to actions,
            # so that we can later set the action attribute.
            # eg. `self.action = 'list'` on an incoming GET request.
            self.action_map = actions

            # Bind methods to actions
            # This is the bit that's different to a standard view
            for method, action in actions.items():
                handler = getattr(self, action)
                setattr(self, method, handler)

            self.request = request
            self.args = args
            self.kwargs = kwargs

            # And continue as usual
            return self.dispatch(request, *args, **kwargs)

        # take name and docstring from class
        update_wrapper(view, cls, updated=())

        # and possible attributes set by decorators
        # like csrf_exempt from dispatch
        update_wrapper(view, cls.dispatch, assigned=())

        # We need to set these on the view function, so that breadcrumb
        # generation can pick out these bits of information from a
        # resolved URL.
        view.cls = cls
        view.initkwargs = initkwargs
        view.actions = actions
        return csrf_exempt(view)

    def initialize_request(self, request, *args, **kwargs):
        """
        Set the `.action` attribute on the view, depending on the request method.
        """
        request = super().initialize_request(request, *args, **kwargs)
        method = request.method.lower()
        if method == 'options':
            # This is a special case as we always provide handling for the
            # options method in the base `View` class.
            # Unlike the other explicitly defined actions, 'metadata' is implicit.
            self.action = 'metadata'
        else:
            self.action = self.action_map.get(method)
        return request

    def reverse_action(self, url_name, *args, **kwargs):
        """
        Reverse the action for the given `url_name`.
        """
        url_name = '%s-%s' % (self.basename, url_name)
        namespace = None
        if self.request and self.request.resolver_match:
            namespace = self.request.resolver_match.namespace
        if namespace:
            url_name = namespace + ':' + url_name
        kwargs.setdefault('request', self.request)

        return reverse(url_name, *args, **kwargs)

    @classmethod
    def get_extra_actions(cls):
        """
        Get the methods that are marked as an extra ViewSet `@action`.
        """
        return [_check_attr_name(method, name)
                for name, method
                in getmembers(cls, _is_extra_action)]

    def get_extra_action_url_map(self):
        """
        Build a map of {names: urls} for the extra actions.

        This method will noop if `detail` was not provided as a view initkwarg.
        """
        action_urls = OrderedDict()

        # exit early if `detail` has not been provided
        if self.detail is None:
            return action_urls

        # filter for the relevant extra actions
        actions = [
            action for action in self.get_extra_actions()
            if action.detail == self.detail
        ]

        for action in actions:
            try:
                url_name = '%s-%s' % (self.basename, action.url_name)
                namespace = self.request.resolver_match.namespace
                if namespace:
                    url_name = '%s:%s' % (namespace, url_name)

                url = reverse(url_name, self.args, self.kwargs, request=self.request)
                view = self.__class__(**action.kwargs)
                action_urls[view.get_view_name()] = url
            except NoReverseMatch:
                pass  # URL requires additional arguments, ignore

        return action_urls


class ViewSet(ViewSetMixin, views.APIView):
    """
    The base ViewSet class does not provide any actions by default.
    """
    pass


class GenericViewSet(ViewSetMixin, generics.GenericAPIView):
    """
    The GenericViewSet class does not provide any actions by default,
    but does include the base set of generic view behavior, such as
    the `get_object` and `get_queryset` methods.
    """
    pass


class ReadOnlyModelViewSet(mixins.RetrieveModelMixin,
                           mixins.ListModelMixin,
                           GenericViewSet):
    """
    A viewset that provides default `list()` and `retrieve()` actions.
    """
    pass


class ModelViewSet(mixins.CreateModelMixin,
                   mixins.RetrieveModelMixin,
                   mixins.UpdateModelMixin,
                   mixins.DestroyModelMixin,
                   mixins.ListModelMixin,
                   GenericViewSet):
    """
    A viewset that provides default `create()`, `retrieve()`, `update()`,
    `partial_update()`, `destroy()` and `list()` actions.
    """
    pass
