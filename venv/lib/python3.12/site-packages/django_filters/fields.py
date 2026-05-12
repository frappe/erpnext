from collections import namedtuple
from datetime import datetime, time

from django import forms
from django.utils.dateparse import parse_datetime
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _

from .conf import settings
from .constants import EMPTY_VALUES
from .utils import handle_timezone
from .widgets import (
    BaseCSVWidget,
    CSVWidget,
    DateRangeWidget,
    LookupChoiceWidget,
    RangeWidget,
)


class RangeField(forms.MultiValueField):
    widget = RangeWidget

    def __init__(self, fields=None, *args, **kwargs):
        if fields is None:
            fields = (forms.DecimalField(), forms.DecimalField())
        super().__init__(fields, *args, **kwargs)

    def compress(self, data_list):
        if data_list:
            return slice(*data_list)
        return None


class DateRangeField(RangeField):
    widget = DateRangeWidget

    def __init__(self, *args, **kwargs):
        fields = (forms.DateField(), forms.DateField())
        super().__init__(fields, *args, **kwargs)

    def compress(self, data_list):
        if data_list:
            start_date, stop_date = data_list
            if start_date:
                start_date = handle_timezone(
                    datetime.combine(start_date, time.min), False
                )
            if stop_date:
                stop_date = handle_timezone(
                    datetime.combine(stop_date, time.max), False
                )
            return slice(start_date, stop_date)
        return None


class DateTimeRangeField(RangeField):
    widget = DateRangeWidget

    def __init__(self, *args, **kwargs):
        fields = (forms.DateTimeField(), forms.DateTimeField())
        super().__init__(fields, *args, **kwargs)


class IsoDateTimeRangeField(RangeField):
    widget = DateRangeWidget

    def __init__(self, *args, **kwargs):
        fields = (IsoDateTimeField(), IsoDateTimeField())
        super().__init__(fields, *args, **kwargs)


class TimeRangeField(RangeField):
    widget = DateRangeWidget

    def __init__(self, *args, **kwargs):
        fields = (forms.TimeField(), forms.TimeField())
        super().__init__(fields, *args, **kwargs)


class Lookup(namedtuple("Lookup", ("value", "lookup_expr"))):
    def __new__(cls, value, lookup_expr):
        if value in EMPTY_VALUES or lookup_expr in EMPTY_VALUES:
            raise ValueError(
                "Empty values ([], (), {}, '', None) are not "
                "valid Lookup arguments. Return None instead."
            )

        return super().__new__(cls, value, lookup_expr)


class LookupChoiceField(forms.MultiValueField):
    default_error_messages = {
        "lookup_required": _("Select a lookup."),
    }

    def __init__(self, field, lookup_choices, *args, **kwargs):
        empty_label = kwargs.pop("empty_label", settings.EMPTY_CHOICE_LABEL)
        fields = (field, ChoiceField(choices=lookup_choices, empty_label=empty_label))
        widget = LookupChoiceWidget(widgets=[f.widget for f in fields])
        kwargs["widget"] = widget
        kwargs["help_text"] = field.help_text
        super().__init__(fields, *args, **kwargs)

    def compress(self, data_list):
        if len(data_list) == 2:
            value, lookup_expr = data_list
            if value not in EMPTY_VALUES:
                if lookup_expr not in EMPTY_VALUES:
                    return Lookup(value=value, lookup_expr=lookup_expr)
                else:
                    raise forms.ValidationError(
                        self.error_messages["lookup_required"], code="lookup_required"
                    )
        return None


class IsoDateTimeField(forms.DateTimeField):
    """
    Supports 'iso-8601' date format too which is out the scope of
    the ``datetime.strptime`` standard library

    # ISO 8601: ``http://www.w3.org/TR/NOTE-datetime``

    Based on Gist example by David Medina https://gist.github.com/copitux/5773821
    """

    ISO_8601 = "iso-8601"
    input_formats = [ISO_8601]

    def strptime(self, value, format):
        value = force_str(value)

        if format == self.ISO_8601:
            parsed = parse_datetime(value)
            if parsed is None:  # Continue with other formats if doesn't match
                raise ValueError
            return handle_timezone(parsed)
        return super().strptime(value, format)


