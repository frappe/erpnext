import copy
import datetime
import decimal
import functools
import inspect
import re
import uuid
from collections import OrderedDict
from collections.abc import Mapping

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import (
    EmailValidator, MaxLengthValidator, MaxValueValidator, MinLengthValidator,
    MinValueValidator, ProhibitNullCharactersValidator, RegexValidator,
    URLValidator, ip_address_validators
)
from django.forms import FilePathField as DjangoFilePathField
from django.forms import ImageField as DjangoImageField
from django.utils import timezone
from django.utils.dateparse import (
    parse_date, parse_datetime, parse_duration, parse_time
)
from django.utils.duration import duration_string
from django.utils.encoding import is_protected_type, smart_str
from django.utils.formats import localize_input, sanitize_separators
from django.utils.ipv6 import clean_ipv6_address
from django.utils.translation import gettext_lazy as _
from pytz.exceptions import InvalidTimeError

from rest_framework import ISO_8601
from rest_framework.exceptions import ErrorDetail, ValidationError
from rest_framework.settings import api_settings
from rest_framework.utils import html, humanize_datetime, json, representation
from rest_framework.utils.formatting import lazy_format
from rest_framework.validators import ProhibitSurrogateCharactersValidator


class empty:
    """
    This class is used to represent no data being provided for a given input
    or output value.

    It is required because `None` may be a valid input or output value.
    """
    pass


class BuiltinSignatureError(Exception):
    """
    Built-in function signatures are not inspectable. This exception is raised
    so the serializer can raise a helpful error message.
    """
    pass


def is_simple_callable(obj):
    """
    True if the object is a callable that takes no arguments.
    """
    if not callable(obj):
        return False

    # Bail early since we cannot inspect built-in function signatures.
    if inspect.isbuiltin(obj):
        raise BuiltinSignatureError(
            'Built-in function signatures are not inspectable. '
            'Wrap the function call in a simple, pure Python function.')

    if not (inspect.isfunction(obj) or inspect.ismethod(obj) or isinstance(obj, functools.partial)):
        return False

    sig = inspect.signature(obj)
    params = sig.parameters.values()
    return all(
        param.kind == param.VAR_POSITIONAL or
        param.kind == param.VAR_KEYWORD or
        param.default != param.empty
        for param in params
    )


def get_attribute(instance, attrs):
    """
    Similar to Python's built in `getattr(instance, attr)`,
    but takes a list of nested attributes, instead of a single attribute.

    Also accepts either attribute lookup on objects or dictionary lookups.
    """
    for attr in attrs:
        try:
            if isinstance(instance, Mapping):
                instance = instance[attr]
            else:
                instance = getattr(instance, attr)
        except ObjectDoesNotExist:
            return None
        if is_simple_callable(instance):
            try:
                instance = instance()
            except (AttributeError, KeyError) as exc:
                # If we raised an Attribute or KeyError here it'd get treated
                # as an omitted field in `Field.get_attribute()`. Instead we
                # raise a ValueError to ensure the exception is not masked.
                raise ValueError('Exception raised in callable attribute "{}"; original exception was: {}'.format(attr, exc))

    return instance


def set_value(dictionary, keys, value):
    """
    Similar to Python's built in `dictionary[key] = value`,
    but takes a list of nested keys instead of a single key.

    set_value({'a': 1}, [], {'b': 2}) -> {'a': 1, 'b': 2}
    set_value({'a': 1}, ['x'], 2) -> {'a': 1, 'x': 2}
    set_value({'a': 1}, ['x', 'y'], 2) -> {'a': 1, 'x': {'y': 2}}
    """
    if not keys:
        dictionary.update(value)
        return

    for key in keys[:-1]:
        if key not in dictionary:
            dictionary[key] = {}
        dictionary = dictionary[key]

    dictionary[keys[-1]] = value


def to_choices_dict(choices):
    """
    Convert choices into key/value dicts.

    to_choices_dict([1]) -> {1: 1}
    to_choices_dict([(1, '1st'), (2, '2nd')]) -> {1: '1st', 2: '2nd'}
    to_choices_dict([('Group', ((1, '1st'), 2))]) -> {'Group': {1: '1st', 2: '2'}}
    """
    # Allow single, paired or grouped choices style:
    # choices = [1, 2, 3]
    # choices = [(1, 'First'), (2, 'Second'), (3, 'Third')]
    # choices = [('Category', ((1, 'First'), (2, 'Second'))), (3, 'Third')]
    ret = OrderedDict()
    for choice in choices:
        if not isinstance(choice, (list, tuple)):
            # single choice
            ret[choice] = choice
        else:
            key, value = choice
            if isinstance(value, (list, tuple)):
                # grouped choices (category, sub choices)
                ret[key] = to_choices_dict(value)
            else:
                # paired choice (key, display value)
                ret[key] = value
    return ret


def flatten_choices_dict(choices):
    """
    Convert a group choices dict into a flat dict of choices.

    flatten_choices_dict({1: '1st', 2: '2nd'}) -> {1: '1st', 2: '2nd'}
    flatten_choices_dict({'Group': {1: '1st', 2: '2nd'}}) -> {1: '1st', 2: '2nd'}
    """
    ret = OrderedDict()
    for key, value in choices.items():
        if isinstance(value, dict):
            # grouped choices (category, sub choices)
            for sub_key, sub_value in value.items():
                ret[sub_key] = sub_value
        else:
            # choice (key, display value)
            ret[key] = value
    return ret


def iter_options(grouped_choices, cutoff=None, cutoff_text=None):
    """
    Helper function for options and option groups in templates.
    """
    class StartOptionGroup:
        start_option_group = True
        end_option_group = False

        def __init__(self, label):
            self.label = label

    class EndOptionGroup:
        start_option_group = False
        end_option_group = True

    class Option:
        start_option_group = False
        end_option_group = False

        def __init__(self, value, display_text, disabled=False):
            self.value = value
            self.display_text = display_text
            self.disabled = disabled

    count = 0

    for key, value in grouped_choices.items():
        if cutoff and count >= cutoff:
            break

        if isinstance(value, dict):
            yield StartOptionGroup(label=key)
            for sub_key, sub_value in value.items():
                if cutoff and count >= cutoff:
                    break
                yield Option(value=sub_key, display_text=sub_value)
                count += 1
            yield EndOptionGroup()
        else:
            yield Option(value=key, display_text=value)
            count += 1

    if cutoff and count >= cutoff and cutoff_text:
        cutoff_text = cutoff_text.format(count=cutoff)
        yield Option(value='n/a', display_text=cutoff_text, disabled=True)


def get_error_detail(exc_info):
    """
    Given a Django ValidationError, return a list of ErrorDetail,
    with the `code` populated.
    """
    code = getattr(exc_info, 'code', None) or 'invalid'

    try:
        error_dict = exc_info.error_dict
    except AttributeError:
        return [
            ErrorDetail((error.message % error.params) if error.params else error.message,
                        code=error.code if error.code else code)
            for error in exc_info.error_list]
    return {
        k: [
            ErrorDetail((error.message % error.params) if error.params else error.message,
                        code=error.code if error.code else code)
            for error in errors
        ] for k, errors in error_dict.items()
    }


