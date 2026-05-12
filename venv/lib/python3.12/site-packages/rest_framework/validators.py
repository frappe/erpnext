"""
We perform uniqueness checks explicitly on the serializer class, rather
the using Django's `.full_clean()`.

This gives us better separation of concerns, allows us to use single-step
object creation, and makes it possible to switch between using the implicit
`ModelSerializer` class and an equivalent explicit `Serializer` class.
"""
from django.db import DataError
from django.utils.translation import gettext_lazy as _

from rest_framework.exceptions import ValidationError
from rest_framework.utils.representation import smart_repr


# Robust filter and exist implementations. Ensures that queryset.exists() for
# an invalid value returns `False`, rather than raising an error.
# Refs https://github.com/encode/django-rest-framework/issues/3381
def qs_exists(queryset):
    try:
        return queryset.exists()
    except (TypeError, ValueError, DataError):
        return False


def qs_filter(queryset, **kwargs):
    try:
        return queryset.filter(**kwargs)
    except (TypeError, ValueError, DataError):
        return queryset.none()


class UniqueValidator:
    """
    Validator that corresponds to `unique=True` on a model field.

    Should be applied to an individual field on the serializer.
    """
    message = _('This field must be unique.')
    requires_context = True

    def __init__(self, queryset, message=None, lookup='exact'):
        self.queryset = queryset
        self.message = message or self.message
        self.lookup = lookup

    def filter_queryset(self, value, queryset, field_name):
        """
        Filter the queryset to all instances matching the given attribute.
        """
        filter_kwargs = {'%s__%s' % (field_name, self.lookup): value}
        return qs_filter(queryset, **filter_kwargs)

    def exclude_current_instance(self, queryset, instance):
        """
        If an instance is being updated, then do not include
        that instance itself as a uniqueness conflict.
        """
        if instance is not None:
            return queryset.exclude(pk=instance.pk)
        return queryset

    def __call__(self, value, serializer_field):
        # Determine the underlying model field name. This may not be the
        # same as the serializer field name if `source=<>` is set.
        field_name = serializer_field.source_attrs[-1]
        # Determine the existing instance, if this is an update operation.
        instance = getattr(serializer_field.parent, 'instance', None)

        queryset = self.queryset
        queryset = self.filter_queryset(value, queryset, field_name)
        queryset = self.exclude_current_instance(queryset, instance)
        if qs_exists(queryset):
            raise ValidationError(self.message, code='unique')

    def __repr__(self):
        return '<%s(queryset=%s)>' % (
            self.__class__.__name__,
            smart_repr(self.queryset)
        )


class UniqueTogetherValidator:
    """
    Validator that corresponds to `unique_together = (...)` on a model class.

    Should be applied to the serializer class, not to an individual field.
    """
    message = _('The fields {field_names} must make a unique set.')
    missing_message = _('This field is required.')
    requires_context = True

    def __init__(self, queryset, fields, message=None):
        self.queryset = queryset
        self.fields = fields
        self.message = message or self.message

    def enforce_required_fields(self, attrs, serializer):
        """
        The `UniqueTogetherValidator` always forces an implied 'required'
        state on the fields it applies to.
        """
        if serializer.instance is not None:
            return

        missing_items = {
            field_name: self.missing_message
            for field_name in self.fields
            if serializer.fields[field_name].source not in attrs
        }
        if missing_items:
            raise ValidationError(missing_items, code='required')

    def filter_queryset(self, attrs, queryset, serializer):
        """
        Filter the queryset to all instances matching the given attributes.
        """
        # field names => field sources
        sources = [
            serializer.fields[field_name].source
            for field_name in self.fields
        ]

        # If this is an update, then any unprovided field should
        # have it's value set based on the existing instance attribute.
        if serializer.instance is not None:
            for source in sources:
                if source not in attrs:
                    attrs[source] = getattr(serializer.instance, source)

        # Determine the filter keyword arguments and filter the queryset.
        filter_kwargs = {
            source: attrs[source]
            for source in sources
        }
        return qs_filter(queryset, **filter_kwargs)

    def exclude_current_instance(self, attrs, queryset, instance):
        """
        If an instance is being updated, then do not include
        that instance itself as a uniqueness conflict.
        """
        if instance is not None:
            return queryset.exclude(pk=instance.pk)
        return queryset

    def __call__(self, attrs, serializer):
        self.enforce_required_fields(attrs, serializer)
        queryset = self.queryset
        queryset = self.filter_queryset(attrs, queryset, serializer)
        queryset = self.exclude_current_instance(attrs, queryset, serializer.instance)

        # Ignore validation if any field is None
        checked_values = [
            value for field, value in attrs.items() if field in self.fields
        ]
        if None not in checked_values and qs_exists(queryset):
            field_names = ', '.join(self.fields)
            message = self.message.format(field_names=field_names)
            raise ValidationError(message, code='unique')

    def __repr__(self):
        return '<%s(queryset=%s, fields=%s)>' % (
            self.__class__.__name__,
            smart_repr(self.queryset),
            smart_repr(self.fields)
        )