class BaseCSVField(forms.Field):
    """
    Base field for validating CSV types. Value validation is performed by
    secondary base classes.

    ex::
        class IntegerCSVField(BaseCSVField, filters.IntegerField):
            pass

    """

    base_widget_class = BaseCSVWidget

    def __init__(self, *args, **kwargs):
        widget = kwargs.get("widget") or self.widget
        kwargs["widget"] = self._get_widget_class(widget)

        super().__init__(*args, **kwargs)

    def _get_widget_class(self, widget):
        # passthrough, allows for override
        if isinstance(widget, BaseCSVWidget) or (
            isinstance(widget, type) and issubclass(widget, BaseCSVWidget)
        ):
            return widget

        # complain since we are unable to reconstruct widget instances
        assert isinstance(
            widget, type
        ), "'%s.widget' must be a widget class, not %s." % (
            self.__class__.__name__,
            repr(widget),
        )

        bases = (
            self.base_widget_class,
            widget,
        )
        return type(str("CSV%s" % widget.__name__), bases, {})

    def clean(self, value):
        if value in self.empty_values and self.required:
            raise forms.ValidationError(
                self.error_messages["required"], code="required"
            )

        if value is None:
            return None
        return [super(BaseCSVField, self).clean(v) for v in value]


class BaseRangeField(BaseCSVField):
    # Force use of text input, as range must always have two inputs. A date
    # input would only allow a user to input one value and would always fail.
    widget = CSVWidget

    default_error_messages = {"invalid_values": _("Range query expects two values.")}

    def clean(self, value):
        value = super().clean(value)

        assert value is None or isinstance(value, list)

        if value and len(value) != 2:
            raise forms.ValidationError(
                self.error_messages["invalid_values"], code="invalid_values"
            )

        return value


class ChoiceIterator:
    # Emulates the behavior of ModelChoiceIterator, but instead wraps
    # the field's _choices iterable.

    def __init__(self, field, choices):
        self.field = field
        self.choices = choices

    def __iter__(self):
        if self.field.empty_label is not None:
            yield ("", self.field.empty_label)
        if self.field.null_label is not None:
            yield (self.field.null_value, self.field.null_label)
        yield from self.choices

    def __len__(self):
        add = 1 if self.field.empty_label is not None else 0
        add += 1 if self.field.null_label is not None else 0
        return len(self.choices) + add


class ModelChoiceIterator(forms.models.ModelChoiceIterator):
    # Extends the base ModelChoiceIterator to add in 'null' choice handling.
    # This is a bit verbose since we have to insert the null choice after the
    # empty choice, but before the remainder of the choices.

    def __iter__(self):
        iterable = super().__iter__()

        if self.field.empty_label is not None:
            yield next(iterable)
        if self.field.null_label is not None:
            yield (self.field.null_value, self.field.null_label)
        yield from iterable

    def __len__(self):
        add = 1 if self.field.null_label is not None else 0
        return super().__len__() + add


class ChoiceIteratorMixin:
    def __init__(self, *args, **kwargs):
        self.null_label = kwargs.pop("null_label", settings.NULL_CHOICE_LABEL)
        self.null_value = kwargs.pop("null_value", settings.NULL_CHOICE_VALUE)

        super().__init__(*args, **kwargs)

    def _get_choices(self):
        return super()._get_choices()

    def _set_choices(self, value):
        super()._set_choices(value)
        value = self.iterator(self, self._choices)

        self._choices = self.widget.choices = value

    choices = property(_get_choices, _set_choices)


# Unlike their Model* counterparts, forms.ChoiceField and forms.MultipleChoiceField do not set empty_label
class ChoiceField(ChoiceIteratorMixin, forms.ChoiceField):
    iterator = ChoiceIterator

    def __init__(self, *args, **kwargs):
        self.empty_label = kwargs.pop("empty_label", settings.EMPTY_CHOICE_LABEL)
        super().__init__(*args, **kwargs)


class MultipleChoiceField(ChoiceIteratorMixin, forms.MultipleChoiceField):
    iterator = ChoiceIterator

    def __init__(self, *args, **kwargs):
        self.empty_label = None
        super().__init__(*args, **kwargs)


class ModelChoiceField(ChoiceIteratorMixin, forms.ModelChoiceField):
    iterator = ModelChoiceIterator

    def to_python(self, value):
        # bypass the queryset value check
        if self.null_label is not None and value == self.null_value:
            return value
        return super().to_python(value)


class ModelMultipleChoiceField(ChoiceIteratorMixin, forms.ModelMultipleChoiceField):
    iterator = ModelChoiceIterator

    def _check_values(self, value):
        null = self.null_label is not None and value and self.null_value in value
        if null:  # remove the null value and any potential duplicates
            value = [v for v in value if v != self.null_value]

        result = list(super()._check_values(value))
        result += [self.null_value] if null else []
        return result