class CreateOnlyDefault:
    """
    This class may be used to provide default values that are only used
    for create operations, but that do not return any value for update
    operations.
    """
    requires_context = True

    def __init__(self, default):
        self.default = default

    def __call__(self, serializer_field):
        is_update = serializer_field.parent.instance is not None
        if is_update:
            raise SkipField()
        if callable(self.default):
            if getattr(self.default, 'requires_context', False):
                return self.default(serializer_field)
            else:
                return self.default()
        return self.default

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, repr(self.default))


class CurrentUserDefault:
    requires_context = True

    def __call__(self, serializer_field):
        return serializer_field.context['request'].user

    def __repr__(self):
        return '%s()' % self.__class__.__name__


class SkipField(Exception):
    pass


REGEX_TYPE = type(re.compile(''))

NOT_READ_ONLY_WRITE_ONLY = 'May not set both `read_only` and `write_only`'
NOT_READ_ONLY_REQUIRED = 'May not set both `read_only` and `required`'
NOT_REQUIRED_DEFAULT = 'May not set both `required` and `default`'
USE_READONLYFIELD = 'Field(read_only=True) should be ReadOnlyField'
MISSING_ERROR_MESSAGE = (
    'ValidationError raised by `{class_name}`, but error key `{key}` does '
    'not exist in the `error_messages` dictionary.'
)


class Field:
    _creation_counter = 0

    default_error_messages = {
        'required': _('This field is required.'),
        'null': _('This field may not be null.')
    }
    default_validators = []
    default_empty_html = empty
    initial = None

    def __init__(self, *, read_only=False, write_only=False,
                 required=None, default=empty, initial=empty, source=None,
                 label=None, help_text=None, style=None,
                 error_messages=None, validators=None, allow_null=False):
        self._creation_counter = Field._creation_counter
        Field._creation_counter += 1

        # If `required` is unset, then use `True` unless a default is provided.
        if required is None:
            required = default is empty and not read_only

        # Some combinations of keyword arguments do not make sense.
        assert not (read_only and write_only), NOT_READ_ONLY_WRITE_ONLY
        assert not (read_only and required), NOT_READ_ONLY_REQUIRED
        assert not (required and default is not empty), NOT_REQUIRED_DEFAULT
        assert not (read_only and self.__class__ == Field), USE_READONLYFIELD

        self.read_only = read_only
        self.write_only = write_only
        self.required = required
        self.default = default
        self.source = source
        self.initial = self.initial if (initial is empty) else initial
        self.label = label
        self.help_text = help_text
        self.style = {} if style is None else style
        self.allow_null = allow_null

        if self.default_empty_html is not empty:
            if default is not empty:
                self.default_empty_html = default

        if validators is not None:
            self.validators = list(validators)

        # These are set up by `.bind()` when the field is added to a serializer.
        self.field_name = None
        self.parent = None

        # Collect default error message from self and parent classes
        messages = {}
        for cls in reversed(self.__class__.__mro__):
            messages.update(getattr(cls, 'default_error_messages', {}))
        messages.update(error_messages or {})
        self.error_messages = messages

    def bind(self, field_name, parent):
        """
        Initializes the field name and parent for the field instance.
        Called when a field is added to the parent serializer instance.
        """

        # In order to enforce a consistent style, we error if a redundant
        # 'source' argument has been used. For example:
        # my_field = serializer.CharField(source='my_field')
        assert self.source != field_name, (
            "It is redundant to specify `source='%s'` on field '%s' in "
            "serializer '%s', because it is the same as the field name. "
            "Remove the `source` keyword argument." %
            (field_name, self.__class__.__name__, parent.__class__.__name__)
        )

        self.field_name = field_name
        self.parent = parent

        # `self.label` should default to being based on the field name.
        if self.label is None:
            self.label = field_name.replace('_', ' ').capitalize()

        # self.source should default to being the same as the field name.
        if self.source is None:
            self.source = field_name

        # self.source_attrs is a list of attributes that need to be looked up
        # when serializing the instance, or populating the validated data.
        if self.source == '*':
            self.source_attrs = []
        else:
            self.source_attrs = self.source.split('.')

    # .validators is a lazily loaded property, that gets its default
    # value from `get_validators`.
    @property
    def validators(self):
        if not hasattr(self, '_validators'):
            self._validators = self.get_validators()
        return self._validators

    @validators.setter
    def validators(self, validators):
        self._validators = validators

    def get_validators(self):
        return list(self.default_validators)

    def get_initial(self):
        """
        Return a value to use when the field is being returned as a primitive
        value, without any object instance.
        """
        if callable(self.initial):
            return self.initial()
        return self.initial

    def get_value(self, dictionary):
        """
        Given the *incoming* primitive data, return the value for this field
        that should be validated and transformed to a native value.
        """
        if html.is_html_input(dictionary):
            # HTML forms will represent empty fields as '', and cannot
            # represent None or False values directly.
            if self.field_name not in dictionary:
                if getattr(self.root, 'partial', False):
                    return empty
                return self.default_empty_html
            ret = dictionary[self.field_name]
            if ret == '' and self.allow_null:
                # If the field is blank, and null is a valid value then
                # determine if we should use null instead.
                return '' if getattr(self, 'allow_blank', False) else None
            elif ret == '' and not self.required:
                # If the field is blank, and emptiness is valid then
                # determine if we should use emptiness instead.
                return '' if getattr(self, 'allow_blank', False) else empty
            return ret
        return dictionary.get(self.field_name, empty)

    def get_attribute(self, instance):
        """
        Given the *outgoing* object instance, return the primitive value
        that should be used for this field.
        """
        try:
            return get_attribute(instance, self.source_attrs)
        except BuiltinSignatureError as exc:
            msg = (
                'Field source for `{serializer}.{field}` maps to a built-in '
                'function type and is invalid. Define a property or method on '
                'the `{instance}` instance that wraps the call to the built-in '
                'function.'.format(
                    serializer=self.parent.__class__.__name__,
                    field=self.field_name,
                    instance=instance.__class__.__name__,
                )
            )
            raise type(exc)(msg)
        except (KeyError, AttributeError) as exc:
            if self.default is not empty:
                return self.get_default()
            if self.allow_null:
                return None
            if not self.required:
                raise SkipField()
            msg = (
                'Got {exc_type} when attempting to get a value for field '
                '`{field}` on serializer `{serializer}`.\nThe serializer '
                'field might be named incorrectly and not match '
                'any attribute or key on the `{instance}` instance.\n'
                'Original exception text was: {exc}.'.format(
                    exc_type=type(exc).__name__,
                    field=self.field_name,
                    serializer=self.parent.__class__.__name__,
                    instance=instance.__class__.__name__,
                    exc=exc
                )
            )
            raise type(exc)(msg)

    def get_default(self):
        """
        Return the default value to use when validating data if no input
        is provided for this field.

        If a default has not been set for this field then this will simply
        raise `SkipField`, indicating that no value should be set in the
        validated data for this field.
        """
        if self.default is empty or getattr(self.root, 'partial', False):
            # No default, or this is a partial update.
            raise SkipField()
        if callable(self.default):
            if getattr(self.default, 'requires_context', False):
                return self.default(self)
            else:
                return self.default()

        return self.default

    def validate_empty_values(self, data):
        """
        Validate empty values, and either:

        * Raise `ValidationError`, indicating invalid data.
        * Raise `SkipField`, indicating that the field should be ignored.
        * Return (True, data), indicating an empty value that should be
          returned without any further validation being applied.
        * Return (False, data), indicating a non-empty value, that should
          have validation applied as normal.
        """
        if self.read_only:
            return (True, self.get_default())

        if data is empty:
            if getattr(self.root, 'partial', False):
                raise SkipField()
            if self.required:
                self.fail('required')
            return (True, self.get_default())

        if data is None:
            if not self.allow_null:
                self.fail('null')
            # Nullable `source='*'` fields should not be skipped when its named
            # field is given a null value. This is because `source='*'` means
            # the field is passed the entire object, which is not null.
            elif self.source == '*':
                return (False, None)
            return (True, None)

        return (False, data)

    def run_validation(self, data=empty):
        """
        Validate a simple representation and return the internal value.

        The provided data may be `empty` if no representation was included
        in the input.

        May raise `SkipField` if the field should not be included in the
        validated data.
        """
        (is_empty_value, data) = self.validate_empty_values(data)
        if is_empty_value:
            return data
        value = self.to_internal_value(data)
        self.run_validators(value)
        return value

    def run_validators(self, value):
        """
        Test the given value against all the validators on the field,
        and either raise a `ValidationError` or simply return.
        """
        errors = []
        for validator in self.validators:
            try:
                if getattr(validator, 'requires_context', False):
                    validator(value, self)
                else:
                    validator(value)
            except ValidationError as exc:
                # If the validation error contains a mapping of fields to
                # errors then simply raise it immediately rather than
                # attempting to accumulate a list of errors.
                if isinstance(exc.detail, dict):
                    raise
                errors.extend(exc.detail)
            except DjangoValidationError as exc:
                errors.extend(get_error_detail(exc))
        if errors:
            raise ValidationError(errors)

    def to_internal_value(self, data):
        """
        Transform the *incoming* primitive data into a native value.
        """
        raise NotImplementedError(
            '{cls}.to_internal_value() must be implemented for field '
            '{field_name}. If you do not need to support write operations '
            'you probably want to subclass `ReadOnlyField` instead.'.format(
                cls=self.__class__.__name__,
                field_name=self.field_name,
            )
        )

    def to_representation(self, value):
        """
        Transform the *outgoing* native value into primitive data.
        """
        raise NotImplementedError(
            '{cls}.to_representation() must be implemented for field {field_name}.'.format(
                cls=self.__class__.__name__,
                field_name=self.field_name,
            )
        )

    def fail(self, key, **kwargs):
        """
        A helper method that simply raises a validation error.
        """
        try:
            msg = self.error_messages[key]
        except KeyError:
            class_name = self.__class__.__name__
            msg = MISSING_ERROR_MESSAGE.format(class_name=class_name, key=key)
            raise AssertionError(msg)
        message_string = msg.format(**kwargs)
        raise ValidationError(message_string, code=key)

    @property
    def root(self):
        """
        Returns the top-level serializer for this field.
        """
        root = self
        while root.parent is not None:
            root = root.parent
        return root

    @property
    def context(self):
        """
        Returns the context as passed to the root serializer on initialization.
        """
        return getattr(self.root, '_context', {})

    def __new__(cls, *args, **kwargs):
        """
        When a field is instantiated, we store the arguments that were used,
        so that we can present a helpful representation of the object.
        """
        instance = super().__new__(cls)
        instance._args = args
        instance._kwargs = kwargs
        return instance

    def __deepcopy__(self, memo):
        """
        When cloning fields we instantiate using the arguments it was
        originally created with, rather than copying the complete state.
        """
        # Treat regexes and validators as immutable.
        # See https://github.com/encode/django-rest-framework/issues/1954
        # and https://github.com/encode/django-rest-framework/pull/4489
        args = [
            copy.deepcopy(item) if not isinstance(item, REGEX_TYPE) else item
            for item in self._args
        ]
        kwargs = {
            key: (copy.deepcopy(value, memo) if (key not in ('validators', 'regex')) else value)
            for key, value in self._kwargs.items()
        }
        return self.__class__(*args, **kwargs)

    def __repr__(self):
        """
        Fields are represented using their initial calling arguments.
        This allows us to create descriptive representations for serializer
        instances that show all the declared fields on the serializer.
        """
        return representation.field_repr(self)


