import warnings
from collections import Counter, OrderedDict
from urllib import parse

from django.db import models
from django.utils.encoding import force_str

from rest_framework import exceptions, serializers
from rest_framework.compat import coreapi, coreschema, uritemplate
from rest_framework.settings import api_settings

from .generators import BaseSchemaGenerator
from .inspectors import ViewInspector
from .utils import get_pk_description, is_list_view


def common_path(paths):
    split_paths = [path.strip('/').split('/') for path in paths]
    s1 = min(split_paths)
    s2 = max(split_paths)
    common = s1
    for i, c in enumerate(s1):
        if c != s2[i]:
            common = s1[:i]
            break
    return '/' + '/'.join(common)


def is_custom_action(action):
    return action not in {
        'retrieve', 'list', 'create', 'update', 'partial_update', 'destroy'
    }


def distribute_links(obj):
    for key, value in obj.items():
        distribute_links(value)

    for preferred_key, link in obj.links:
        key = obj.get_available_key(preferred_key)
        obj[key] = link


INSERT_INTO_COLLISION_FMT = """
Schema Naming Collision.

coreapi.Link for URL path {value_url} cannot be inserted into schema.
Position conflicts with coreapi.Link for URL path {target_url}.

Attempted to insert link with keys: {keys}.

Adjust URLs to avoid naming collision or override `SchemaGenerator.get_keys()`
to customise schema structure.
"""


class LinkNode(OrderedDict):
    def __init__(self):
        self.links = []
        self.methods_counter = Counter()
        super().__init__()

    def get_available_key(self, preferred_key):
        if preferred_key not in self:
            return preferred_key

        while True:
            current_val = self.methods_counter[preferred_key]
            self.methods_counter[preferred_key] += 1

            key = '{}_{}'.format(preferred_key, current_val)
            if key not in self:
                return key


def insert_into(target, keys, value):
    """
    Nested dictionary insertion.

    >>> example = {}
    >>> insert_into(example, ['a', 'b', 'c'], 123)
    >>> example
    LinkNode({'a': LinkNode({'b': LinkNode({'c': LinkNode(links=[123])}}})))
    """
    for key in keys[:-1]:
        if key not in target:
            target[key] = LinkNode()
        target = target[key]

    try:
        target.links.append((keys[-1], value))
    except TypeError:
        msg = INSERT_INTO_COLLISION_FMT.format(
            value_url=value.url,
            target_url=target.url,
            keys=keys
        )
        raise ValueError(msg)


