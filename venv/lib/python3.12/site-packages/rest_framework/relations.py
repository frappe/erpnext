import sys
from collections import OrderedDict
from urllib import parse

from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist
from django.db.models import Manager
from django.db.models.query import QuerySet
from django.urls import NoReverseMatch, Resolver404, get_script_prefix, resolve
from django.utils.encoding import smart_str, uri_to_iri
from django.utils.translation import gettext_lazy as _

from rest_framework.fields import (
    Field, SkipField, empty, get_attribute, is_simple_callable, iter_options
)
from rest_framework.reverse import reverse
from rest_framework.settings import api_settings
from rest_framework.utils import html


def method_overridden(method_name, klass, instance):
    """
    Determine if a method has been overridden.
    """
    method = getattr(klass, method_name)
    default_method = getattr(method, '__func__', method)  # Python 3 compat
    return default_method is not getattr(instance, method_name).__func__


class ObjectValueError(ValueError):
    """
    Raised when `queryset.get()` failed due to an underlying `ValueError`.
    Wrapping prevents calling code conflating this with unrelated errors.
    """


class ObjectTypeError(TypeError):
    """
    Raised when `queryset.get()` failed due to an underlying `TypeError`.
    Wrapping prevents calling code conflating this with unrelated errors.
    """


class Hyperlink(str):
    """
    A string like object that additionally has an associated name.
    We use this for hyperlinked URLs that may render as a named link
    in some contexts, or render as a plain URL in others.
    """
    def __new__(cls, url, obj):
        ret = super().__new__(cls, url)
        ret.obj = obj
        return ret

    def __getnewargs__(self):
        return (str(self), self.name)

    @property
    def name(self):
        # This ensures that we only called `__str__` lazily,
        # as in some cases calling __str__ on a model instances *might*
        # involve a database lookup.
        return str(self.obj)

    is_hyperlink = True


class PKOnlyObject:
    """
    This is a mock object, used for when we only need the pk of the object
    instance, but still want to return an object with a .pk attribute,
    in order to keep the same interface as a regular model instance.
    """
    def __init__(self, pk):
        self.pk = pk

    def __str__(self):
        return "%s" % self.pk


# We assume that 'validators' are intended for the child serializer,
# rather than the parent serializer.
MANY_RELATION_KWARGS = (
    'read_only', 'write_only', 'required', 'default', 'initial', 'source',
    'label', 'help_text', 'style', 'error_messages', 'allow_empty',
    'html_cutoff', 'html_cutoff_text'
)