# Boolean types...

class BooleanField(Field):
    default_error_messages = {
        'invalid': _('Must be a valid boolean.')
    }
    default_empty_html = False
    initial = False
    TRUE_VALUES = {
        't', 'T',
        'y', 'Y', 'yes', 'Yes', 'YES',
        'true', 'True', 'TRUE',
        'on', 'On', 'ON',
        '1', 1,
        True
    }
    FALSE_VALUES = {
        'f', 'F',
        'n', 'N', 'no', 'No', 'NO',
        'false', 'False', 'FALSE',
        'off', 'Off', 'OFF',
        '0', 0, 0.0,
        False
    }
    NULL_VALUES = {'null', 'Null', 'NULL', '', None}

    def to_internal_value(self, data):
        try:
            if data in self.TRUE_VALUES:
                return True
            elif data in self.FALSE_VALUES:
                return False
            elif data in self.NULL_VALUES and self.allow_null:
                return None
        except TypeError:  # Input is an unhashable type
            pass
        self.fail('invalid', input=data)

    def to_representation(self, value):
        if value in self.TRUE_VALUES:
            return True
        elif value in self.FALSE_VALUES:
            return False
        if value in self.NULL_VALUES and self.allow_null:
            return None
        return bool(value)


# String types...

class CharField(Field):
    default_error_messages = {
        'invalid': _('Not a valid string.'),
        'blank': _('This field may not be blank.'),
        'max_length': _('Ensure this field has no more than {max_length} characters.'),
        'min_length': _('Ensure this field has at least {min_length} characters.'),
    }
    initial = ''

    def __init__(self, **kwargs):
        self.allow_blank = kwargs.pop('allow_blank', False)
        self.trim_whitespace = kwargs.pop('trim_whitespace', True)
        self.max_length = kwargs.pop('max_length', None)
        self.min_length = kwargs.pop('min_length', None)
        super().__init__(**kwargs)
        if self.max_length is not None:
            message = lazy_format(self.error_messages['max_length'], max_length=self.max_length)
            self.validators.append(
                MaxLengthValidator(self.max_length, message=message))
        if self.min_length is not None:
            message = lazy_format(self.error_messages['min_length'], min_length=self.min_length)
            self.validators.append(
                MinLengthValidator(self.min_length, message=message))

        self.validators.append(ProhibitNullCharactersValidator())
        self.validators.append(ProhibitSurrogateCharactersValidator())

    def run_validation(self, data=empty):
        # Test for the empty string here so that it does not get validated,
        # and so that subclasses do not need to handle it explicitly
        # inside the `to_internal_value()` method.
        if data == '' or (self.trim_whitespace and str(data).strip() == ''):
            if not self.allow_blank:
                self.fail('blank')
            return ''
        return super().run_validation(data)

    def to_internal_value(self, data):
        # We're lenient with allowing basic numerics to be coerced into strings,
        # but other types should fail. Eg. unclear if booleans should represent as `true` or `True`,
        # and composites such as lists are likely user error.
        if isinstance(data, bool) or not isinstance(data, (str, int, float,)):
            self.fail('invalid')
        value = str(data)
        return value.strip() if self.trim_whitespace else value

    def to_representation(self, value):
        return str(value)


