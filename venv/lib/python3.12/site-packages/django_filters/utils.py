import datetime
import warnings
from collections import OrderedDict

import django
from django.conf import settings
from django.core.exceptions import FieldDoesNotExist, FieldError
from django.db import models
from django.db.models.constants import LOOKUP_SEP
from django.db.models.expressions import Expression
from django.db.models.fields.related import ForeignObjectRel, RelatedField
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.text import capfirst
from django.utils.translation import gettext as _

from .exceptions import FieldLookupError


def deprecate(msg, level_modifier=0):
    warnings.warn(msg, MigrationNotice, stacklevel=3 + level_modifier)


class MigrationNotice(DeprecationWarning):
    url = "https://django-filter.readthedocs.io/en/main/guide/migration.html"

    def __init__(self, message):
        super().__init__("%s See: %s" % (message, self.url))


class RenameAttributesBase(type):
    """
    Handles the deprecation paths when renaming an attribute.

    It does the following:
    - Defines accessors that redirect to the renamed attributes.
    - Complain whenever an old attribute is accessed.

    This is conceptually based on `django.utils.deprecation.RenameMethodsBase`.
    """

    renamed_attributes = ()

    def __new__(metacls, name, bases, attrs):
        # remove old attributes before creating class
        old_names = [r[0] for r in metacls.renamed_attributes]
        old_names = [name for name in old_names if name in attrs]
        old_attrs = {name: attrs.pop(name) for name in old_names}

        # get a handle to any accessors defined on the class
        cls_getattr = attrs.pop("__getattr__", None)
        cls_setattr = attrs.pop("__setattr__", None)

        new_class = super().__new__(metacls, name, bases, attrs)

        def __getattr__(self, name):
            name = type(self).get_name(name)
            if cls_getattr is not None:
                return cls_getattr(self, name)
            elif hasattr(super(new_class, self), "__getattr__"):
                return super(new_class, self).__getattr__(name)
            return self.__getattribute__(name)

        def __setattr__(self, name, value):
            name = type(self).get_name(name)
            if cls_setattr is not None:
                return cls_setattr(self, name, value)
            return super(new_class, self).__setattr__(name, value)

        new_class.__getattr__ = __getattr__
        new_class.__setattr__ = __setattr__

        # set renamed attributes
        for name, value in old_attrs.items():
            setattr(new_class, name, value)

        return new_class

    def get_name(metacls, name):
        """
        Get the real attribute name. If the attribute has been renamed,
        the new name will be returned and a deprecation warning issued.
        """
        for renamed_attribute in metacls.renamed_attributes:
            old_name, new_name, deprecation_warning = renamed_attribute

            if old_name == name:
                warnings.warn(
                    "`%s.%s` attribute should be renamed `%s`."
                    % (metacls.__name__, old_name, new_name),
                    deprecation_warning,
                    3,
                )
                return new_name

        return name

    def __getattr__(metacls, name):
        return super().__getattribute__(metacls.get_name(name))

    def __setattr__(metacls, name, value):
        return super().__setattr__(metacls.get_name(name), value)


def try_dbfield(fn, field_class):
    """
    Try ``fn`` with the DB ``field_class`` by walking its
    MRO until a result is found.

    ex::
        _try_dbfield(field_dict.get, models.CharField)

    """
    # walk the mro, as field_class could be a derived model field.
    for cls in field_class.mro():
        # skip if cls is models.Field
        if cls is models.Field:
            continue

        data = fn(cls)
        if data:
            return data


def get_all_model_fields(model):
    opts = model._meta

    return [
        f.name
        for f in sorted(opts.fields + opts.many_to_many)
        if not isinstance(f, models.AutoField)
        and not (getattr(f.remote_field, "parent_link", False))
    ]


def get_model_field(model, field_name):
    """
    Get a ``model`` field, traversing relationships
    in the ``field_name``.

    ex::

        f = get_model_field(Book, 'author__first_name')

    """
    fields = get_field_parts(model, field_name)
    return fields[-1] if fields else None


def get_field_parts(model, field_name):
    """
    Get the field parts that represent the traversable relationships from the
    base ``model`` to the final field, described by ``field_name``.

    ex::

        >>> parts = get_field_parts(Book, 'author__first_name')
        >>> [p.verbose_name for p in parts]
        ['author', 'first name']

    """
    parts = field_name.split(LOOKUP_SEP)
    opts = model._meta
    fields = []

    # walk relationships
    for name in parts:
        try:
            field = opts.get_field(name)
        except FieldDoesNotExist:
            return None

        fields.append(field)
        try:
            if isinstance(field, RelatedField):
                opts = field.remote_field.model._meta
            elif isinstance(field, ForeignObjectRel):
                opts = field.related_model._meta
        except AttributeError:
            # Lazy relationships are not resolved until registry is populated.
            raise RuntimeError(
                "Unable to resolve relationship `%s` for `%s`. Django is most "
                "likely not initialized, and its apps registry not populated. "
                "Ensure Django has finished setup before loading `FilterSet`s."
                % (field_name, model._meta.label)
            )

    return fields


