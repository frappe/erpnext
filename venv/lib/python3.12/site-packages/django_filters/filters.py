from collections import OrderedDict
from datetime import timedelta

from django import forms
from django.core.validators import MaxValueValidator
from django.db.models import Q
from django.db.models.constants import LOOKUP_SEP
from django.forms.utils import pretty_name
from django.utils.itercompat import is_iterable
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from .conf import settings
from .constants import EMPTY_VALUES
from .fields import (
    BaseCSVField,
    BaseRangeField,
    ChoiceField,
    DateRangeField,
    DateTimeRangeField,
    IsoDateTimeField,
    IsoDateTimeRangeField,
    LookupChoiceField,
    ModelChoiceField,
    ModelMultipleChoiceField,
    MultipleChoiceField,
    RangeField,
    TimeRangeField,
)
from .utils import get_model_field, label_for_filter

__all__ = [
    "AllValuesFilter",
    "AllValuesMultipleFilter",
    "BaseCSVFilter",
    "BaseInFilter",
    "BaseRangeFilter",
    "BooleanFilter",
    "CharFilter",
    "ChoiceFilter",
    "DateFilter",
    "DateFromToRangeFilter",
    "DateRangeFilter",
    "DateTimeFilter",
    "DateTimeFromToRangeFilter",
    "DurationFilter",
    "Filter",
    "IsoDateTimeFilter",
    "IsoDateTimeFromToRangeFilter",
    "LookupChoiceFilter",
    "ModelChoiceFilter",
    "ModelMultipleChoiceFilter",
    "MultipleChoiceFilter",
    "NumberFilter",
    "NumericRangeFilter",
    "OrderingFilter",
    "RangeFilter",
    "TimeFilter",
    "TimeRangeFilter",
    "TypedChoiceFilter",
    "TypedMultipleChoiceFilter",
    "UUIDFilter",
]


class Filter:
    creation_counter = 0
    field_class = forms.Field

    def __init__(
        self,
        field_name=None,
        lookup_expr=None,
        *,
        label=None,
        method=None,
        distinct=False,
        exclude=False,
        **kwargs
    ):
        if lookup_expr is None:
            lookup_expr = settings.DEFAULT_LOOKUP_EXPR
        self.field_name = field_name
        self.lookup_expr = lookup_expr
        self.label = label
        self.method = method
        self.distinct = distinct
        self.exclude = exclude

        self.extra = kwargs
        self.extra.setdefault("required", False)

        self.creation_counter = Filter.creation_counter
        Filter.creation_counter += 1

    def get_method(self, qs):
        """Return filter method based on whether we're excluding
        or simply filtering.
        """
        return qs.exclude if self.exclude else qs.filter

    def method():
        """
        Filter method needs to be lazily resolved, as it may be dependent on
        the 'parent' FilterSet.
        """

        def fget(self):
            return self._method

        def fset(self, value):
            self._method = value

            # clear existing FilterMethod
            if isinstance(self.filter, FilterMethod):
                del self.filter

            # override filter w/ FilterMethod.
            if value is not None:
                self.filter = FilterMethod(self)

        return locals()

    method = property(**method())

    def label():
        def fget(self):
            if self._label is None and hasattr(self, "model"):
                self._label = label_for_filter(
                    self.model, self.field_name, self.lookup_expr, self.exclude
                )
            return self._label

        def fset(self, value):
            self._label = value

        return locals()

    label = property(**label())

    @property
    def field(self):
        if not hasattr(self, "_field"):
            field_kwargs = self.extra.copy()

            if settings.DISABLE_HELP_TEXT:
                field_kwargs.pop("help_text", None)

            self._field = self.field_class(label=self.label, **field_kwargs)
        return self._field

    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs
        if self.distinct:
            qs = qs.distinct()
        lookup = "%s__%s" % (self.field_name, self.lookup_expr)
        qs = self.get_method(qs)(**{lookup: value})
        return qs


class CharFilter(Filter):
    field_class = forms.CharField


class BooleanFilter(Filter):
    field_class = forms.NullBooleanField


class ChoiceFilter(Filter):
    field_class = ChoiceField

    def __init__(self, *args, **kwargs):
        self.null_value = kwargs.get("null_value", settings.NULL_CHOICE_VALUE)
        super().__init__(*args, **kwargs)

    def filter(self, qs, value):
        if value != self.null_value:
            return super().filter(qs, value)

        qs = self.get_method(qs)(
            **{"%s__%s" % (self.field_name, self.lookup_expr): None}
        )
        return qs.distinct() if self.distinct else qs