class EmailField(CharField):
    default_error_messages = {
        'invalid': _('Enter a valid email address.')
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        validator = EmailValidator(message=self.error_messages['invalid'])
        self.validators.append(validator)


class RegexField(CharField):
    default_error_messages = {
        'invalid': _('This value does not match the required pattern.')
    }

    def __init__(self, regex, **kwargs):
        super().__init__(**kwargs)
        validator = RegexValidator(regex, message=self.error_messages['invalid'])
        self.validators.append(validator)


class SlugField(CharField):
    default_error_messages = {
        'invalid': _('Enter a valid "slug" consisting of letters, numbers, underscores or hyphens.'),
        'invalid_unicode': _('Enter a valid "slug" consisting of Unicode letters, numbers, underscores, or hyphens.')
    }

    def __init__(self, allow_unicode=False, **kwargs):
        super().__init__(**kwargs)
        self.allow_unicode = allow_unicode
        if self.allow_unicode:
            validator = RegexValidator(re.compile(r'^[-\w]+\Z', re.UNICODE), message=self.error_messages['invalid_unicode'])
        else:
            validator = RegexValidator(re.compile(r'^[-a-zA-Z0-9_]+$'), message=self.error_messages['invalid'])
        self.validators.append(validator)


class URLField(CharField):
    default_error_messages = {
        'invalid': _('Enter a valid URL.')
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        validator = URLValidator(message=self.error_messages['invalid'])
        self.validators.append(validator)


class UUIDField(Field):
    valid_formats = ('hex_verbose', 'hex', 'int', 'urn')

    default_error_messages = {
        'invalid': _('Must be a valid UUID.'),
    }

    def __init__(self, **kwargs):
        self.uuid_format = kwargs.pop('format', 'hex_verbose')
        if self.uuid_format not in self.valid_formats:
            raise ValueError(
                'Invalid format for uuid representation. '
                'Must be one of "{}"'.format('", "'.join(self.valid_formats))
            )
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        if not isinstance(data, uuid.UUID):
            try:
                if isinstance(data, int):
                    return uuid.UUID(int=data)
                elif isinstance(data, str):
                    return uuid.UUID(hex=data)
                else:
                    self.fail('invalid', value=data)
            except (ValueError):
                self.fail('invalid', value=data)
        return data

    def to_representation(self, value):
        if self.uuid_format == 'hex_verbose':
            return str(value)
        else:
            return getattr(value, self.uuid_format)


class IPAddressField(CharField):
    """Support both IPAddressField and GenericIPAddressField"""

    default_error_messages = {
        'invalid': _('Enter a valid IPv4 or IPv6 address.'),
    }

    def __init__(self, protocol='both', **kwargs):
        self.protocol = protocol.lower()
        self.unpack_ipv4 = (self.protocol == 'both')
        super().__init__(**kwargs)
        validators, error_message = ip_address_validators(protocol, self.unpack_ipv4)
        self.validators.extend(validators)

    def to_internal_value(self, data):
        if not isinstance(data, str):
            self.fail('invalid', value=data)

        if ':' in data:
            try:
                if self.protocol in ('both', 'ipv6'):
                    return clean_ipv6_address(data, self.unpack_ipv4)
            except DjangoValidationError:
                self.fail('invalid', value=data)

        return super().to_internal_value(data)


# Number types...

class IntegerField(Field):
    default_error_messages = {
        'invalid': _('A valid integer is required.'),
        'max_value': _('Ensure this value is less than or equal to {max_value}.'),
        'min_value': _('Ensure this value is greater than or equal to {min_value}.'),
        'max_string_length': _('String value too large.')
    }
    MAX_STRING_LENGTH = 1000  # Guard against malicious string inputs.
    re_decimal = re.compile(r'\.0*\s*$')  # allow e.g. '1.0' as an int, but not '1.2'

    def __init__(self, **kwargs):
        self.max_value = kwargs.pop('max_value', None)
        self.min_value = kwargs.pop('min_value', None)
        super().__init__(**kwargs)
        if self.max_value is not None:
            message = lazy_format(self.error_messages['max_value'], max_value=self.max_value)
            self.validators.append(
                MaxValueValidator(self.max_value, message=message))
        if self.min_value is not None:
            message = lazy_format(self.error_messages['min_value'], min_value=self.min_value)
            self.validators.append(
                MinValueValidator(self.min_value, message=message))

    def to_internal_value(self, data):
        if isinstance(data, str) and len(data) > self.MAX_STRING_LENGTH:
            self.fail('max_string_length')

        try:
            data = int(self.re_decimal.sub('', str(data)))
        except (ValueError, TypeError):
            self.fail('invalid')
        return data

    def to_representation(self, value):
        return int(value)


class FloatField(Field):
    default_error_messages = {
        'invalid': _('A valid number is required.'),
        'max_value': _('Ensure this value is less than or equal to {max_value}.'),
        'min_value': _('Ensure this value is greater than or equal to {min_value}.'),
        'max_string_length': _('String value too large.')
    }
    MAX_STRING_LENGTH = 1000  # Guard against malicious string inputs.

    def __init__(self, **kwargs):
        self.max_value = kwargs.pop('max_value', None)
        self.min_value = kwargs.pop('min_value', None)
        super().__init__(**kwargs)
        if self.max_value is not None:
            message = lazy_format(self.error_messages['max_value'], max_value=self.max_value)
            self.validators.append(
                MaxValueValidator(self.max_value, message=message))
        if self.min_value is not None:
            message = lazy_format(self.error_messages['min_value'], min_value=self.min_value)
            self.validators.append(
                MinValueValidator(self.min_value, message=message))

    def to_internal_value(self, data):

        if isinstance(data, str) and len(data) > self.MAX_STRING_LENGTH:
            self.fail('max_string_length')

        try:
            return float(data)
        except (TypeError, ValueError):
            self.fail('invalid')

    def to_representation(self, value):
        return float(value)


class DecimalField(Field):
    default_error_messages = {
        'invalid': _('A valid number is required.'),
        'max_value': _('Ensure this value is less than or equal to {max_value}.'),
        'min_value': _('Ensure this value is greater than or equal to {min_value}.'),
        'max_digits': _('Ensure that there are no more than {max_digits} digits in total.'),
        'max_decimal_places': _('Ensure that there are no more than {max_decimal_places} decimal places.'),
        'max_whole_digits': _('Ensure that there are no more than {max_whole_digits} digits before the decimal point.'),
        'max_string_length': _('String value too large.')
    }
    MAX_STRING_LENGTH = 1000  # Guard against malicious string inputs.

    def __init__(self, max_digits, decimal_places, coerce_to_string=None, max_value=None, min_value=None,
                 localize=False, rounding=None, **kwargs):
        self.max_digits = max_digits
        self.decimal_places = decimal_places
        self.localize = localize
        if coerce_to_string is not None:
            self.coerce_to_string = coerce_to_string
        if self.localize:
            self.coerce_to_string = True

        self.max_value = max_value
        self.min_value = min_value

        if self.max_digits is not None and self.decimal_places is not None:
            self.max_whole_digits = self.max_digits - self.decimal_places
        else:
            self.max_whole_digits = None

        super().__init__(**kwargs)

        if self.max_value is not None:
            message = lazy_format(self.error_messages['max_value'], max_value=self.max_value)
            self.validators.append(
                MaxValueValidator(self.max_value, message=message))
        if self.min_value is not None:
            message = lazy_format(self.error_messages['min_value'], min_value=self.min_value)
            self.validators.append(
                MinValueValidator(self.min_value, message=message))

        if rounding is not None:
            valid_roundings = [v for k, v in vars(decimal).items() if k.startswith('ROUND_')]
            assert rounding in valid_roundings, (
                'Invalid rounding option %s. Valid values for rounding are: %s' % (rounding, valid_roundings))
        self.rounding = rounding

    def validate_empty_values(self, data):
        if smart_str(data).strip() == '' and self.allow_null:
            return (True, None)
        return super().validate_empty_values(data)

    def to_internal_value(self, data):
        """
        Validate that the input is a decimal number and return a Decimal
        instance.
        """

        data = smart_str(data).strip()

        if self.localize:
            data = sanitize_separators(data)

        if len(data) > self.MAX_STRING_LENGTH:
            self.fail('max_string_length')

        try:
            value = decimal.Decimal(data)
        except decimal.DecimalException:
            self.fail('invalid')

        if value.is_nan():
            self.fail('invalid')

        # Check for infinity and negative infinity.
        if value in (decimal.Decimal('Inf'), decimal.Decimal('-Inf')):
            self.fail('invalid')

        return self.quantize(self.validate_precision(value))

    def validate_precision(self, value):
        """
        Ensure that there are no more than max_digits in the number, and no
        more than decimal_places digits after the decimal point.

        Override this method to disable the precision validation for input
        values or to enhance it in any way you need to.
        """
        sign, digittuple, exponent = value.as_tuple()

        if exponent >= 0:
            # 1234500.0
            total_digits = len(digittuple) + exponent
            whole_digits = total_digits
            decimal_places = 0
        elif len(digittuple) > abs(exponent):
            # 123.45
            total_digits = len(digittuple)
            whole_digits = total_digits - abs(exponent)
            decimal_places = abs(exponent)
        else:
            # 0.001234
            total_digits = abs(exponent)
            whole_digits = 0
            decimal_places = total_digits

        if self.max_digits is not None and total_digits > self.max_digits:
            self.fail('max_digits', max_digits=self.max_digits)
        if self.decimal_places is not None and decimal_places > self.decimal_places:
            self.fail('max_decimal_places', max_decimal_places=self.decimal_places)
        if self.max_whole_digits is not None and whole_digits > self.max_whole_digits:
            self.fail('max_whole_digits', max_whole_digits=self.max_whole_digits)

        return value

    def to_representation(self, value):
        coerce_to_string = getattr(self, 'coerce_to_string', api_settings.COERCE_DECIMAL_TO_STRING)

        if value is None:
            if coerce_to_string:
                return ''
            else:
                return None

        if not isinstance(value, decimal.Decimal):
            value = decimal.Decimal(str(value).strip())

        quantized = self.quantize(value)

        if not coerce_to_string:
            return quantized
        if self.localize:
            return localize_input(quantized)

        return '{:f}'.format(quantized)

    def quantize(self, value):
        """
        Quantize the decimal value to the configured precision.
        """
        if self.decimal_places is None:
            return value

        context = decimal.getcontext().copy()
        if self.max_digits is not None:
            context.prec = self.max_digits
        return value.quantize(
            decimal.Decimal('.1') ** self.decimal_places,
            rounding=self.rounding,
            context=context
        )


# Date & time fields...

class DateTimeField(Field):
    default_error_messages = {
        'invalid': _('Datetime has wrong format. Use one of these formats instead: {format}.'),
        'date': _('Expected a datetime but got a date.'),
        'make_aware': _('Invalid datetime for the timezone "{timezone}".'),
        'overflow': _('Datetime value out of range.')
    }
    datetime_parser = datetime.datetime.strptime

    def __init__(self, format=empty, input_formats=None, default_timezone=None, **kwargs):
        if format is not empty:
            self.format = format
        if input_formats is not None:
            self.input_formats = input_formats
        if default_timezone is not None:
            self.timezone = default_timezone
        super().__init__(**kwargs)

    def enforce_timezone(self, value):
        """
        When `self.default_timezone` is `None`, always return naive datetimes.
        When `self.default_timezone` is not `None`, always return aware datetimes.
        """
        field_timezone = self.timezone if hasattr(self, 'timezone') else self.default_timezone()

        if field_timezone is not None:
            if timezone.is_aware(value):
                try:
                    return value.astimezone(field_timezone)
                except OverflowError:
                    self.fail('overflow')
            try:
                return timezone.make_aware(value, field_timezone)
            except InvalidTimeError:
                self.fail('make_aware', timezone=field_timezone)
        elif (field_timezone is None) and timezone.is_aware(value):
            return timezone.make_naive(value, datetime.timezone.utc)
        return value

    def default_timezone(self):
        return timezone.get_current_timezone() if settings.USE_TZ else None

    def to_internal_value(self, value):
        input_formats = getattr(self, 'input_formats', api_settings.DATETIME_INPUT_FORMATS)

        if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
            self.fail('date')

        if isinstance(value, datetime.datetime):
            return self.enforce_timezone(value)

        for input_format in input_formats:
            if input_format.lower() == ISO_8601:
                try:
                    parsed = parse_datetime(value)
                    if parsed is not None:
                        return self.enforce_timezone(parsed)
                except (ValueError, TypeError):
                    pass
            else:
                try:
                    parsed = self.datetime_parser(value, input_format)
                    return self.enforce_timezone(parsed)
                except (ValueError, TypeError):
                    pass

        humanized_format = humanize_datetime.datetime_formats(input_formats)
        self.fail('invalid', format=humanized_format)

    def to_representation(self, value):
        if not value:
            return None

        output_format = getattr(self, 'format', api_settings.DATETIME_FORMAT)

        if output_format is None or isinstance(value, str):
            return value

        value = self.enforce_timezone(value)

        if output_format.lower() == ISO_8601:
            value = value.isoformat()
            if value.endswith('+00:00'):
                value = value[:-6] + 'Z'
            return value
        return value.strftime(output_format)


class DateField(Field):
    default_error_messages = {
        'invalid': _('Date has wrong format. Use one of these formats instead: {format}.'),
        'datetime': _('Expected a date but got a datetime.'),
    }
    datetime_parser = datetime.datetime.strptime

    def __init__(self, format=empty, input_formats=None, **kwargs):
        if format is not empty:
            self.format = format
        if input_formats is not None:
            self.input_formats = input_formats
        super().__init__(**kwargs)

    def to_internal_value(self, value):
        input_formats = getattr(self, 'input_formats', api_settings.DATE_INPUT_FORMATS)

        if isinstance(value, datetime.datetime):
            self.fail('datetime')

        if isinstance(value, datetime.date):
            return value

        for input_format in input_formats:
            if input_format.lower() == ISO_8601:
                try:
                    parsed = parse_date(value)
                except (ValueError, TypeError):
                    pass
                else:
                    if parsed is not None:
                        return parsed
            else:
                try:
                    parsed = self.datetime_parser(value, input_format)
                except (ValueError, TypeError):
                    pass
                else:
                    return parsed.date()

        humanized_format = humanize_datetime.date_formats(input_formats)
        self.fail('invalid', format=humanized_format)

    def to_representation(self, value):
        if not value:
            return None

        output_format = getattr(self, 'format', api_settings.DATE_FORMAT)

        if output_format is None or isinstance(value, str):
            return value

        # Applying a `DateField` to a datetime value is almost always
        # not a sensible thing to do, as it means naively dropping
        # any explicit or implicit timezone info.
        assert not isinstance(value, datetime.datetime), (
            'Expected a `date`, but got a `datetime`. Refusing to coerce, '
            'as this may mean losing timezone information. Use a custom '
            'read-only field and deal with timezone issues explicitly.'
        )

        if output_format.lower() == ISO_8601:
            return value.isoformat()

        return value.strftime(output_format)


class TimeField(Field):
    default_error_messages = {
        'invalid': _('Time has wrong format. Use one of these formats instead: {format}.'),
    }
    datetime_parser = datetime.datetime.strptime

    def __init__(self, format=empty, input_formats=None, **kwargs):
        if format is not empty:
            self.format = format
        if input_formats is not None:
            self.input_formats = input_formats
        super().__init__(**kwargs)

    def to_internal_value(self, value):
        input_formats = getattr(self, 'input_formats', api_settings.TIME_INPUT_FORMATS)

        if isinstance(value, datetime.time):
            return value

        for input_format in input_formats:
            if input_format.lower() == ISO_8601:
                try:
                    parsed = parse_time(value)
                except (ValueError, TypeError):
                    pass
                else:
                    if parsed is not None:
                        return parsed
            else:
                try:
                    parsed = self.datetime_parser(value, input_format)
                except (ValueError, TypeError):
                    pass
                else:
                    return parsed.time()

        humanized_format = humanize_datetime.time_formats(input_formats)
        self.fail('invalid', format=humanized_format)

    def to_representation(self, value):
        if value in (None, ''):
            return None

        output_format = getattr(self, 'format', api_settings.TIME_FORMAT)

        if output_format is None or isinstance(value, str):
            return value

        # Applying a `TimeField` to a datetime value is almost always
        # not a sensible thing to do, as it means naively dropping
        # any explicit or implicit timezone info.
        assert not isinstance(value, datetime.datetime), (
            'Expected a `time`, but got a `datetime`. Refusing to coerce, '
            'as this may mean losing timezone information. Use a custom '
            'read-only field and deal with timezone issues explicitly.'
        )

        if output_format.lower() == ISO_8601:
            return value.isoformat()
        return value.strftime(output_format)


class DurationField(Field):
    default_error_messages = {
        'invalid': _('Duration has wrong format. Use one of these formats instead: {format}.'),
        'max_value': _('Ensure this value is less than or equal to {max_value}.'),
        'min_value': _('Ensure this value is greater than or equal to {min_value}.'),
    }

    def __init__(self, **kwargs):
        self.max_value = kwargs.pop('max_value', None)
        self.min_value = kwargs.pop('min_value', None)
        super().__init__(**kwargs)
        if self.max_value is not None:
            message = lazy_format(self.error_messages['max_value'], max_value=self.max_value)
            self.validators.append(
                MaxValueValidator(self.max_value, message=message))
        if self.min_value is not None:
            message = lazy_format(self.error_messages['min_value'], min_value=self.min_value)
            self.validators.append(
                MinValueValidator(self.min_value, message=message))

    def to_internal_value(self, value):
        if isinstance(value, datetime.timedelta):
            return value
        parsed = parse_duration(str(value))
        if parsed is not None:
            return parsed
        self.fail('invalid', format='[DD] [HH:[MM:]]ss[.uuuuuu]')

    def to_representation(self, value):
        return duration_string(value)


# Choice types...

class ChoiceField(Field):
    default_error_messages = {
        'invalid_choice': _('"{input}" is not a valid choice.')
    }
    html_cutoff = None
    html_cutoff_text = _('More than {count} items...')

    def __init__(self, choices, **kwargs):
        self.choices = choices
        self.html_cutoff = kwargs.pop('html_cutoff', self.html_cutoff)
        self.html_cutoff_text = kwargs.pop('html_cutoff_text', self.html_cutoff_text)

        self.allow_blank = kwargs.pop('allow_blank', False)

        super().__init__(**kwargs)

    def to_internal_value(self, data):
        if data == '' and self.allow_blank:
            return ''

        try:
            return self.choice_strings_to_values[str(data)]
        except KeyError:
            self.fail('invalid_choice', input=data)

    def to_representation(self, value):
        if value in ('', None):
            return value
        return self.choice_strings_to_values.get(str(value), value)

    def iter_options(self):
        """
        Helper method for use with templates rendering select widgets.
        """
        return iter_options(
            self.grouped_choices,
            cutoff=self.html_cutoff,
            cutoff_text=self.html_cutoff_text
        )

    def _get_choices(self):
        return self._choices

    def _set_choices(self, choices):
        self.grouped_choices = to_choices_dict(choices)
        self._choices = flatten_choices_dict(self.grouped_choices)

        # Map the string representation of choices to the underlying value.
        # Allows us to deal with eg. integer choices while supporting either
        # integer or string input, but still get the correct datatype out.
        self.choice_strings_to_values = {
            str(key): key for key in self.choices
        }

    choices = property(_get_choices, _set_choices)


class MultipleChoiceField(ChoiceField):
    default_error_messages = {
        'invalid_choice': _('"{input}" is not a valid choice.'),
        'not_a_list': _('Expected a list of items but got type "{input_type}".'),
        'empty': _('This selection may not be empty.')
    }
    default_empty_html = []

    def __init__(self, **kwargs):
        self.allow_empty = kwargs.pop('allow_empty', True)
        super().__init__(**kwargs)

    def get_value(self, dictionary):
        if self.field_name not in dictionary:
            if getattr(self.root, 'partial', False):
                return empty
        # We override the default field access in order to support
        # lists in HTML forms.
        if html.is_html_input(dictionary):
            return dictionary.getlist(self.field_name)
        return dictionary.get(self.field_name, empty)

    def to_internal_value(self, data):
        if isinstance(data, str) or not hasattr(data, '__iter__'):
            self.fail('not_a_list', input_type=type(data).__name__)
        if not self.allow_empty and len(data) == 0:
            self.fail('empty')

        return {
            # Arguments for super() are needed because of scoping inside
            # comprehensions.
            super(MultipleChoiceField, self).to_internal_value(item)
            for item in data
        }

    def to_representation(self, value):
        return {
            self.choice_strings_to_values.get(str(item), item) for item in value
        }


class FilePathField(ChoiceField):
    default_error_messages = {
        'invalid_choice': _('"{input}" is not a valid path choice.')
    }

    def __init__(self, path, match=None, recursive=False, allow_files=True,
                 allow_folders=False, required=None, **kwargs):
        # Defer to Django's FilePathField implementation to get the
        # valid set of choices.
        field = DjangoFilePathField(
            path, match=match, recursive=recursive, allow_files=allow_files,
            allow_folders=allow_folders, required=required
        )
        kwargs['choices'] = field.choices
        super().__init__(**kwargs)


# File types...

class FileField(Field):
    default_error_messages = {
        'required': _('No file was submitted.'),
        'invalid': _('The submitted data was not a file. Check the encoding type on the form.'),
        'no_name': _('No filename could be determined.'),
        'empty': _('The submitted file is empty.'),
        'max_length': _('Ensure this filename has at most {max_length} characters (it has {length}).'),
    }

    def __init__(self, **kwargs):
        self.max_length = kwargs.pop('max_length', None)
        self.allow_empty_file = kwargs.pop('allow_empty_file', False)
        if 'use_url' in kwargs:
            self.use_url = kwargs.pop('use_url')
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        try:
            # `UploadedFile` objects should have name and size attributes.
            file_name = data.name
            file_size = data.size
        except AttributeError:
            self.fail('invalid')

        if not file_name:
            self.fail('no_name')
        if not self.allow_empty_file and not file_size:
            self.fail('empty')
        if self.max_length and len(file_name) > self.max_length:
            self.fail('max_length', max_length=self.max_length, length=len(file_name))

        return data

    def to_representation(self, value):
        if not value:
            return None

        use_url = getattr(self, 'use_url', api_settings.UPLOADED_FILES_USE_URL)
        if use_url:
            try:
                url = value.url
            except AttributeError:
                return None
            request = self.context.get('request', None)
            if request is not None:
                return request.build_absolute_uri(url)
            return url

        return value.name


class ImageField(FileField):
    default_error_messages = {
        'invalid_image': _(
            'Upload a valid image. The file you uploaded was either not an image or a corrupted image.'
        ),
    }

    def __init__(self, **kwargs):
        self._DjangoImageField = kwargs.pop('_DjangoImageField', DjangoImageField)
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        # Image validation is a bit grungy, so we'll just outright
        # defer to Django's implementation so we don't need to
        # consider it, or treat PIL as a test dependency.
        file_object = super().to_internal_value(data)
        django_field = self._DjangoImageField()
        django_field.error_messages = self.error_messages
        return django_field.clean(file_object)


# Composite field types...

class _UnvalidatedField(Field):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.allow_blank = True
        self.allow_null = True

    def to_internal_value(self, data):
        return data

    def to_representation(self, value):
        return value


class ListField(Field):
    child = _UnvalidatedField()
    initial = []
    default_error_messages = {
        'not_a_list': _('Expected a list of items but got type "{input_type}".'),
        'empty': _('This list may not be empty.'),
        'min_length': _('Ensure this field has at least {min_length} elements.'),
        'max_length': _('Ensure this field has no more than {max_length} elements.')
    }

    def __init__(self, **kwargs):
        self.child = kwargs.pop('child', copy.deepcopy(self.child))
        self.allow_empty = kwargs.pop('allow_empty', True)
        self.max_length = kwargs.pop('max_length', None)
        self.min_length = kwargs.pop('min_length', None)

        assert not inspect.isclass(self.child), '`child` has not been instantiated.'
        assert self.child.source is None, (
            "The `source` argument is not meaningful when applied to a `child=` field. "
            "Remove `source=` from the field declaration."
        )

        super().__init__(**kwargs)
        self.child.bind(field_name='', parent=self)
        if self.max_length is not None:
            message = lazy_format(self.error_messages['max_length'], max_length=self.max_length)
            self.validators.append(MaxLengthValidator(self.max_length, message=message))
        if self.min_length is not None:
            message = lazy_format(self.error_messages['min_length'], min_length=self.min_length)
            self.validators.append(MinLengthValidator(self.min_length, message=message))

    def get_value(self, dictionary):
        if self.field_name not in dictionary:
            if getattr(self.root, 'partial', False):
                return empty
        # We override the default field access in order to support
        # lists in HTML forms.
        if html.is_html_input(dictionary):
            val = dictionary.getlist(self.field_name, [])
            if len(val) > 0:
                # Support QueryDict lists in HTML input.
                return val
            return html.parse_html_list(dictionary, prefix=self.field_name, default=empty)

        return dictionary.get(self.field_name, empty)

    def to_internal_value(self, data):
        """
        List of dicts of native values <- List of dicts of primitive datatypes.
        """
        if html.is_html_input(data):
            data = html.parse_html_list(data, default=[])
        if isinstance(data, (str, Mapping)) or not hasattr(data, '__iter__'):
            self.fail('not_a_list', input_type=type(data).__name__)
        if not self.allow_empty and len(data) == 0:
            self.fail('empty')
        return self.run_child_validation(data)

    def to_representation(self, data):
        """
        List of object instances -> List of dicts of primitive datatypes.
        """
        return [self.child.to_representation(item) if item is not None else None for item in data]

    def run_child_validation(self, data):
        result = []
        errors = OrderedDict()

        for idx, item in enumerate(data):
            try:
                result.append(self.child.run_validation(item))
            except ValidationError as e:
                errors[idx] = e.detail

        if not errors:
            return result
        raise ValidationError(errors)


class DictField(Field):
    child = _UnvalidatedField()
    initial = {}
    default_error_messages = {
        'not_a_dict': _('Expected a dictionary of items but got type "{input_type}".'),
        'empty': _('This dictionary may not be empty.'),
    }

    def __init__(self, **kwargs):
        self.child = kwargs.pop('child', copy.deepcopy(self.child))
        self.allow_empty = kwargs.pop('allow_empty', True)

        assert not inspect.isclass(self.child), '`child` has not been instantiated.'
        assert self.child.source is None, (
            "The `source` argument is not meaningful when applied to a `child=` field. "
            "Remove `source=` from the field declaration."
        )

        super().__init__(**kwargs)
        self.child.bind(field_name='', parent=self)

    def get_value(self, dictionary):
        # We override the default field access in order to support
        # dictionaries in HTML forms.
        if html.is_html_input(dictionary):
            return html.parse_html_dict(dictionary, prefix=self.field_name)
        return dictionary.get(self.field_name, empty)

    def to_internal_value(self, data):
        """
        Dicts of native values <- Dicts of primitive datatypes.
        """
        if html.is_html_input(data):
            data = html.parse_html_dict(data)
        if not isinstance(data, dict):
            self.fail('not_a_dict', input_type=type(data).__name__)
        if not self.allow_empty and len(data) == 0:
            self.fail('empty')

        return self.run_child_validation(data)

    def to_representation(self, value):
        return {
            str(key): self.child.to_representation(val) if val is not None else None
            for key, val in value.items()
        }

    def run_child_validation(self, data):
        result = {}
        errors = OrderedDict()

        for key, value in data.items():
            key = str(key)

            try:
                result[key] = self.child.run_validation(value)
            except ValidationError as e:
                errors[key] = e.detail

        if not errors:
            return result
        raise ValidationError(errors)


class HStoreField(DictField):
    child = CharField(allow_blank=True, allow_null=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        assert isinstance(self.child, CharField), (
            "The `child` argument must be an instance of `CharField`, "
            "as the hstore extension stores values as strings."
        )


class JSONField(Field):
    default_error_messages = {
        'invalid': _('Value must be valid JSON.')
    }

    # Workaround for isinstance calls when importing the field isn't possible
    _is_jsonfield = True

    def __init__(self, **kwargs):
        self.binary = kwargs.pop('binary', False)
        self.encoder = kwargs.pop('encoder', None)
        self.decoder = kwargs.pop('decoder', None)
        super().__init__(**kwargs)

    def get_value(self, dictionary):
        if html.is_html_input(dictionary) and self.field_name in dictionary:
            # When HTML form input is used, mark up the input
            # as being a JSON string, rather than a JSON primitive.
            class JSONString(str):
                def __new__(cls, value):
                    ret = str.__new__(cls, value)
                    ret.is_json_string = True
                    return ret
            return JSONString(dictionary[self.field_name])
        return dictionary.get(self.field_name, empty)

    def to_internal_value(self, data):
        try:
            if self.binary or getattr(data, 'is_json_string', False):
                if isinstance(data, bytes):
                    data = data.decode()
                return json.loads(data, cls=self.decoder)
            else:
                json.dumps(data, cls=self.encoder)
        except (TypeError, ValueError):
            self.fail('invalid')
        return data

    def to_representation(self, value):
        if self.binary:
            value = json.dumps(value, cls=self.encoder)
            value = value.encode()
        return value


# Miscellaneous field types...

class ReadOnlyField(Field):
    """
    A read-only field that simply returns the field value.

    If the field is a method with no parameters, the method will be called
    and its return value used as the representation.

    For example, the following would call `get_expiry_date()` on the object:

    class ExampleSerializer(Serializer):
        expiry_date = ReadOnlyField(source='get_expiry_date')
    """

    def __init__(self, **kwargs):
        kwargs['read_only'] = True
        super().__init__(**kwargs)

    def to_representation(self, value):
        return value


class HiddenField(Field):
    """
    A hidden field does not take input from the user, or present any output,
    but it does populate a field in `validated_data`, based on its default
    value. This is particularly useful when we have a `unique_for_date`
    constraint on a pair of fields, as we need some way to include the date in
    the validated data.
    """
    def __init__(self, **kwargs):
        assert 'default' in kwargs, 'default is a required argument.'
        kwargs['write_only'] = True
        super().__init__(**kwargs)

    def get_value(self, dictionary):
        # We always use the default value for `HiddenField`.
        # User input is never provided or accepted.
        return empty

    def to_internal_value(self, data):
        return data


class SerializerMethodField(Field):
    """
    A read-only field that get its representation from calling a method on the
    parent serializer class. The method called will be of the form
    "get_{field_name}", and should take a single argument, which is the
    object being serialized.

    For example:

    class ExampleSerializer(self):
        extra_info = SerializerMethodField()

        def get_extra_info(self, obj):
            return ...  # Calculate some data to return.
    """
    def __init__(self, method_name=None, **kwargs):
        self.method_name = method_name
        kwargs['source'] = '*'
        kwargs['read_only'] = True
        super().__init__(**kwargs)

    def bind(self, field_name, parent):
        # The method name defaults to `get_{field_name}`.
        if self.method_name is None:
            self.method_name = 'get_{field_name}'.format(field_name=field_name)

        super().bind(field_name, parent)

    def to_representation(self, value):
        method = getattr(self.parent, self.method_name)
        return method(value)


class ModelField(Field):
    """
    A generic field that can be used against an arbitrary model field.

    This is used by `ModelSerializer` when dealing with custom model fields,
    that do not have a serializer field to be mapped to.
    """
    default_error_messages = {
        'max_length': _('Ensure this field has no more than {max_length} characters.'),
    }

    def __init__(self, model_field, **kwargs):
        self.model_field = model_field
        # The `max_length` option is supported by Django's base `Field` class,
        # so we'd better support it here.
        self.max_length = kwargs.pop('max_length', None)
        super().__init__(**kwargs)
        if self.max_length is not None:
            message = lazy_format(self.error_messages['max_length'], max_length=self.max_length)
            self.validators.append(
                MaxLengthValidator(self.max_length, message=message))

    def to_internal_value(self, data):
        rel = self.model_field.remote_field
        if rel is not None:
            return rel.model._meta.get_field(rel.field_name).to_python(data)
        return self.model_field.to_python(data)

    def get_attribute(self, obj):
        # We pass the object instance onto `to_representation`,
        # not just the field attribute.
        return obj

    def to_representation(self, obj):
        value = self.model_field.value_from_object(obj)
        if is_protected_type(value):
            return value
        return self.model_field.value_to_string(obj)
