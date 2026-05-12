import re
import warnings
from collections import OrderedDict
from decimal import Decimal
from operator import attrgetter
from urllib.parse import urljoin

from django.core.validators import (
    DecimalValidator, EmailValidator, MaxLengthValidator, MaxValueValidator,
    MinLengthValidator, MinValueValidator, RegexValidator, URLValidator
)
from django.db import models
from django.utils.encoding import force_str

from rest_framework import (
    RemovedInDRF315Warning, exceptions, renderers, serializers
)
from rest_framework.compat import uritemplate
from rest_framework.fields import _UnvalidatedField, empty
from rest_framework.settings import api_settings

from .generators import BaseSchemaGenerator
from .inspectors import ViewInspector
from .utils import get_pk_description, is_list_view


class SchemaGenerator(BaseSchemaGenerator):

    def get_info(self):
        # Title and version are required by openapi specification 3.x
        info = {
            'title': self.title or '',
            'version': self.version or ''
        }

        if self.description is not None:
            info['description'] = self.description

        return info

    def check_duplicate_operation_id(self, paths):
        ids = {}
        for route in paths:
            for method in paths[route]:
                if 'operationId' not in paths[route][method]:
                    continue
                operation_id = paths[route][method]['operationId']
                if operation_id in ids:
                    warnings.warn(
                        'You have a duplicated operationId in your OpenAPI schema: {operation_id}\n'
                        '\tRoute: {route1}, Method: {method1}\n'
                        '\tRoute: {route2}, Method: {method2}\n'
                        '\tAn operationId has to be unique across your schema. Your schema may not work in other tools.'
                        .format(
                            route1=ids[operation_id]['route'],
                            method1=ids[operation_id]['method'],
                            route2=route,
                            method2=method,
                            operation_id=operation_id
                        )
                    )
                ids[operation_id] = {
                    'route': route,
                    'method': method
                }

    def get_schema(self, request=None, public=False):
        """
        Generate a OpenAPI schema.
        """
        self._initialise_endpoints()
        components_schemas = {}

        # Iterate endpoints generating per method path operations.
        paths = {}
        _, view_endpoints = self._get_paths_and_endpoints(None if public else request)
        for path, method, view in view_endpoints:
            if not self.has_view_permissions(path, method, view):
                continue

            operation = view.schema.get_operation(path, method)
            components = view.schema.get_components(path, method)
            for k in components.keys():
                if k not in components_schemas:
                    continue
                if components_schemas[k] == components[k]:
                    continue
                warnings.warn('Schema component "{}" has been overriden with a different value.'.format(k))

            components_schemas.update(components)

            # Normalise path for any provided mount url.
            if path.startswith('/'):
                path = path[1:]
            path = urljoin(self.url or '/', path)

            paths.setdefault(path, {})
            paths[path][method.lower()] = operation

        self.check_duplicate_operation_id(paths)

        # Compile final schema.
        schema = {
            'openapi': '3.0.2',
            'info': self.get_info(),
            'paths': paths,
        }

        if len(components_schemas) > 0:
            schema['components'] = {
                'schemas': components_schemas
            }

        return schema

# View Inspectors