def resolve_field(model_field, lookup_expr):
    """
    Resolves a ``lookup_expr`` into its final output field, given
    the initial ``model_field``. The lookup expression should only contain
    transforms and lookups, not intermediary model field parts.

    Note:
    This method is based on django.db.models.sql.query.Query.build_lookup

    For more info on the lookup API:
    https://docs.djangoproject.com/en/stable/ref/models/lookups/

    """
    query = model_field.model._default_manager.all().query
    lhs = Expression(model_field)
    lookups = lookup_expr.split(LOOKUP_SEP)

    assert len(lookups) > 0

    try:
        while lookups:
            name = lookups[0]
            args = (lhs, name)
            # If there is just one part left, try first get_lookup() so
            # that if the lhs supports both transform and lookup for the
            # name, then lookup will be picked.
            if len(lookups) == 1:
                final_lookup = lhs.get_lookup(name)
                if not final_lookup:
                    # We didn't find a lookup. We are going to interpret
                    # the name as transform, and do an Exact lookup against
                    # it.
                    lhs = query.try_transform(*args)
                    final_lookup = lhs.get_lookup("exact")
                return lhs.output_field, final_lookup.lookup_name
            lhs = query.try_transform(*args)
            lookups = lookups[1:]
    except FieldError as e:
        raise FieldLookupError(model_field, lookup_expr) from e


def handle_timezone(value, is_dst=None):
    if settings.USE_TZ and timezone.is_naive(value):
        if django.VERSION < (5, 0):
            return timezone.make_aware(value, timezone.get_current_timezone(), is_dst)
        return timezone.make_aware(value, timezone.get_current_timezone())
    elif not settings.USE_TZ and timezone.is_aware(value):
        return timezone.make_naive(value, datetime.timezone.utc)
    return value


def verbose_field_name(model, field_name):
    """
    Get the verbose name for a given ``field_name``. The ``field_name``
    will be traversed across relationships. Returns '[invalid name]' for
    any field name that cannot be traversed.

    ex::

        >>> verbose_field_name(Article, 'author__name')
        'author name'

    """
    if field_name is None:
        return "[invalid name]"

    parts = get_field_parts(model, field_name)
    if not parts:
        return "[invalid name]"

    names = []
    for part in parts:
        if isinstance(part, ForeignObjectRel):
            if part.related_name:
                names.append(part.related_name.replace("_", " "))
            else:
                return "[invalid name]"
        else:
            names.append(force_str(part.verbose_name))

    return " ".join(names)


def verbose_lookup_expr(lookup_expr):
    """
    Get a verbose, more humanized expression for a given ``lookup_expr``.
    Each part in the expression is looked up in the ``FILTERS_VERBOSE_LOOKUPS``
    dictionary. Missing keys will simply default to itself.

    ex::

        >>> verbose_lookup_expr('year__lt')
        'year is less than'

        # with `FILTERS_VERBOSE_LOOKUPS = {}`
        >>> verbose_lookup_expr('year__lt')
        'year lt'

    """
    from .conf import settings as app_settings

    VERBOSE_LOOKUPS = app_settings.VERBOSE_LOOKUPS or {}
    lookups = [
        force_str(VERBOSE_LOOKUPS.get(lookup, _(lookup)))
        for lookup in lookup_expr.split(LOOKUP_SEP)
    ]

    return " ".join(lookups)


def label_for_filter(model, field_name, lookup_expr, exclude=False):
    """
    Create a generic label suitable for a filter.

    ex::

        >>> label_for_filter(Article, 'author__name', 'in')
        'auther name is in'

    """
    name = verbose_field_name(model, field_name)
    verbose_expression = [_("exclude"), name] if exclude else [name]

    # iterable lookups indicate a LookupTypeField, which should not be verbose
    if isinstance(lookup_expr, str):
        verbose_expression += [verbose_lookup_expr(lookup_expr)]

    verbose_expression = [force_str(part) for part in verbose_expression if part]
    verbose_expression = capfirst(" ".join(verbose_expression))

    return verbose_expression


def translate_validation(error_dict):
    """
    Translate a Django ErrorDict into its DRF ValidationError.
    """
    # it's necessary to lazily import the exception, as it can otherwise create
    # an import loop when importing django_filters inside the project settings.
    from rest_framework.exceptions import ErrorDetail, ValidationError

    exc = OrderedDict(
        (
            key,
            [
                ErrorDetail(e.message % (e.params or ()), code=e.code)
                for e in error_list
            ],
        )
        for key, error_list in error_dict.as_data().items()
    )

    return ValidationError(exc)