class ProhibitSurrogateCharactersValidator:
    message = _('Surrogate characters are not allowed: U+{code_point:X}.')
    code = 'surrogate_characters_not_allowed'

    def __call__(self, value):
        for surrogate_character in (ch for ch in str(value)
                                    if 0xD800 <= ord(ch) <= 0xDFFF):
            message = self.message.format(code_point=ord(surrogate_character))
            raise ValidationError(message, code=self.code)


class BaseUniqueForValidator:
    message = None
    missing_message = _('This field is required.')
    requires_context = True

    def __init__(self, queryset, field, date_field, message=None):
        self.queryset = queryset
        self.field = field
        self.date_field = date_field
        self.message = message or self.message

    def enforce_required_fields(self, attrs):
        """
        The `UniqueFor<Range>Validator` classes always force an implied
        'required' state on the fields they are applied to.
        """
        missing_items = {
            field_name: self.missing_message
            for field_name in [self.field, self.date_field]
            if field_name not in attrs
        }
        if missing_items:
            raise ValidationError(missing_items, code='required')

    def filter_queryset(self, attrs, queryset, field_name, date_field_name):
        raise NotImplementedError('`filter_queryset` must be implemented.')

    def exclude_current_instance(self, attrs, queryset, instance):
        """
        If an instance is being updated, then do not include
        that instance itself as a uniqueness conflict.
        """
        if instance is not None:
            return queryset.exclude(pk=instance.pk)
        return queryset

    def __call__(self, attrs, serializer):
        # Determine the underlying model field names. These may not be the
        # same as the serializer field names if `source=<>` is set.
        field_name = serializer.fields[self.field].source_attrs[-1]
        date_field_name = serializer.fields[self.date_field].source_attrs[-1]

        self.enforce_required_fields(attrs)
        queryset = self.queryset
        queryset = self.filter_queryset(attrs, queryset, field_name, date_field_name)
        queryset = self.exclude_current_instance(attrs, queryset, serializer.instance)
        if qs_exists(queryset):
            message = self.message.format(date_field=self.date_field)
            raise ValidationError({
                self.field: message
            }, code='unique')

    def __repr__(self):
        return '<%s(queryset=%s, field=%s, date_field=%s)>' % (
            self.__class__.__name__,
            smart_repr(self.queryset),
            smart_repr(self.field),
            smart_repr(self.date_field)
        )


class UniqueForDateValidator(BaseUniqueForValidator):
    message = _('This field must be unique for the "{date_field}" date.')

    def filter_queryset(self, attrs, queryset, field_name, date_field_name):
        value = attrs[self.field]
        date = attrs[self.date_field]

        filter_kwargs = {}
        filter_kwargs[field_name] = value
        filter_kwargs['%s__day' % date_field_name] = date.day
        filter_kwargs['%s__month' % date_field_name] = date.month
        filter_kwargs['%s__year' % date_field_name] = date.year
        return qs_filter(queryset, **filter_kwargs)


class UniqueForMonthValidator(BaseUniqueForValidator):
    message = _('This field must be unique for the "{date_field}" month.')

    def filter_queryset(self, attrs, queryset, field_name, date_field_name):
        value = attrs[self.field]
        date = attrs[self.date_field]

        filter_kwargs = {}
        filter_kwargs[field_name] = value
        filter_kwargs['%s__month' % date_field_name] = date.month
        return qs_filter(queryset, **filter_kwargs)


class UniqueForYearValidator(BaseUniqueForValidator):
    message = _('This field must be unique for the "{date_field}" year.')

    def filter_queryset(self, attrs, queryset, field_name, date_field_name):
        value = attrs[self.field]
        date = attrs[self.date_field]

        filter_kwargs = {}
        filter_kwargs[field_name] = value
        filter_kwargs['%s__year' % date_field_name] = date.year
        return qs_filter(queryset, **filter_kwargs)