class RelatedField(Field):
    queryset = None
    html_cutoff = None
    html_cutoff_text = None

    def __init__(self, **kwargs):
        self.queryset = kwargs.pop('queryset', self.queryset)

        cutoff_from_settings = api_settings.HTML_SELECT_CUTOFF
        if cutoff_from_settings is not None:
            cutoff_from_settings = int(cutoff_from_settings)
        self.html_cutoff = kwargs.pop('html_cutoff', cutoff_from_settings)

        self.html_cutoff_text = kwargs.pop(
            'html_cutoff_text',
            self.html_cutoff_text or _(api_settings.HTML_SELECT_CUTOFF_TEXT)
        )
        if not method_overridden('get_queryset', RelatedField, self):
            assert self.queryset is not None or kwargs.get('read_only'), (
                'Relational field must provide a `queryset` argument, '
                'override `get_queryset`, or set read_only=`True`.'
            )
        assert not (self.queryset is not None and kwargs.get('read_only')), (
            'Relational fields should not provide a `queryset` argument, '
            'when setting read_only=`True`.'
        )
        kwargs.pop('many', None)
        kwargs.pop('allow_empty', None)
        super().__init__(**kwargs)

    def __new__(cls, *args, **kwargs):
        # We override this method in order to automagically create
        # `ManyRelatedField` classes instead when `many=True` is set.
        if kwargs.pop('many', False):
            return cls.many_init(*args, **kwargs)
        return super().__new__(cls, *args, **kwargs)

    @classmethod
    def many_init(cls, *args, **kwargs):
        """
        This method handles creating a parent `ManyRelatedField` instance
        when the `many=True` keyword argument is passed.

        Typically you won't need to override this method.

        Note that we're over-cautious in passing most arguments to both parent
        and child classes in order to try to cover the general case. If you're
        overriding this method you'll probably want something much simpler, eg:

        @classmethod
        def many_init(cls, *args, **kwargs):
            kwargs['child'] = cls()
            return CustomManyRelatedField(*args, **kwargs)
        """
        list_kwargs = {'child_relation': cls(*args, **kwargs)}
        for key in kwargs:
            if key in MANY_RELATION_KWARGS:
                list_kwargs[key] = kwargs[key]
        return ManyRelatedField(**list_kwargs)

    def run_validation(self, data=empty):
        # We force empty strings to None values for relational fields.
        if data == '':
            data = None
        return super().run_validation(data)

    def get_queryset(self):
        queryset = self.queryset
        if isinstance(queryset, (QuerySet, Manager)):
            # Ensure queryset is re-evaluated whenever used.
            # Note that actually a `Manager` class may also be used as the
            # queryset argument. This occurs on ModelSerializer fields,
            # as it allows us to generate a more expressive 'repr' output
            # for the field.
            # Eg: 'MyRelationship(queryset=ExampleModel.objects.all())'
            queryset = queryset.all()
        return queryset

    def use_pk_only_optimization(self):
        return False

    def get_attribute(self, instance):
        if self.use_pk_only_optimization() and self.source_attrs:
            # Optimized case, return a mock object only containing the pk attribute.
            try:
                attribute_instance = get_attribute(instance, self.source_attrs[:-1])
                value = attribute_instance.serializable_value(self.source_attrs[-1])
                if is_simple_callable(value):
                    # Handle edge case where the relationship `source` argument
                    # points to a `get_relationship()` method on the model.
                    value = value()

                # Handle edge case where relationship `source` argument points
                # to an instance instead of a pk (e.g., a `@property`).
                value = getattr(value, 'pk', value)

                return PKOnlyObject(pk=value)
            except AttributeError:
                pass

        # Standard case, return the object instance.
        return super().get_attribute(instance)

    def get_choices(self, cutoff=None):
        queryset = self.get_queryset()
        if queryset is None:
            # Ensure that field.choices returns something sensible
            # even when accessed with a read-only field.
            return {}

        if cutoff is not None:
            queryset = queryset[:cutoff]

        return OrderedDict([
            (
                self.to_representation(item),
                self.display_value(item)
            )
            for item in queryset
        ])

    @property
    def choices(self):
        return self.get_choices()

    @property
    def grouped_choices(self):
        return self.choices

    def iter_options(self):
        return iter_options(
            self.get_choices(cutoff=self.html_cutoff),
            cutoff=self.html_cutoff,
            cutoff_text=self.html_cutoff_text
        )

    def display_value(self, instance):
        return str(instance)


class StringRelatedField(RelatedField):
    """
    A read only field that represents its targets using their
    plain string representation.
    """

    def __init__(self, **kwargs):
        kwargs['read_only'] = True
        super().__init__(**kwargs)

    def to_representation(self, value):
        return str(value)


class PrimaryKeyRelatedField(RelatedField):
    default_error_messages = {
        'required': _('This field is required.'),
        'does_not_exist': _('Invalid pk "{pk_value}" - object does not exist.'),
        'incorrect_type': _('Incorrect type. Expected pk value, received {data_type}.'),
    }

    def __init__(self, **kwargs):
        self.pk_field = kwargs.pop('pk_field', None)
        super().__init__(**kwargs)

    def use_pk_only_optimization(self):
        return True

    def to_internal_value(self, data):
        if self.pk_field is not None:
            data = self.pk_field.to_internal_value(data)
        queryset = self.get_queryset()
        try:
            if isinstance(data, bool):
                raise TypeError
            return queryset.get(pk=data)
        except ObjectDoesNotExist:
            self.fail('does_not_exist', pk_value=data)
        except (TypeError, ValueError):
            self.fail('incorrect_type', data_type=type(data).__name__)

    def to_representation(self, value):
        if self.pk_field is not None:
            return self.pk_field.to_representation(value.pk)
        return value.pk