class SchemaGenerator(BaseSchemaGenerator):
    """
    Original CoreAPI version.
    """
    # Map HTTP methods onto actions.
    default_mapping = {
        'get': 'retrieve',
        'post': 'create',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy',
    }

    # Map the method names we use for viewset actions onto external schema names.
    # These give us names that are more suitable for the external representation.
    # Set by 'SCHEMA_COERCE_METHOD_NAMES'.
    coerce_method_names = None

    def __init__(self, title=None, url=None, description=None, patterns=None, urlconf=None, version=None):
        assert coreapi, '`coreapi` must be installed for schema support.'
        assert coreschema, '`coreschema` must be installed for schema support.'

        super().__init__(title, url, description, patterns, urlconf)
        self.coerce_method_names = api_settings.SCHEMA_COERCE_METHOD_NAMES

    def get_links(self, request=None):
        """
        Return a dictionary containing all the links that should be
        included in the API schema.
        """
        links = LinkNode()

        paths, view_endpoints = self._get_paths_and_endpoints(request)

        # Only generate the path prefix for paths that will be included
        if not paths:
            return None
        prefix = self.determine_path_prefix(paths)

        for path, method, view in view_endpoints:
            if not self.has_view_permissions(path, method, view):
                continue
            link = view.schema.get_link(path, method, base_url=self.url)
            subpath = path[len(prefix):]
            keys = self.get_keys(subpath, method, view)
            insert_into(links, keys, link)

        return links

    def get_schema(self, request=None, public=False):
        """
        Generate a `coreapi.Document` representing the API schema.
        """
        self._initialise_endpoints()

        links = self.get_links(None if public else request)
        if not links:
            return None

        url = self.url
        if not url and request is not None:
            url = request.build_absolute_uri()

        distribute_links(links)
        return coreapi.Document(
            title=self.title, description=self.description,
            url=url, content=links
        )

    # Method for generating the link layout....
    def get_keys(self, subpath, method, view):
        """
        Return a list of keys that should be used to layout a link within
        the schema document.

        /users/                   ("users", "list"), ("users", "create")
        /users/{pk}/              ("users", "read"), ("users", "update"), ("users", "delete")
        /users/enabled/           ("users", "enabled")  # custom viewset list action
        /users/{pk}/star/         ("users", "star")     # custom viewset detail action
        /users/{pk}/groups/       ("users", "groups", "list"), ("users", "groups", "create")
        /users/{pk}/groups/{pk}/  ("users", "groups", "read"), ("users", "groups", "update"), ("users", "groups", "delete")
        """
        if hasattr(view, 'action'):
            # Viewsets have explicitly named actions.
            action = view.action
        else:
            # Views have no associated action, so we determine one from the method.
            if is_list_view(subpath, method, view):
                action = 'list'
            else:
                action = self.default_mapping[method.lower()]

        named_path_components = [
            component for component
            in subpath.strip('/').split('/')
            if '{' not in component
        ]

        if is_custom_action(action):
            # Custom action, eg "/users/{pk}/activate/", "/users/active/"
            mapped_methods = {
                # Don't count head mapping, e.g. not part of the schema
                method for method in view.action_map if method != 'head'
            }
            if len(mapped_methods) > 1:
                action = self.default_mapping[method.lower()]
                if action in self.coerce_method_names:
                    action = self.coerce_method_names[action]
                return named_path_components + [action]
            else:
                return named_path_components[:-1] + [action]

        if action in self.coerce_method_names:
            action = self.coerce_method_names[action]

        # Default action, eg "/users/", "/users/{pk}/"
        return named_path_components + [action]

    def determine_path_prefix(self, paths):
        """
        Given a list of all paths, return the common prefix which should be
        discounted when generating a schema structure.

        This will be the longest common string that does not include that last
        component of the URL, or the last component before a path parameter.

        For example:

        /api/v1/users/
        /api/v1/users/{pk}/

        The path prefix is '/api/v1'
        """
        prefixes = []
        for path in paths:
            components = path.strip('/').split('/')
            initial_components = []
            for component in components:
                if '{' in component:
                    break
                initial_components.append(component)
            prefix = '/'.join(initial_components[:-1])
            if not prefix:
                # We can just break early in the case that there's at least
                # one URL that doesn't have a path prefix.
                return '/'
            prefixes.append('/' + prefix + '/')
        return common_path(prefixes)

# View Inspectors #


def field_to_schema(field):
    title = force_str(field.label) if field.label else ''
    description = force_str(field.help_text) if field.help_text else ''

    if isinstance(field, (serializers.ListSerializer, serializers.ListField)):
        child_schema = field_to_schema(field.child)
        return coreschema.Array(
            items=child_schema,
            title=title,
            description=description
        )
    elif isinstance(field, serializers.DictField):
        return coreschema.Object(
            title=title,
            description=description
        )
    elif isinstance(field, serializers.Serializer):
        return coreschema.Object(
            properties=OrderedDict([
                (key, field_to_schema(value))
                for key, value
                in field.fields.items()
            ]),
            title=title,
            description=description
        )
    elif isinstance(field, serializers.ManyRelatedField):
        related_field_schema = field_to_schema(field.child_relation)

        return coreschema.Array(
            items=related_field_schema,
            title=title,
            description=description
        )
    elif isinstance(field, serializers.PrimaryKeyRelatedField):
        schema_cls = coreschema.String
        model = getattr(field.queryset, 'model', None)
        if model is not None:
            model_field = model._meta.pk
            if isinstance(model_field, models.AutoField):
                schema_cls = coreschema.Integer
        return schema_cls(title=title, description=description)
    elif isinstance(field, serializers.RelatedField):
        return coreschema.String(title=title, description=description)
    elif isinstance(field, serializers.MultipleChoiceField):
        return coreschema.Array(
            items=coreschema.Enum(enum=list(field.choices)),
            title=title,
            description=description
        )
    elif isinstance(field, serializers.ChoiceField):
        return coreschema.Enum(
            enum=list(field.choices),
            title=title,
            description=description
        )
    elif isinstance(field, serializers.BooleanField):
        return coreschema.Boolean(title=title, description=description)
    elif isinstance(field, (serializers.DecimalField, serializers.FloatField)):
        return coreschema.Number(title=title, description=description)
    elif isinstance(field, serializers.IntegerField):
        return coreschema.Integer(title=title, description=description)
    elif isinstance(field, serializers.DateField):
        return coreschema.String(
            title=title,
            description=description,
            format='date'
        )
    elif isinstance(field, serializers.DateTimeField):
        return coreschema.String(
            title=title,
            description=description,
            format='date-time'
        )
    elif isinstance(field, serializers.JSONField):
        return coreschema.Object(title=title, description=description)

    if field.style.get('base_template') == 'textarea.html':
        return coreschema.String(
            title=title,
            description=description,
            format='textarea'
        )

    return coreschema.String(title=title, description=description)