class TypedChoiceFilter(Filter):
    field_class = forms.TypedChoiceField


class UUIDFilter(Filter):
    field_class = forms.UUIDField


class MultipleChoiceFilter(Filter):
    """
    This filter performs OR(by default) or AND(using conjoined=True) query
    on the selected options.

    Advanced usage
    --------------
    Depending on your application logic, when all or no choices are selected,
    filtering may be a no-operation. In this case you may wish to avoid the
    filtering overhead, particularly if using a `distinct` call.

    You can override `get_filter_predicate` to use a custom filter.
    By default it will use the filter's name for the key, and the value will
    be the model object - or in case of passing in `to_field_name` the
    value of that attribute on the model.

    Set `always_filter` to `False` after instantiation to enable the default
    `is_noop` test. You can override `is_noop` if you need a different test
    for your application.

    `distinct` defaults to `True` as to-many relationships will generally
    require this.
    """

    field_class = MultipleChoiceField

    always_filter = True

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("distinct", True)
        self.conjoined = kwargs.pop("conjoined", False)
        self.null_value = kwargs.get("null_value", settings.NULL_CHOICE_VALUE)
        super().__init__(*args, **kwargs)

    def is_noop(self, qs, value):
        """
        Return `True` to short-circuit unnecessary and potentially slow
        filtering.
        """
        if self.always_filter:
            return False

        # A reasonable default for being a noop...
        if self.extra.get("required") and len(value) == len(self.field.choices):
            return True

        return False

    def filter(self, qs, value):
        if not value:
            # Even though not a noop, no point filtering if empty.
            return qs

        if self.is_noop(qs, value):
            return qs

        if not self.conjoined:
            q = Q()
        for v in set(value):
            if v == self.null_value:
                v = None
            predicate = self.get_filter_predicate(v)
            if self.conjoined:
                qs = self.get_method(qs)(**predicate)
            else:
                q |= Q(**predicate)

        if not self.conjoined:
            qs = self.get_method(qs)(q)

        return qs.distinct() if self.distinct else qs

    def get_filter_predicate(self, v):
        name = self.field_name
        if name and self.lookup_expr != settings.DEFAULT_LOOKUP_EXPR:
            name = LOOKUP_SEP.join([name, self.lookup_expr])
        try:
            return {name: getattr(v, self.field.to_field_name)}
        except (AttributeError, TypeError):
            return {name: v}


class TypedMultipleChoiceFilter(MultipleChoiceFilter):
    field_class = forms.TypedMultipleChoiceField


class DateFilter(Filter):
    field_class = forms.DateField


class DateTimeFilter(Filter):
    field_class = forms.DateTimeField


class IsoDateTimeFilter(DateTimeFilter):
    """
    Uses IsoDateTimeField to support filtering on ISO 8601 formatted datetimes.

    For context see:

    * https://code.djangoproject.com/ticket/23448
    * https://github.com/encode/django-rest-framework/issues/1338
    * https://github.com/carltongibson/django-filter/pull/264
    """

    field_class = IsoDateTimeField


class TimeFilter(Filter):
    field_class = forms.TimeField


class DurationFilter(Filter):
    field_class = forms.DurationField


class QuerySetRequestMixin:
    """
    Add callable functionality to filters that support the ``queryset``
    argument. If the ``queryset`` is callable, then it **must** accept the
    ``request`` object as a single argument.

    This is useful for filtering querysets by properties on the ``request``
    object, such as the user.

    Example::

        def departments(request):
            company = request.user.company
            return company.department_set.all()

        class EmployeeFilter(filters.FilterSet):
            department = filters.ModelChoiceFilter(queryset=departments)
            ...

    The above example restricts the set of departments to those in the logged-in
    user's associated company.

    """

    def __init__(self, *args, **kwargs):
        self.queryset = kwargs.get("queryset")
        super().__init__(*args, **kwargs)

    def get_request(self):
        try:
            return self.parent.request
        except AttributeError:
            return None

    def get_queryset(self, request):
        queryset = self.queryset

        if callable(queryset):
            return queryset(request)
        return queryset

    @property
    def field(self):
        request = self.get_request()
        queryset = self.get_queryset(request)

        if queryset is not None:
            self.extra["queryset"] = queryset

        return super().field