class HyperlinkedRelatedField(RelatedField):
    lookup_field = 'pk'
    view_name = None

    default_error_messages = {
        'required': _('This field is required.'),
        'no_match': _('Invalid hyperlink - No URL match.'),
        'incorrect_match': _('Invalid hyperlink - Incorrect URL match.'),
        'does_not_exist': _('Invalid hyperlink - Object does not exist.'),
        'incorrect_type': _('Incorrect type. Expected URL string, received {data_type}.'),
    }

    def __init__(self, view_name=None, **kwargs):
        if view_name is not None:
            self.view_name = view_name
        assert self.view_name is not None, 'The `view_name` argument is required.'
        self.lookup_field = kwargs.pop('lookup_field', self.lookup_field)
        self.lookup_url_kwarg = kwargs.pop('lookup_url_kwarg', self.lookup_field)
        self.format = kwargs.pop('format', None)

        # We include this simply for dependency injection in tests.
        # We can't add it as a class attributes or it would expect an
        # implicit `self` argument to be passed.
        self.reverse = reverse

        super().__init__(**kwargs)

    def use_pk_only_optimization(self):
        return self.lookup_field == 'pk'

    def get_object(self, view_name, view_args, view_kwargs):
        """
        Return the object corresponding to a matched URL.

        Takes the matched URL conf arguments, and should return an
        object instance, or raise an `ObjectDoesNotExist` exception.
        """
        lookup_value = view_kwargs[self.lookup_url_kwarg]
        lookup_kwargs = {self.lookup_field: lookup_value}
        queryset = self.get_queryset()

        try:
            return queryset.get(**lookup_kwargs)
        except ValueError:
            exc = ObjectValueError(str(sys.exc_info()[1]))
            raise exc.with_traceback(sys.exc_info()[2])
        except TypeError:
            exc = ObjectTypeError(str(sys.exc_info()[1]))
            raise exc.with_traceback(sys.exc_info()[2])

    def get_url(self, obj, view_name, request, format):
        """
        Given an object, return the URL that hyperlinks to the object.

        May raise a `NoReverseMatch` if the `view_name` and `lookup_field`
        attributes are not configured to correctly match the URL conf.
        """
        # Unsaved objects will not yet have a valid URL.
        if hasattr(obj, 'pk') and obj.pk in (None, ''):
            return None

        lookup_value = getattr(obj, self.lookup_field)
        kwargs = {self.lookup_url_kwarg: lookup_value}
        return self.reverse(view_name, kwargs=kwargs, request=request, format=format)

    def to_internal_value(self, data):
        request = self.context.get('request')
        try:
            http_prefix = data.startswith(('http:', 'https:'))
        except AttributeError:
            self.fail('incorrect_type', data_type=type(data).__name__)

        if http_prefix:
            # If needed convert absolute URLs to relative path
            data = parse.urlparse(data).path
            prefix = get_script_prefix()
            if data.startswith(prefix):
                data = '/' + data[len(prefix):]

        data = uri_to_iri(parse.unquote(data))

        try:
            match = resolve(data)
        except Resolver404:
            self.fail('no_match')

        try:
            expected_viewname = request.versioning_scheme.get_versioned_viewname(
                self.view_name, request
            )
        except AttributeError:
            expected_viewname = self.view_name

        if match.view_name != expected_viewname:
            self.fail('incorrect_match')

        try:
            return self.get_object(match.view_name, match.args, match.kwargs)
        except (ObjectDoesNotExist, ObjectValueError, ObjectTypeError):
            self.fail('does_not_exist')

    def to_representation(self, value):
        assert 'request' in self.context, (
            "`%s` requires the request in the serializer"
            " context. Add `context={'request': request}` when instantiating "
            "the serializer." % self.__class__.__name__
        )

        request = self.context['request']
        format = self.context.get('format')

        # By default use whatever format is given for the current context
        # unless the target is a different type to the source.
        #
        # Eg. Consider a HyperlinkedIdentityField pointing from a json
        # representation to an html property of that representation...
        #
        # '/snippets/1/' should link to '/snippets/1/highlight/'
        # ...but...
        # '/snippets/1/.json' should link to '/snippets/1/highlight/.html'
        if format and self.format and self.format != format:
            format = self.format

        # Return the hyperlink, or error if incorrectly configured.
        try:
            url = self.get_url(value, self.view_name, request, format)
        except NoReverseMatch:
            msg = (
                'Could not resolve URL for hyperlinked relationship using '
                'view name "%s". You may have failed to include the related '
                'model in your API, or incorrectly configured the '
                '`lookup_field` attribute on this field.'
            )
            if value in ('', None):
                value_string = {'': 'the empty string', None: 'None'}[value]
                msg += (
                    " WARNING: The value of the field on the model instance "
                    "was %s, which may be why it didn't match any "
                    "entries in your URL conf." % value_string
                )
            raise ImproperlyConfigured(msg % self.view_name)

        if url is None:
            return None

        return Hyperlink(url, value)