class AutoSchema(ViewInspector):
    """
    Default inspector for APIView

    Responsible for per-view introspection and schema generation.
    """
    def __init__(self, manual_fields=None):
        """
        Parameters:

        * `manual_fields`: list of `coreapi.Field` instances that
            will be added to auto-generated fields, overwriting on `Field.name`
        """
        super().__init__()
        if manual_fields is None:
            manual_fields = []
        self._manual_fields = manual_fields

    def get_link(self, path, method, base_url):
        """
        Generate `coreapi.Link` for self.view, path and method.

        This is the main _public_ access point.

        Parameters:

        * path: Route path for view from URLConf.
        * method: The HTTP request method.
        * base_url: The project "mount point" as given to SchemaGenerator
        """
        fields = self.get_path_fields(path, method)
        fields += self.get_serializer_fields(path, method)
        fields += self.get_pagination_fields(path, method)
        fields += self.get_filter_fields(path, method)

        manual_fields = self.get_manual_fields(path, method)
        fields = self.update_fields(fields, manual_fields)

        if fields and any([field.location in ('form', 'body') for field in fields]):
            encoding = self.get_encoding(path, method)
        else:
            encoding = None

        description = self.get_description(path, method)

        if base_url and path.startswith('/'):
            path = path[1:]

        return coreapi.Link(
            url=parse.urljoin(base_url, path),
            action=method.lower(),
            encoding=encoding,
            fields=fields,
            description=description
        )

    def get_path_fields(self, path, method):
        """
        Return a list of `coreapi.Field` instances corresponding to any
        templated path variables.
        """
        view = self.view
        model = getattr(getattr(view, 'queryset', None), 'model', None)
        fields = []

        for variable in uritemplate.variables(path):
            title = ''
            description = ''
            schema_cls = coreschema.String
            kwargs = {}
            if model is not None:
                # Attempt to infer a field description if possible.
                try:
                    model_field = model._meta.get_field(variable)
                except Exception:
                    model_field = None

                if model_field is not None and model_field.verbose_name:
                    title = force_str(model_field.verbose_name)

                if model_field is not None and model_field.help_text:
                    description = force_str(model_field.help_text)
                elif model_field is not None and model_field.primary_key:
                    description = get_pk_description(model, model_field)

                if hasattr(view, 'lookup_value_regex') and view.lookup_field == variable:
                    kwargs['pattern'] = view.lookup_value_regex
                elif isinstance(model_field, models.AutoField):
                    schema_cls = coreschema.Integer

            field = coreapi.Field(
                name=variable,
                location='path',
                required=True,
                schema=schema_cls(title=title, description=description, **kwargs)
            )
            fields.append(field)

        return fields

    def get_serializer_fields(self, path, method):
        """
        Return a list of `coreapi.Field` instances corresponding to any
        request body input, as determined by the serializer class.
        """
        view = self.view

        if method not in ('PUT', 'PATCH', 'POST'):
            return []

        if not hasattr(view, 'get_serializer'):
            return []

        try:
            serializer = view.get_serializer()
        except exceptions.APIException:
            serializer = None
            warnings.warn('{}.get_serializer() raised an exception during '
                          'schema generation. Serializer fields will not be '
                          'generated for {} {}.'
                          .format(view.__class__.__name__, method, path))

        if isinstance(serializer, serializers.ListSerializer):
            return [
                coreapi.Field(
                    name='data',
                    location='body',
                    required=True,
                    schema=coreschema.Array()
                )
            ]

        if not isinstance(serializer, serializers.Serializer):
            return []

        fields = []
        for field in serializer.fields.values():
            if field.read_only or isinstance(field, serializers.HiddenField):
                continue

            required = field.required and method != 'PATCH'
            field = coreapi.Field(
                name=field.field_name,
                location='form',
                required=required,
                schema=field_to_schema(field)
            )
            fields.append(field)

        return fields

    def get_pagination_fields(self, path, method):
        view = self.view

        if not is_list_view(path, method, view):
            return []

        pagination = getattr(view, 'pagination_class', None)
        if not pagination:
            return []

        paginator = view.pagination_class()
        return paginator.get_schema_fields(view)

    def _allows_filters(self, path, method):
        """
        Determine whether to include filter Fields in schema.

        Default implementation looks for ModelViewSet or GenericAPIView
        actions/methods that cause filtering on the default implementation.

        Override to adjust behaviour for your view.

        Note: Introduced in v3.7: Initially "private" (i.e. with leading underscore)
            to allow changes based on user experience.
        """
        if getattr(self.view, 'filter_backends', None) is None:
            return False

        if hasattr(self.view, 'action'):
            return self.view.action in ["list", "retrieve", "update", "partial_update", "destroy"]

        return method.lower() in ["get", "put", "patch", "delete"]

    def get_filter_fields(self, path, method):
        if not self._allows_filters(path, method):
            return []

        fields = []
        for filter_backend in self.view.filter_backends:
            fields += filter_backend().get_schema_fields(self.view)
        return fields

    def get_manual_fields(self, path, method):
        return self._manual_fields

    @staticmethod
    def update_fields(fields, update_with):
        """
        Update list of coreapi.Field instances, overwriting on `Field.name`.

        Utility function to handle replacing coreapi.Field fields
        from a list by name. Used to handle `manual_fields`.

        Parameters:

        * `fields`: list of `coreapi.Field` instances to update
        * `update_with: list of `coreapi.Field` instances to add or replace.
        """
        if not update_with:
            return fields

        by_name = OrderedDict((f.name, f) for f in fields)
        for f in update_with:
            by_name[f.name] = f
        fields = list(by_name.values())
        return fields

    def get_encoding(self, path, method):
        """
        Return the 'encoding' parameter to use for a given endpoint.
        """
        view = self.view

        # Core API supports the following request encodings over HTTP...
        supported_media_types = {
            'application/json',
            'application/x-www-form-urlencoded',
            'multipart/form-data',
        }
        parser_classes = getattr(view, 'parser_classes', [])
        for parser_class in parser_classes:
            media_type = getattr(parser_class, 'media_type', None)
            if media_type in supported_media_types:
                return media_type
            # Raw binary uploads are supported with "application/octet-stream"
            if media_type == '*/*':
                return 'application/octet-stream'

        return None


class ManualSchema(ViewInspector):
    """
    Allows providing a list of coreapi.Fields,
    plus an optional description.
    """
    def __init__(self, fields, description='', encoding=None):
        """
        Parameters:

        * `fields`: list of `coreapi.Field` instances.
        * `description`: String description for view. Optional.
        """
        super().__init__()
        assert all(isinstance(f, coreapi.Field) for f in fields), "`fields` must be a list of coreapi.Field instances"
        self._fields = fields
        self._description = description
        self._encoding = encoding

    def get_link(self, path, method, base_url):

        if base_url and path.startswith('/'):
            path = path[1:]

        return coreapi.Link(
            url=parse.urljoin(base_url, path),
            action=method.lower(),
            encoding=self._encoding,
            fields=self._fields,
            description=self._description
        )


def is_enabled():
    """Is CoreAPI Mode enabled?"""
    return issubclass(api_settings.DEFAULT_SCHEMA_CLASS, AutoSchema)