class ModelChoiceFilter(QuerySetRequestMixin, ChoiceFilter):
    field_class = ModelChoiceField

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("empty_label", settings.EMPTY_CHOICE_LABEL)
        super().__init__(*args, **kwargs)


class ModelMultipleChoiceFilter(QuerySetRequestMixin, MultipleChoiceFilter):
    field_class = ModelMultipleChoiceField


class NumberFilter(Filter):
    field_class = forms.DecimalField

    def get_max_validator(self):
        """
        Return a MaxValueValidator for the field, or None to disable.
        """
        return MaxValueValidator(1e50)

    @property
    def field(self):
        if not hasattr(self, "_field"):
            field = super().field
            max_validator = self.get_max_validator()
            if max_validator:
                field.validators.append(max_validator)

            self._field = field
        return self._field


class NumericRangeFilter(Filter):
    field_class = RangeField

    def filter(self, qs, value):
        if value:
            if value.start is not None and value.stop is not None:
                value = (value.start, value.stop)
            elif value.start is not None:
                self.lookup_expr = "startswith"
                value = value.start
            elif value.stop is not None:
                self.lookup_expr = "endswith"
                value = value.stop

        return super().filter(qs, value)


class RangeFilter(Filter):
    field_class = RangeField

    def filter(self, qs, value):
        if value:
            if value.start is not None and value.stop is not None:
                self.lookup_expr = "range"
                value = (value.start, value.stop)
            elif value.start is not None:
                self.lookup_expr = "gte"
                value = value.start
            elif value.stop is not None:
                self.lookup_expr = "lte"
                value = value.stop

        return super().filter(qs, value)


def _truncate(dt):
    return dt.date()


class DateRangeFilter(ChoiceFilter):
    choices = [
        ("today", _("Today")),
        ("yesterday", _("Yesterday")),
        ("week", _("Past 7 days")),
        ("month", _("This month")),
        ("year", _("This year")),
    ]

    filters = {
        "today": lambda qs, name: qs.filter(
            **{
                "%s__year" % name: now().year,
                "%s__month" % name: now().month,
                "%s__day" % name: now().day,
            }
        ),
        "yesterday": lambda qs, name: qs.filter(
            **{
                "%s__year" % name: (now() - timedelta(days=1)).year,
                "%s__month" % name: (now() - timedelta(days=1)).month,
                "%s__day" % name: (now() - timedelta(days=1)).day,
            }
        ),
        "week": lambda qs, name: qs.filter(
            **{
                "%s__gte" % name: _truncate(now() - timedelta(days=7)),
                "%s__lt" % name: _truncate(now() + timedelta(days=1)),
            }
        ),
        "month": lambda qs, name: qs.filter(
            **{"%s__year" % name: now().year, "%s__month" % name: now().month}
        ),
        "year": lambda qs, name: qs.filter(
            **{
                "%s__year" % name: now().year,
            }
        ),
    }

    def __init__(self, choices=None, filters=None, *args, **kwargs):
        if choices is not None:
            self.choices = choices
        if filters is not None:
            self.filters = filters

        unique = set([x[0] for x in self.choices]) ^ set(self.filters)
        assert not unique, (
            "Keys must be present in both 'choices' and 'filters'. Missing keys: "
            "'%s'" % ", ".join(sorted(unique))
        )

        # null choice not relevant
        kwargs.setdefault("null_label", None)
        super().__init__(choices=self.choices, *args, **kwargs)

    def filter(self, qs, value):
        if not value:
            return qs

        assert value in self.filters

        qs = self.filters[value](qs, self.field_name)
        return qs.distinct() if self.distinct else qs


class DateFromToRangeFilter(RangeFilter):
    field_class = DateRangeField


class DateTimeFromToRangeFilter(RangeFilter):
    field_class = DateTimeRangeField


class IsoDateTimeFromToRangeFilter(RangeFilter):
    field_class = IsoDateTimeRangeField


class TimeRangeFilter(RangeFilter):
    field_class = TimeRangeField


class AllValuesFilter(ChoiceFilter):
    @property
    def field(self):
        qs = self.model._default_manager.distinct()
        qs = qs.order_by(self.field_name).values_list(self.field_name, flat=True)
        self.extra["choices"] = [(o, o) for o in qs]
        return super().field


class AllValuesMultipleFilter(MultipleChoiceFilter):
    @property
    def field(self):
        qs = self.model._default_manager.distinct()
        qs = qs.order_by(self.field_name).values_list(self.field_name, flat=True)
        self.extra["choices"] = [(o, o) for o in qs]
        return super().field


