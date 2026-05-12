import copy
from collections import OrderedDict

from django import forms
from django.db import models
from django.db.models.constants import LOOKUP_SEP
from django.db.models.fields.related import ManyToManyRel, ManyToOneRel, OneToOneRel

from .conf import settings
from .constants import ALL_FIELDS
from .filters import (
    BaseInFilter,
    BaseRangeFilter,
    BooleanFilter,
    CharFilter,
    ChoiceFilter,
    DateFilter,
    DateTimeFilter,
    DurationFilter,
    Filter,
    ModelChoiceFilter,
    ModelMultipleChoiceFilter,
    NumberFilter,
    TimeFilter,
    UUIDFilter,
)
from .utils import get_all_model_fields, get_model_field, resolve_field, try_dbfield


def remote_queryset(field):
    """
    Get the queryset for the other side of a relationship. This works
    for both `RelatedField`s and `ForeignObjectRel`s.
    """
    model = field.related_model

    # Reverse relationships do not have choice limits
    if not hasattr(field, "get_limit_choices_to"):
        return model._default_manager.all()

    limit_choices_to = field.get_limit_choices_to()
    return model._default_manager.complex_filter(limit_choices_to)


class FilterSetOptions:
    def __init__(self, options=None):
        self.model = getattr(options, "model", None)
        self.fields = getattr(options, "fields", None)
        self.exclude = getattr(options, "exclude", None)

        self.filter_overrides = getattr(options, "filter_overrides", {})

        self.form = getattr(options, "form", forms.Form)


class FilterSetMetaclass(type):
    def __new__(cls, name, bases, attrs):
        attrs["declared_filters"] = cls.get_declared_filters(bases, attrs)

        new_class = super().__new__(cls, name, bases, attrs)
        new_class._meta = FilterSetOptions(getattr(new_class, "Meta", None))
        new_class.base_filters = new_class.get_filters()

        return new_class

    @classmethod
    def get_declared_filters(cls, bases, attrs):
        filters = [
            (filter_name, attrs.pop(filter_name))
            for filter_name, obj in list(attrs.items())
            if isinstance(obj, Filter)
        ]

        # Default the `filter.field_name` to the attribute name on the filterset
        for filter_name, f in filters:
            if getattr(f, "field_name", None) is None:
                f.field_name = filter_name

        filters.sort(key=lambda x: x[1].creation_counter)

        # Ensures a base class field doesn't override cls attrs, and maintains
        # field precedence when inheriting multiple parents. e.g. if there is a
        # class C(A, B), and A and B both define 'field', use 'field' from A.
        known = set(attrs)

        def visit(name):
            known.add(name)
            return name

        base_filters = [
            (visit(name), f)
            for base in bases
            if hasattr(base, "declared_filters")
            for name, f in base.declared_filters.items()
            if name not in known
        ]

        return OrderedDict(base_filters + filters)


FILTER_FOR_DBFIELD_DEFAULTS = {
    models.AutoField: {"filter_class": NumberFilter},
    models.CharField: {"filter_class": CharFilter},
    models.TextField: {"filter_class": CharFilter},
    models.BooleanField: {"filter_class": BooleanFilter},
    models.DateField: {"filter_class": DateFilter},
    models.DateTimeField: {"filter_class": DateTimeFilter},
    models.TimeField: {"filter_class": TimeFilter},
    models.DurationField: {"filter_class": DurationFilter},
    models.DecimalField: {"filter_class": NumberFilter},
    models.SmallIntegerField: {"filter_class": NumberFilter},
    models.IntegerField: {"filter_class": NumberFilter},
    models.PositiveIntegerField: {"filter_class": NumberFilter},
    models.PositiveSmallIntegerField: {"filter_class": NumberFilter},
    models.FloatField: {"filter_class": NumberFilter},
    models.NullBooleanField: {"filter_class": BooleanFilter},
    models.SlugField: {"filter_class": CharFilter},
    models.EmailField: {"filter_class": CharFilter},
    models.FilePathField: {"filter_class": CharFilter},
    models.URLField: {"filter_class": CharFilter},
    models.GenericIPAddressField: {"filter_class": CharFilter},
    models.CommaSeparatedIntegerField: {"filter_class": CharFilter},
    models.UUIDField: {"filter_class": UUIDFilter},
    # Forward relationships
    models.OneToOneField: {
        "filter_class": ModelChoiceFilter,
        "extra": lambda f: {
            "queryset": remote_queryset(f),
            "to_field_name": f.remote_field.field_name,
            "null_label": settings.NULL_CHOICE_LABEL if f.null else None,
        },
    },
    models.ForeignKey: {
        "filter_class": ModelChoiceFilter,
        "extra": lambda f: {
            "queryset": remote_queryset(f),
            "to_field_name": f.remote_field.field_name,
            "null_label": settings.NULL_CHOICE_LABEL if f.null else None,
        },
    },
    models.ManyToManyField: {
        "filter_class": ModelMultipleChoiceFilter,
        "extra": lambda f: {
            "queryset": remote_queryset(f),
        },
    },
    # Reverse relationships
    OneToOneRel: {
        "filter_class": ModelChoiceFilter,
        "extra": lambda f: {
            "queryset": remote_queryset(f),
            "null_label": settings.NULL_CHOICE_LABEL if f.null else None,
        },
    },
    ManyToOneRel: {
        "filter_class": ModelMultipleChoiceFilter,
        "extra": lambda f: {
            "queryset": remote_queryset(f),
        },
    },
    ManyToManyRel: {
        "filter_class": ModelMultipleChoiceFilter,
        "extra": lambda f: {
            "queryset": remote_queryset(f),
        },
    },
}


