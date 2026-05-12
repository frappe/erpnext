"""
Helper functions for mapping model fields to a dictionary of default
keyword arguments that should be used for their equivalent serializer fields.
"""
import inspect

from django.core import validators
from django.db import models
from django.utils.text import capfirst

from rest_framework.compat import postgres_fields
from rest_framework.validators import UniqueValidator

NUMERIC_FIELD_TYPES = (
    models.IntegerField, models.FloatField, models.DecimalField, models.DurationField,
)


class ClassLookupDict:
    """
    Takes a dictionary with classes as keys.
    Lookups against this object will traverses the object's inheritance
    hierarchy in method resolution order, and returns the first matching value
    from the dictionary or raises a KeyError if nothing matches.
    """
    def __init__(self, mapping):
        self.mapping = mapping

    def __getitem__(self, key):
        if hasattr(key, '_proxy_class'):
            # Deal with proxy classes. Ie. BoundField behaves as if it
            # is a Field instance when using ClassLookupDict.
            base_class = key._proxy_class
        else:
            base_class = key.__class__

        for cls in inspect.getmro(base_class):
            if cls in self.mapping:
                return self.mapping[cls]
        raise KeyError('Class %s not found in lookup.' % base_class.__name__)

    def __setitem__(self, key, value):
        self.mapping[key] = value


def needs_label(model_field, field_name):
    """
    Returns `True` if the label based on the model's verbose name
    is not equal to the default label it would have based on it's field name.
    """
    default_label = field_name.replace('_', ' ').capitalize()
    return capfirst(model_field.verbose_name) != default_label


def get_detail_view_name(model):
    """
    Given a model class, return the view name to use for URL relationships
    that refer to instances of the model.
    """
    return '%(model_name)s-detail' % {
        'model_name': model._meta.object_name.lower()
    }


def get_field_kwargs(field_name, model_field):
    """
    Creates a default instance of a basic non-relational field.
    """
    kwargs = {}
    validator_kwarg = list(model_field.validators)

    # The following will only be used by ModelField classes.
    # Gets removed for everything else.
    kwargs['model_field'] = model_field

    if model_field.verbose_name and needs_label(model_field, field_name):
        kwargs['label'] = capfirst(model_field.verbose_name)

    if model_field.help_text:
        kwargs['help_text'] = model_field.help_text

    max_digits = getattr(model_field, 'max_digits', None)
    if max_digits is not None:
        kwargs['max_digits'] = max_digits

    decimal_places = getattr(model_field, 'decimal_places', None)
    if decimal_places is not None:
        kwargs['decimal_places'] = decimal_places

    if isinstance(model_field, models.SlugField):
        kwargs['allow_unicode'] = model_field.allow_unicode

    if isinstance(model_field, models.TextField) and not model_field.choices or \
            (postgres_fields and isinstance(model_field, postgres_fields.JSONField)) or \
            (hasattr(models, 'JSONField') and isinstance(model_field, models.JSONField)):
        kwargs['style'] = {'base_template': 'textarea.html'}

    if model_field.null:
        kwargs['allow_null'] = True

    if isinstance(model_field, models.AutoField) or not model_field.editable:
        # If this field is read-only, then return early.
        # Further keyword arguments are not valid.
        kwargs['read_only'] = True
        return kwargs

    if model_field.has_default() or model_field.blank or model_field.null:
        kwargs['required'] = False

    if model_field.blank and (isinstance(model_field, (models.CharField, models.TextField))):
        kwargs['allow_blank'] = True

    if not model_field.blank and (postgres_fields and isinstance(model_field, postgres_fields.ArrayField)):
        kwargs['allow_empty'] = False

    if isinstance(model_field, models.FilePathField):
        kwargs['path'] = model_field.path

        if model_field.match is not None:
            kwargs['match'] = model_field.match

        if model_field.recursive is not False:
            kwargs['recursive'] = model_field.recursive

        if model_field.allow_files is not True:
            kwargs['allow_files'] = model_field.allow_files

        if model_field.allow_folders is not False:
            kwargs['allow_folders'] = model_field.allow_folders

    if model_field.choices:
        kwargs['choices'] = model_field.choices
    else:
        # Ensure that max_value is passed explicitly as a keyword arg,
        # rather than as a validator.
        max_value = next((
            validator.limit_value for validator in validator_kwarg
            if isinstance(validator, validators.MaxValueValidator)
        ), None)
        if max_value is not None and isinstance(model_field, NUMERIC_FIELD_TYPES):
            kwargs['max_value'] = max_value
            validator_kwarg = [
                validator for validator in validator_kwarg
                if not isinstance(validator, validators.MaxValueValidator)
            ]

        # Ensure that min_value is passed explicitly as a keyword arg,
        # rather than as a validator.
        min_value = next((
            validator.limit_value for validator in validator_kwarg
            if isinstance(validator, validators.MinValueValidator)
        ), None)
        if min_value is not None and isinstance(model_field, NUMERIC_FIELD_TYPES):
            kwargs['min_value'] = min_value
            validator_kwarg = [
                validator for validator in validator_kwarg
                if not isinstance(validator, validators.MinValueValidator)
            ]

        # URLField does not need to include the URLValidator argument,
        # as it is explicitly added in.
        if isinstance(model_field, models.URLField):
            validator_kwarg = [
                validator for validator in validator_kwarg
                if not isinstance(validator, validators.URLValidator)
            ]

        # EmailField does not need to include the validate_email argument,
        # as it is explicitly added in.
        if isinstance(model_field, models.EmailField):
            validator_kwarg = [
                validator for validator in validator_kwarg
                if validator is not validators.validate_email
            ]

        # SlugField do not need to include the 'validate_slug' argument,
        if isinstance(model_field, models.SlugField):
            validator_kwarg = [
                validator for validator in validator_kwarg
                if validator is not validators.validate_slug
            ]

        # IPAddressField do not need to include the 'validate_ipv46_address' argument,
        if isinstance(model_field, models.GenericIPAddressField):
            validator_kwarg = [
                validator for validator in validator_kwarg
                if validator is not validators.validate_ipv46_address
            ]
        # Our decimal validation is handled in the field code, not validator code.
        if isinstance(model_field, models.DecimalField):
            validator_kwarg = [
                validator for validator in validator_kwarg
                if not isinstance(validator, validators.DecimalValidator)
            ]

    # Ensure that max_length is passed explicitly as a keyword arg,
    # rather than as a validator.
    max_length = getattr(model_field, 'max_length', None)
    if max_length is not None and (isinstance(model_field, (models.CharField, models.TextField, models.FileField))):
        kwargs['max_length'] = max_length
        validator_kwarg = [
            validator for validator in validator_kwarg
            if not isinstance(validator, validators.MaxLengthValidator)
        ]

    # Ensure that min_length is passed explicitly as a keyword arg,
    # rather than as a validator.
    min_length = next((
        validator.limit_value for validator in validator_kwarg
        if isinstance(validator, validators.MinLengthValidator)
    ), None)
    if min_length is not None and isinstance(model_field, models.CharField):
        kwargs['min_length'] = min_length
        validator_kwarg = [
            validator for validator in validator_kwarg
            if not isinstance(validator, validators.MinLengthValidator)
        ]

    if getattr(model_field, 'unique', False):
        validator = UniqueValidator(
            queryset=model_field.model._default_manager,
            message=get_unique_error_message(model_field))
        validator_kwarg.append(validator)

    if validator_kwarg:
        kwargs['validators'] = validator_kwarg

    return kwargs