class BaseCSVFilter(Filter):
    """
    Base class for CSV type filters, such as IN and RANGE.
    """

    base_field_class = BaseCSVField

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("help_text", _("Multiple values may be separated by commas."))
        super().__init__(*args, **kwargs)

        class ConcreteCSVField(self.base_field_class, self.field_class):
            pass

        ConcreteCSVField.__name__ = self._field_class_name(
            self.field_class, self.lookup_expr
        )

        self.field_class = ConcreteCSVField

    @classmethod
    def _field_class_name(cls, field_class, lookup_expr):
        """
        Generate a suitable class name for the concrete field class. This is not
        completely reliable, as not all field class names are of the format
        <Type>Field.

        ex::

            BaseCSVFilter._field_class_name(DateTimeField, 'year__in')

            returns 'DateTimeYearInField'

        """
        # DateTimeField => DateTime
        type_name = field_class.__name__
        if type_name.endswith("Field"):
            type_name = type_name[:-5]

        # year__in => YearIn
        parts = lookup_expr.split(LOOKUP_SEP)
        expression_name = "".join(p.capitalize() for p in parts)

        # DateTimeYearInField
        return str("%s%sField" % (type_name, expression_name))


class BaseInFilter(BaseCSVFilter):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("lookup_expr", "in")
        super().__init__(*args, **kwargs)


class BaseRangeFilter(BaseCSVFilter):
    base_field_class = BaseRangeField

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("lookup_expr", "range")
        super().__init__(*args, **kwargs)


class LookupChoiceFilter(Filter):
    """
    A combined filter that allows users to select the lookup expression from a dropdown.

    * ``lookup_choices`` is an optional argument that accepts multiple input
      formats, and is ultimately normalized as the choices used in the lookup
      dropdown. See ``.get_lookup_choices()`` for more information.

    * ``field_class`` is an optional argument that allows you to set the inner
      form field class used to validate the value. Default: ``forms.CharField``

    ex::

        price = django_filters.LookupChoiceFilter(
            field_class=forms.DecimalField,
            lookup_choices=[
                ('exact', 'Equals'),
                ('gt', 'Greater than'),
                ('lt', 'Less than'),
            ]
        )

    """

    field_class = forms.CharField
    outer_class = LookupChoiceField

    def __init__(
        self, field_name=None, lookup_choices=None, field_class=None, **kwargs
    ):
        self.empty_label = kwargs.pop("empty_label", settings.EMPTY_CHOICE_LABEL)

        super(LookupChoiceFilter, self).__init__(field_name=field_name, **kwargs)

        self.lookup_choices = lookup_choices
        if field_class is not None:
            self.field_class = field_class

    @classmethod
    def normalize_lookup(cls, lookup):
        """
        Normalize the lookup into a tuple of ``(lookup expression, display value)``

        If the ``lookup`` is already a tuple, the tuple is not altered.
        If the ``lookup`` is a string, a tuple is returned with the lookup
        expression used as the basis for the display value.

        ex::

            >>> LookupChoiceFilter.normalize_lookup(('exact', 'Equals'))
            ('exact', 'Equals')

            >>> LookupChoiceFilter.normalize_lookup('has_key')
            ('has_key', 'Has key')

        """
        if isinstance(lookup, str):
            return (lookup, pretty_name(lookup))
        return (lookup[0], lookup[1])

    def get_lookup_choices(self):
        """
        Get the lookup choices in a format suitable for ``django.forms.ChoiceField``.
        If the filter is initialized with ``lookup_choices``, this value is normalized
        and passed to the underlying ``LookupChoiceField``. If no choices are provided,
        they are generated from the corresponding model field's registered lookups.
        """
        lookups = self.lookup_choices
        if lookups is None:
            field = get_model_field(self.model, self.field_name)
            lookups = field.get_lookups()

        return [self.normalize_lookup(lookup) for lookup in lookups]

    @property
    def field(self):
        if not hasattr(self, "_field"):
            inner_field = super().field
            lookups = self.get_lookup_choices()

            self._field = self.outer_class(
                inner_field,
                lookups,
                label=self.label,
                empty_label=self.empty_label,
                required=self.extra["required"],
            )

        return self._field

    def filter(self, qs, lookup):
        if not lookup:
            return super().filter(qs, None)

        self.lookup_expr = lookup.lookup_expr
        return super().filter(qs, lookup.value)