class HyperlinkedIdentityField(HyperlinkedRelatedField):
    """
    A read-only field that represents the identity URL for an object, itself.

    This is in contrast to `HyperlinkedRelatedField` which represents the
    URL of relationships to other objects.
    """

    def __init__(self, view_name=None, **kwargs):
        assert view_name is not None, 'The `view_name` argument is required.'
        kwargs['read_only'] = True
        kwargs['source'] = '*'
        super().__init__(view_name, **kwargs)

    def use_pk_only_optimization(self):
        # We have the complete object instance already. We don't need
        # to run the 'only get the pk for this relationship' code.
        return False


class SlugRelatedField(RelatedField):
    """
    A read-write field that represents the target of the relationship
    by a unique 'slug' attribute.
    """
    default_error_messages = {
        'does_not_exist': _('Object with {slug_name}={value} does not exist.'),
        'invalid': _('Invalid value.'),
    }

    def __init__(self, slug_field=None, **kwargs):
        assert slug_field is not None, 'The `slug_field` argument is required.'
        self.slug_field = slug_field
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        queryset = self.get_queryset()
        try:
            return queryset.get(**{self.slug_field: data})
        except ObjectDoesNotExist:
            self.fail('does_not_exist', slug_name=self.slug_field, value=smart_str(data))
        except (TypeError, ValueError):
            self.fail('invalid')

    def to_representation(self, obj):
        return getattr(obj, self.slug_field)


class ManyRelatedField(Field):
    """
    Relationships with `many=True` transparently get coerced into instead being
    a ManyRelatedField with a child relationship.

    The `ManyRelatedField` class is responsible for handling iterating through
    the values and passing each one to the child relationship.

    This class is treated as private API.
    You shouldn't generally need to be using this class directly yourself,
    and should instead simply set 'many=True' on the relationship.
    """
    initial = []
    default_empty_html = []
    default_error_messages = {
        'not_a_list': _('Expected a list of items but got type "{input_type}".'),
        'empty': _('This list may not be empty.')
    }
    html_cutoff = None
    html_cutoff_text = None

    def __init__(self, child_relation=None, *args, **kwargs):
        self.child_relation = child_relation
        self.allow_empty = kwargs.pop('allow_empty', True)

        cutoff_from_settings = api_settings.HTML_SELECT_CUTOFF
        if cutoff_from_settings is not None:
            cutoff_from_settings = int(cutoff_from_settings)
        self.html_cutoff = kwargs.pop('html_cutoff', cutoff_from_settings)

        self.html_cutoff_text = kwargs.pop(
            'html_cutoff_text',
            self.html_cutoff_text or _(api_settings.HTML_SELECT_CUTOFF_TEXT)
        )
        assert child_relation is not None, '`child_relation` is a required argument.'
        super().__init__(*args, **kwargs)
        self.child_relation.bind(field_name='', parent=self)

    def get_value(self, dictionary):
        # We override the default field access in order to support
        # lists in HTML forms.
        if html.is_html_input(dictionary):
            # Don't return [] if the update is partial
            if self.field_name not in dictionary:
                if getattr(self.root, 'partial', False):
                    return empty
            return dictionary.getlist(self.field_name)

        return dictionary.get(self.field_name, empty)

    def to_internal_value(self, data):
        if isinstance(data, str) or not hasattr(data, '__iter__'):
            self.fail('not_a_list', input_type=type(data).__name__)
        if not self.allow_empty and len(data) == 0:
            self.fail('empty')

        return [
            self.child_relation.to_internal_value(item)
            for item in data
        ]

    def get_attribute(self, instance):
        # Can't have any relationships if not created
        if hasattr(instance, 'pk') and instance.pk is None:
            return []

        try:
            relationship = get_attribute(instance, self.source_attrs)
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

        return relationship.all() if hasattr(relationship, 'all') else relationship

    def to_representation(self, iterable):
        return [
            self.child_relation.to_representation(value)
            for value in iterable
        ]

    def get_choices(self, cutoff=None):
        return self.child_relation.get_choices(cutoff)

    @property
    def choices(self):
        return self.get_choices()

    @property
    def grouped_choices(self):
        return self.choices

    def iter_options(self):
        return iter_options(
            self.get_choices(cutoff=self.html_cutoff),
            cutoff=self.html_cutoff,
            cutoff_text=self.html_cutoff_text
        )