class BaseFilterSet:
    FILTER_DEFAULTS = FILTER_FOR_DBFIELD_DEFAULTS

    def __init__(self, data=None, queryset=None, *, request=None, prefix=None):
        if queryset is None:
            queryset = self._meta.model._default_manager.all()
        model = queryset.model

        self.is_bound = data is not None
        self.data = data or {}
        self.queryset = queryset
        self.request = request
        self.form_prefix = prefix

        self.filters = copy.deepcopy(self.base_filters)

        # propagate the model and filterset to the filters
        for filter_ in self.filters.values():
            filter_.model = model
            filter_.parent = self

    def is_valid(self):
        """
        Return True if the underlying form has no errors, or False otherwise.
        """
        return self.is_bound and self.form.is_valid()

    @property
    def errors(self):
        """
        Return an ErrorDict for the data provided for the underlying form.
        """
        return self.form.errors

    def filter_queryset(self, queryset):
        """
        Filter the queryset with the underlying form's `cleaned_data`. You must
        call `is_valid()` or `errors` before calling this method.

        This method should be overridden if additional filtering needs to be
        applied to the queryset before it is cached.
        """
        for name, value in self.form.cleaned_data.items():
            queryset = self.filters[name].filter(queryset, value)
            assert isinstance(
                queryset, models.QuerySet
            ), "Expected '%s.%s' to return a QuerySet, but got a %s instead." % (
                type(self).__name__,
                name,
                type(queryset).__name__,
            )
        return queryset

    @property
    def qs(self):
        if not hasattr(self, "_qs"):
            qs = self.queryset.all()
            if self.is_bound:
                # ensure form validation before filtering
                self.errors
                qs = self.filter_queryset(qs)
            self._qs = qs
        return self._qs

    def get_form_class(self):
        """
        Returns a django Form suitable of validating the filterset data.

        This method should be overridden if the form class needs to be
        customized relative to the filterset instance.
        """
        fields = OrderedDict(
            [(name, filter_.field) for name, filter_ in self.filters.items()]
        )

        return type(str("%sForm" % self.__class__.__name__), (self._meta.form,), fields)

    @property
    def form(self):
        if not hasattr(self, "_form"):
            Form = self.get_form_class()
            if self.is_bound:
                self._form = Form(self.data, prefix=self.form_prefix)
            else:
                self._form = Form(prefix=self.form_prefix)
        return self._form

    @classmethod
    def get_fields(cls):
        """
        Resolve the 'fields' argument that should be used for generating filters on the
        filterset. This is 'Meta.fields' sans the fields in 'Meta.exclude'.
        """
        model = cls._meta.model
        fields = cls._meta.fields
        exclude = cls._meta.exclude

        assert not (fields is None and exclude is None), (
            "Setting 'Meta.model' without either 'Meta.fields' or 'Meta.exclude' "
            "has been deprecated since 0.15.0 and is now disallowed. Add an explicit "
            "'Meta.fields' or 'Meta.exclude' to the %s class." % cls.__name__
        )

        # Setting exclude with no fields implies all other fields.
        if exclude is not None and fields is None:
            fields = ALL_FIELDS

        # Resolve ALL_FIELDS into all fields for the filterset's model.
        if fields == ALL_FIELDS:
            fields = get_all_model_fields(model)

        # Remove excluded fields
        exclude = exclude or []
        if not isinstance(fields, dict):
            fields = [
                (f, [settings.DEFAULT_LOOKUP_EXPR]) for f in fields if f not in exclude
            ]
        else:
            fields = [(f, lookups) for f, lookups in fields.items() if f not in exclude]

        return OrderedDict(fields)

    @classmethod
    def get_filter_name(cls, field_name, lookup_expr):
        """
        Combine a field name and lookup expression into a usable filter name.
        Exact lookups are the implicit default, so "exact" is stripped from the
        end of the filter name.
        """
        filter_name = LOOKUP_SEP.join([field_name, lookup_expr])

        # This also works with transformed exact lookups, such as 'date__exact'
        _default_expr = LOOKUP_SEP + settings.DEFAULT_LOOKUP_EXPR
        if filter_name.endswith(_default_expr):
            filter_name = filter_name[: -len(_default_expr)]

        return filter_name

    @classmethod
    def get_filters(cls):
        """
        Get all filters for the filterset. This is the combination of declared and
        generated filters.
        """

        # No model specified - skip filter generation
        if not cls._meta.model:
            return cls.declared_filters.copy()

        # Determine the filters that should be included on the filterset.
        filters = OrderedDict()
        fields = cls.get_fields()
        undefined = []

        for field_name, lookups in fields.items():
            field = get_model_field(cls._meta.model, field_name)

            # warn if the field doesn't exist.
            if field is None:
                undefined.append(field_name)

            for lookup_expr in lookups:
                filter_name = cls.get_filter_name(field_name, lookup_expr)

                # If the filter is explicitly declared on the class, skip generation
                if filter_name in cls.declared_filters:
                    filters[filter_name] = cls.declared_filters[filter_name]
                    continue

                if field is not None:
                    filters[filter_name] = cls.filter_for_field(
                        field, field_name, lookup_expr
                    )

        # Allow Meta.fields to contain declared filters *only* when a list/tuple
        if isinstance(cls._meta.fields, (list, tuple)):
            undefined = [f for f in undefined if f not in cls.declared_filters]

        if undefined:
            raise TypeError(
                "'Meta.fields' must not contain non-model field names: %s"
                % ", ".join(undefined)
            )

        # Add in declared filters. This is necessary since we don't enforce adding
        # declared filters to the 'Meta.fields' option
        filters.update(cls.declared_filters)
        return filters

    @classmethod
    def filter_for_field(cls, field, field_name, lookup_expr=None):
        if lookup_expr is None:
            lookup_expr = settings.DEFAULT_LOOKUP_EXPR
        field, lookup_type = resolve_field(field, lookup_expr)

        default = {
            "field_name": field_name,
            "lookup_expr": lookup_expr,
        }

        filter_class, params = cls.filter_for_lookup(field, lookup_type)
        default.update(params)

        assert filter_class is not None, (
            "%s resolved field '%s' with '%s' lookup to an unrecognized field "
            "type %s. Try adding an override to 'Meta.filter_overrides'. See: "
            "https://django-filter.readthedocs.io/en/main/ref/filterset.html"
            "#customise-filter-generation-with-filter-overrides"
        ) % (cls.__name__, field_name, lookup_expr, field.__class__.__name__)

        return filter_class(**default)

    @classmethod
    def filter_for_lookup(cls, field, lookup_type):
        DEFAULTS = dict(cls.FILTER_DEFAULTS)
        if hasattr(cls, "_meta"):
            DEFAULTS.update(cls._meta.filter_overrides)

        data = try_dbfield(DEFAULTS.get, field.__class__) or {}
        filter_class = data.get("filter_class")
        params = data.get("extra", lambda field: {})(field)

        # if there is no filter class, exit early
        if not filter_class:
            return None, {}

        # perform lookup specific checks
        if lookup_type == "exact" and getattr(field, "choices", None):
            return ChoiceFilter, {"choices": field.choices}

        if lookup_type == "isnull":
            data = try_dbfield(DEFAULTS.get, models.BooleanField)

            filter_class = data.get("filter_class")
            params = data.get("extra", lambda field: {})(field)
            return filter_class, params

        if lookup_type == "in":

            class ConcreteInFilter(BaseInFilter, filter_class):
                pass

            ConcreteInFilter.__name__ = cls._csv_filter_class_name(
                filter_class, lookup_type
            )

            return ConcreteInFilter, params

        if lookup_type == "range":

            class ConcreteRangeFilter(BaseRangeFilter, filter_class):
                pass

            ConcreteRangeFilter.__name__ = cls._csv_filter_class_name(
                filter_class, lookup_type
            )

            return ConcreteRangeFilter, params

        return filter_class, params

    @classmethod
    def _csv_filter_class_name(cls, filter_class, lookup_type):
        """
        Generate a suitable class name for a concrete filter class. This is not
        completely reliable, as not all filter class names are of the format
        <Type>Filter.

        ex::

            FilterSet._csv_filter_class_name(DateTimeFilter, 'in')

            returns 'DateTimeInFilter'

        """
        # DateTimeFilter => DateTime
        type_name = filter_class.__name__
        if type_name.endswith("Filter"):
            type_name = type_name[:-6]

        # in => In
        lookup_name = lookup_type.capitalize()

        # DateTimeInFilter
        return str("%s%sFilter" % (type_name, lookup_name))


class FilterSet(BaseFilterSet, metaclass=FilterSetMetaclass):
    pass


def filterset_factory(model, fields=ALL_FIELDS):
    meta = type(str("Meta"), (object,), {"model": model, "fields": fields})
    filterset = type(
        str("%sFilterSet" % model._meta.object_name), (FilterSet,), {"Meta": meta}
    )
    return filterset