class OrderingFilter(BaseCSVFilter, ChoiceFilter):
    """
    Enable queryset ordering. As an extension of ``ChoiceFilter`` it accepts
    two additional arguments that are used to build the ordering choices.

    * ``fields`` is a mapping of {model field name: parameter name}. The
      parameter names are exposed in the choices and mask/alias the field
      names used in the ``order_by()`` call. Similar to field ``choices``,
      ``fields`` accepts the 'list of two-tuples' syntax that retains order.
      ``fields`` may also just be an iterable of strings. In this case, the
      field names simply double as the exposed parameter names.

    * ``field_labels`` is an optional argument that allows you to customize
      the display label for the corresponding parameter. It accepts a mapping
      of {field name: human readable label}. Keep in mind that the key is the
      field name, and not the exposed parameter name.

    Additionally, you can just provide your own ``choices`` if you require
    explicit control over the exposed options. For example, when you might
    want to disable descending sort options.

    This filter is also CSV-based, and accepts multiple ordering params. The
    default select widget does not enable the use of this, but it is useful
    for APIs.

    """

    descending_fmt = _("%s (descending)")

    def __init__(self, *args, **kwargs):
        """
        ``fields`` may be either a mapping or an iterable.
        ``field_labels`` must be a map of field names to display labels
        """
        fields = kwargs.pop("fields", {})
        fields = self.normalize_fields(fields)
        field_labels = kwargs.pop("field_labels", {})

        self.param_map = {v: k for k, v in fields.items()}

        if "choices" not in kwargs:
            kwargs["choices"] = self.build_choices(fields, field_labels)

        kwargs.setdefault("label", _("Ordering"))
        kwargs.setdefault("help_text", "")
        kwargs.setdefault("null_label", None)
        super().__init__(*args, **kwargs)

    def get_ordering_value(self, param):
        descending = param.startswith("-")
        param = param[1:] if descending else param
        field_name = self.param_map.get(param, param)

        return "-%s" % field_name if descending else field_name

    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs

        ordering = [self.get_ordering_value(param) for param in value]
        return qs.order_by(*ordering)

    @classmethod
    def normalize_fields(cls, fields):
        """
        Normalize the fields into an ordered map of {field name: param name}
        """
        # fields is a mapping, copy into new OrderedDict
        if isinstance(fields, dict):
            return OrderedDict(fields)

        # convert iterable of values => iterable of pairs (field name, param name)
        assert is_iterable(
            fields
        ), "'fields' must be an iterable (e.g., a list, tuple, or mapping)."

        # fields is an iterable of field names
        assert all(
            isinstance(field, str)
            or is_iterable(field)
            and len(field) == 2  # may need to be wrapped in parens
            for field in fields
        ), "'fields' must contain strings or (field name, param name) pairs."

        return OrderedDict([(f, f) if isinstance(f, str) else f for f in fields])

    def build_choices(self, fields, labels):
        ascending = [
            (param, labels.get(field, _(pretty_name(param))))
            for field, param in fields.items()
        ]
        descending = [
            ("-%s" % param, labels.get("-%s" % param, self.descending_fmt % label))
            for param, label in ascending
        ]

        # interleave the ascending and descending choices
        return [val for pair in zip(ascending, descending) for val in pair]


class FilterMethod:
    """
    This helper is used to override Filter.filter() when a 'method' argument
    is passed. It proxies the call to the actual method on the filter's parent.
    """

    def __init__(self, filter_instance):
        self.f = filter_instance

    def __call__(self, qs, value):
        if value in EMPTY_VALUES:
            return qs

        return self.method(qs, self.f.field_name, value)

    @property
    def method(self):
        """
        Resolve the method on the parent filterset.
        """
        instance = self.f

        # noop if 'method' is a function
        if callable(instance.method):
            return instance.method

        # otherwise, method is the name of a method on the parent FilterSet.
        assert hasattr(
            instance, "parent"
        ), "Filter '%s' must have a parent FilterSet to find '.%s()'" % (
            instance.field_name,
            instance.method,
        )

        parent = instance.parent
        method = getattr(parent, instance.method, None)

        assert callable(
            method
        ), "Expected parent FilterSet '%s.%s' to have a '.%s()' method." % (
            parent.__class__.__module__,
            parent.__class__.__name__,
            instance.method,
        )

        return method