class AutoSchema(ViewInspector):

    def __init__(self, tags=None, operation_id_base=None, component_name=None):
        """
        :param operation_id_base: user-defined name in operationId. If empty, it will be deducted from the Model/Serializer/View name.
        :param component_name: user-defined component's name. If empty, it will be deducted from the Serializer's class name.
        """
        if tags and not all(isinstance(tag, str) for tag in tags):
            raise ValueError('tags must be a list or tuple of string.')
        self._tags = tags
        self.operation_id_base = operation_id_base
        self.component_name = component_name
        super().__init__()

    request_media_types = []
    response_media_types = []

    method_mapping = {
        'get': 'retrieve',
        'post': 'create',
        'put': 'update',
        'patch': 'partialUpdate',
        'delete': 'destroy',
    }

    def get_operation(self, path, method):
        operation = {}

        operation['operationId'] = self.get_operation_id(path, method)
        operation['description'] = self.get_description(path, method)

        parameters = []
        parameters += self.get_path_parameters(path, method)
        parameters += self.get_pagination_parameters(path, method)
        parameters += self.get_filter_parameters(path, method)
        operation['parameters'] = parameters

        request_body = self.get_request_body(path, method)
        if request_body:
            operation['requestBody'] = request_body
        operation['responses'] = self.get_responses(path, method)
        operation['tags'] = self.get_tags(path, method)

        return operation

    def get_component_name(self, serializer):
        """
        Compute the component's name from the serializer.
        Raise an exception if the serializer's class name is "Serializer" (case-insensitive).
        """
        if self.component_name is not None:
            return self.component_name

        # use the serializer's class name as the component name.
        component_name = serializer.__class__.__name__
        # We remove the "serializer" string from the class name.
        pattern = re.compile("serializer", re.IGNORECASE)
        component_name = pattern.sub("", component_name)

        if component_name == "":
            raise Exception(
                '"{}" is an invalid class name for schema generation. '
                'Serializer\'s class name should be unique and explicit. e.g. "ItemSerializer"'
                .format(serializer.__class__.__name__)
            )

        return component_name

    def get_components(self, path, method):
        """
        Return components with their properties from the serializer.
        """

        if method.lower() == 'delete':
            return {}

        request_serializer = self.get_request_serializer(path, method)
        response_serializer = self.get_response_serializer(path, method)

        components = {}

        if isinstance(request_serializer, serializers.Serializer):
            component_name = self.get_component_name(request_serializer)
            content = self.map_serializer(request_serializer)
            components.setdefault(component_name, content)

        if isinstance(response_serializer, serializers.Serializer):
            component_name = self.get_component_name(response_serializer)
            content = self.map_serializer(response_serializer)
            components.setdefault(component_name, content)

        return components

    def _to_camel_case(self, snake_str):
        components = snake_str.split('_')
        # We capitalize the first letter of each component except the first one
        # with the 'title' method and join them together.
        return components[0] + ''.join(x.title() for x in components[1:])

    def get_operation_id_base(self, path, method, action):
        """
        Compute the base part for operation ID from the model, serializer or view name.
        """
        model = getattr(getattr(self.view, 'queryset', None), 'model', None)

        if self.operation_id_base is not None:
            name = self.operation_id_base

        # Try to deduce the ID from the view's model
        elif model is not None:
            name = model.__name__

        # Try with the serializer class name
        elif self.get_serializer(path, method) is not None:
            name = self.get_serializer(path, method).__class__.__name__
            if name.endswith('Serializer'):
                name = name[:-10]

        # Fallback to the view name
        else:
            name = self.view.__class__.__name__
            if name.endswith('APIView'):
                name = name[:-7]
            elif name.endswith('View'):
                name = name[:-4]

            # Due to camel-casing of classes and `action` being lowercase, apply title in order to find if action truly
            # comes at the end of the name
            if name.endswith(action.title()):  # ListView, UpdateAPIView, ThingDelete ...
                name = name[:-len(action)]

        if action == 'list' and not name.endswith('s'):  # listThings instead of listThing
            name += 's'

        return name

    def get_operation_id(self, path, method):
        """
        Compute an operation ID from the view type and get_operation_id_base method.
        """
        method_name = getattr(self.view, 'action', method.lower())
        if is_list_view(path, method, self.view):
            action = 'list'
        elif method_name not in self.method_mapping:
            action = self._to_camel_case(method_name)
        else:
            action = self.method_mapping[method.lower()]

        name = self.get_operation_id_base(path, method, action)

        return action + name

    def get_path_parameters(self, path, method):
        """
        Return a list of parameters from templated path variables.
        """
        assert uritemplate, '`uritemplate` must be installed for OpenAPI schema support.'

        model = getattr(getattr(self.view, 'queryset', None), 'model', None)
        parameters = []

        for variable in uritemplate.variables(path):
            description = ''
            if model is not None:  # TODO: test this.
                # Attempt to infer a field description if possible.
                try:
                    model_field = model._meta.get_field(variable)
                except Exception:
                    model_field = None

                if model_field is not None and model_field.help_text:
                    description = force_str(model_field.help_text)
                elif model_field is not None and model_field.primary_key:
                    description = get_pk_description(model, model_field)

            parameter = {
                "name": variable,
                "in": "path",
                "required": True,
                "description": description,
                'schema': {
                    'type': 'string',  # TODO: integer, pattern, ...
                },
            }
            parameters.append(parameter)

        return parameters

    def get_filter_parameters(self, path, method):
        if not self.allows_filters(path, method):
            return []
        parameters = []
        for filter_backend in self.view.filter_backends:
            parameters += filter_backend().get_schema_operation_parameters(self.view)
        return parameters

    def allows_filters(self, path, method):
        """
        Determine whether to include filter Fields in schema.

        Default implementation looks for ModelViewSet or GenericAPIView
        actions/methods that cause filtering on the default implementation.
        """
        if getattr(self.view, 'filter_backends', None) is None:
            return False
        if hasattr(self.view, 'action'):
            return self.view.action in ["list", "retrieve", "update", "partial_update", "destroy"]
        return method.lower() in ["get", "put", "patch", "delete"]

    def get_pagination_parameters(self, path, method):
        view = self.view

        if not is_list_view(path, method, view):
            return []

        paginator = self.get_paginator()
        if not paginator:
            return []

        return paginator.get_schema_operation_parameters(view)

    def map_choicefield(self, field):
        choices = list(OrderedDict.fromkeys(field.choices))  # preserve order and remove duplicates
        if all(isinstance(choice, bool) for choice in choices):
            type = 'boolean'
        elif all(isinstance(choice, int) for choice in choices):
            type = 'integer'
        elif all(isinstance(choice, (int, float, Decimal)) for choice in choices):  # `number` includes `integer`
            # Ref: https://tools.ietf.org/html/draft-wright-json-schema-validation-00#section-5.21
            type = 'number'
        elif all(isinstance(choice, str) for choice in choices):
            type = 'string'
        else:
            type = None

        mapping = {
            # The value of `enum` keyword MUST be an array and SHOULD be unique.
            # Ref: https://tools.ietf.org/html/draft-wright-json-schema-validation-00#section-5.20
            'enum': choices
        }

        # If We figured out `type` then and only then we should set it. It must be a string.
        # Ref: https://swagger.io/docs/specification/data-models/data-types/#mixed-type
        # It is optional but it can not be null.
        # Ref: https://tools.ietf.org/html/draft-wright-json-schema-validation-00#section-5.21
        if type:
            mapping['type'] = type
        return mapping

    def map_field(self, field):

        # Nested Serializers, `many` or not.
        if isinstance(field, serializers.ListSerializer):
            return {
                'type': 'array',
                'items': self.map_serializer(field.child)
            }
        if isinstance(field, serializers.Serializer):
            data = self.map_serializer(field)
            data['type'] = 'object'
            return data

        # Related fields.
        if isinstance(field, serializers.ManyRelatedField):
            return {
                'type': 'array',
                'items': self.map_field(field.child_relation)
            }
        if isinstance(field, serializers.PrimaryKeyRelatedField):
            model = getattr(field.queryset, 'model', None)
            if model is not None:
                model_field = model._meta.pk
                if isinstance(model_field, models.AutoField):
                    return {'type': 'integer'}

        # ChoiceFields (single and multiple).
        # Q:
        # - Is 'type' required?
        # - can we determine the TYPE of a choicefield?
        if isinstance(field, serializers.MultipleChoiceField):
            return {
                'type': 'array',
                'items': self.map_choicefield(field)
            }

        if isinstance(field, serializers.ChoiceField):
            return self.map_choicefield(field)

        # ListField.
        if isinstance(field, serializers.ListField):
            mapping = {
                'type': 'array',
                'items': {},
            }
            if not isinstance(field.child, _UnvalidatedField):
                mapping['items'] = self.map_field(field.child)
            return mapping

        # DateField and DateTimeField type is string
        if isinstance(field, serializers.DateField):
            return {
                'type': 'string',
                'format': 'date',
            }

        if isinstance(field, serializers.DateTimeField):
            return {
                'type': 'string',
                'format': 'date-time',
            }

        # "Formats such as "email", "uuid", and so on, MAY be used even though undefined by this specification."
        # see: https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.2.md#data-types
        # see also: https://swagger.io/docs/specification/data-models/data-types/#string
        if isinstance(field, serializers.EmailField):
            return {
                'type': 'string',
                'format': 'email'
            }

        if isinstance(field, serializers.URLField):
            return {
                'type': 'string',
                'format': 'uri'
            }

        if isinstance(field, serializers.UUIDField):
            return {
                'type': 'string',
                'format': 'uuid'
            }

        if isinstance(field, serializers.IPAddressField):
            content = {
                'type': 'string',
            }
            if field.protocol != 'both':
                content['format'] = field.protocol
            return content

        if isinstance(field, serializers.DecimalField):
            if getattr(field, 'coerce_to_string', api_settings.COERCE_DECIMAL_TO_STRING):
                content = {
                    'type': 'string',
                    'format': 'decimal',
                }
            else:
                content = {
                    'type': 'number'
                }

            if field.decimal_places:
                content['multipleOf'] = float('.' + (field.decimal_places - 1) * '0' + '1')
            if field.max_whole_digits:
                content['maximum'] = int(field.max_whole_digits * '9') + 1
                content['minimum'] = -content['maximum']
            self._map_min_max(field, content)
            return content

        if isinstance(field, serializers.FloatField):
            content = {
                'type': 'number',
            }
            self._map_min_max(field, content)
            return content

        if isinstance(field, serializers.IntegerField):
            content = {
                'type': 'integer'
            }
            self._map_min_max(field, content)
            # 2147483647 is max for int32_size, so we use int64 for format
            if int(content.get('maximum', 0)) > 2147483647 or int(content.get('minimum', 0)) > 2147483647:
                content['format'] = 'int64'
            return content

        if isinstance(field, serializers.FileField):
            return {
                'type': 'string',
                'format': 'binary'
            }

        # Simplest cases, default to 'string' type:
        FIELD_CLASS_SCHEMA_TYPE = {
            serializers.BooleanField: 'boolean',
            serializers.JSONField: 'object',
            serializers.DictField: 'object',
            serializers.HStoreField: 'object',
        }
        return {'type': FIELD_CLASS_SCHEMA_TYPE.get(field.__class__, 'string')}

    def _map_min_max(self, field, content):
        if field.max_value:
            content['maximum'] = field.max_value
        if field.min_value:
            content['minimum'] = field.min_value

    def map_serializer(self, serializer):
        # Assuming we have a valid serializer instance.
        required = []
        properties = {}

        for field in serializer.fields.values():
            if isinstance(field, serializers.HiddenField):
                continue

            if field.required:
                required.append(field.field_name)

            schema = self.map_field(field)
            if field.read_only:
                schema['readOnly'] = True
            if field.write_only:
                schema['writeOnly'] = True
            if field.allow_null:
                schema['nullable'] = True
            if field.default is not None and field.default != empty and not callable(field.default):
                schema['default'] = field.default
            if field.help_text:
                schema['description'] = str(field.help_text)
            self.map_field_validators(field, schema)

            properties[field.field_name] = schema

        result = {
            'type': 'object',
            'properties': properties
        }
        if required:
            result['required'] = required

        return result

    def map_field_validators(self, field, schema):
        """
        map field validators
        """
        for v in field.validators:
            # "Formats such as "email", "uuid", and so on, MAY be used even though undefined by this specification."
            # https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.2.md#data-types
            if isinstance(v, EmailValidator):
                schema['format'] = 'email'
            if isinstance(v, URLValidator):
                schema['format'] = 'uri'
            if isinstance(v, RegexValidator):
                # In Python, the token \Z does what \z does in other engines.
                # https://stackoverflow.com/questions/53283160
                schema['pattern'] = v.regex.pattern.replace('\\Z', '\\z')
            elif isinstance(v, MaxLengthValidator):
                attr_name = 'maxLength'
                if isinstance(field, serializers.ListField):
                    attr_name = 'maxItems'
                schema[attr_name] = v.limit_value
            elif isinstance(v, MinLengthValidator):
                attr_name = 'minLength'
                if isinstance(field, serializers.ListField):
                    attr_name = 'minItems'
                schema[attr_name] = v.limit_value
            elif isinstance(v, MaxValueValidator):
                schema['maximum'] = v.limit_value
            elif isinstance(v, MinValueValidator):
                schema['minimum'] = v.limit_value
            elif isinstance(v, DecimalValidator) and \
                    not getattr(field, 'coerce_to_string', api_settings.COERCE_DECIMAL_TO_STRING):
                if v.decimal_places:
                    schema['multipleOf'] = float('.' + (v.decimal_places - 1) * '0' + '1')
                if v.max_digits:
                    digits = v.max_digits
                    if v.decimal_places is not None and v.decimal_places > 0:
                        digits -= v.decimal_places
                    schema['maximum'] = int(digits * '9') + 1
                    schema['minimum'] = -schema['maximum']

    def get_paginator(self):
        pagination_class = getattr(self.view, 'pagination_class', None)
        if pagination_class:
            return pagination_class()
        return None

    def map_parsers(self, path, method):
        return list(map(attrgetter('media_type'), self.view.parser_classes))

    def map_renderers(self, path, method):
        media_types = []
        for renderer in self.view.renderer_classes:
            # BrowsableAPIRenderer not relevant to OpenAPI spec
            if issubclass(renderer, renderers.BrowsableAPIRenderer):
                continue
            media_types.append(renderer.media_type)
        return media_types

    def get_serializer(self, path, method):
        view = self.view

        if not hasattr(view, 'get_serializer'):
            return None

        try:
            return view.get_serializer()
        except exceptions.APIException:
            warnings.warn('{}.get_serializer() raised an exception during '
                          'schema generation. Serializer fields will not be '
                          'generated for {} {}.'
                          .format(view.__class__.__name__, method, path))
            return None

    def get_request_serializer(self, path, method):
        """
        Override this method if your view uses a different serializer for
        handling request body.
        """
        return self.get_serializer(path, method)

    def get_response_serializer(self, path, method):
        """
        Override this method if your view uses a different serializer for
        populating response data.
        """
        return self.get_serializer(path, method)

    def get_reference(self, serializer):
        return {'$ref': '#/components/schemas/{}'.format(self.get_component_name(serializer))}

    def get_request_body(self, path, method):
        if method not in ('PUT', 'PATCH', 'POST'):
            return {}

        self.request_media_types = self.map_parsers(path, method)

        serializer = self.get_request_serializer(path, method)

        if not isinstance(serializer, serializers.Serializer):
            item_schema = {}
        else:
            item_schema = self.get_reference(serializer)

        return {
            'content': {
                ct: {'schema': item_schema}
                for ct in self.request_media_types
            }
        }

    def get_responses(self, path, method):
        if method == 'DELETE':
            return {
                '204': {
                    'description': ''
                }
            }

        self.response_media_types = self.map_renderers(path, method)

        serializer = self.get_response_serializer(path, method)

        if not isinstance(serializer, serializers.Serializer):
            item_schema = {}
        else:
            item_schema = self.get_reference(serializer)

        if is_list_view(path, method, self.view):
            response_schema = {
                'type': 'array',
                'items': item_schema,
            }
            paginator = self.get_paginator()
            if paginator:
                response_schema = paginator.get_paginated_response_schema(response_schema)
        else:
            response_schema = item_schema
        status_code = '201' if method == 'POST' else '200'
        return {
            status_code: {
                'content': {
                    ct: {'schema': response_schema}
                    for ct in self.response_media_types
                },
                # description is a mandatory property,
                # https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.2.md#responseObject
                # TODO: put something meaningful into it
                'description': ""
            }
        }

    def get_tags(self, path, method):
        # If user have specified tags, use them.
        if self._tags:
            return self._tags

        # First element of a specific path could be valid tag. This is a fallback solution.
        # PUT, PATCH, GET(Retrieve), DELETE:        /user_profile/{id}/       tags = [user-profile]
        # POST, GET(List):                          /user_profile/            tags = [user-profile]
        if path.startswith('/'):
            path = path[1:]

        return [path.split('/')[0].replace('_', '-')]

    def _get_reference(self, serializer):
        warnings.warn(
            "Method `_get_reference()` has been renamed to `get_reference()`. "
            "The old name will be removed in DRF v3.15.",
            RemovedInDRF315Warning, stacklevel=2
        )
        return self.get_reference(serializer)