def get_relation_kwargs(field_name, relation_info):
    """
    Creates a default instance of a flat relational field.
    """
    model_field, related_model, to_many, to_field, has_through_model, reverse = relation_info
    kwargs = {
        'queryset': related_model._default_manager,
        'view_name': get_detail_view_name(related_model)
    }

    if to_many:
        kwargs['many'] = True

    if to_field:
        kwargs['to_field'] = to_field

    limit_choices_to = model_field and model_field.get_limit_choices_to()
    if limit_choices_to:
        if not isinstance(limit_choices_to, models.Q):
            limit_choices_to = models.Q(**limit_choices_to)
        kwargs['queryset'] = kwargs['queryset'].filter(limit_choices_to)

    if has_through_model:
        kwargs['read_only'] = True
        kwargs.pop('queryset', None)

    if model_field:
        if model_field.verbose_name and needs_label(model_field, field_name):
            kwargs['label'] = capfirst(model_field.verbose_name)
        help_text = model_field.help_text
        if help_text:
            kwargs['help_text'] = help_text
        if not model_field.editable:
            kwargs['read_only'] = True
            kwargs.pop('queryset', None)
        if model_field.null:
            kwargs['allow_null'] = True
        if kwargs.get('read_only', False):
            # If this field is read-only, then return early.
            # No further keyword arguments are valid.
            return kwargs

        if model_field.has_default() or model_field.blank or model_field.null:
            kwargs['required'] = False
        if model_field.validators:
            kwargs['validators'] = model_field.validators
        if getattr(model_field, 'unique', False):
            validator = UniqueValidator(
                queryset=model_field.model._default_manager,
                message=get_unique_error_message(model_field))
            kwargs['validators'] = kwargs.get('validators', []) + [validator]
        if to_many and not model_field.blank:
            kwargs['allow_empty'] = False

    return kwargs


def get_nested_relation_kwargs(relation_info):
    kwargs = {'read_only': True}
    if relation_info.to_many:
        kwargs['many'] = True
    return kwargs


def get_url_kwargs(model_field):
    return {
        'view_name': get_detail_view_name(model_field)
    }


def get_unique_error_message(model_field):
    unique_error_message = model_field.error_messages.get('unique', None)
    if unique_error_message:
        unique_error_message = unique_error_message % {
            'model_name': model_field.model._meta.verbose_name,
            'field_label': model_field.verbose_name
        }
    return unique_error_message
