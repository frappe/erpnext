"""
Helper functions for creating user-friendly representations
of serializer classes and serializer fields.
"""
import re

from django.db import models
from django.utils.encoding import force_str
from django.utils.functional import Promise


def manager_repr(value):
    model = value.model
    opts = model._meta
    names_and_managers = [
        (manager.name, manager)
        for manager
        in opts.managers
    ]
    for manager_name, manager_instance in names_and_managers:
        if manager_instance == value:
            return '%s.%s.all()' % (model._meta.object_name, manager_name)
    return repr(value)


def smart_repr(value):
    if isinstance(value, models.Manager):
        return manager_repr(value)

    if isinstance(value, Promise) and value._delegate_text:
        value = force_str(value)

    value = repr(value)

    # Representations like u'help text'
    # should simply be presented as 'help text'
    if value.startswith("u'") and value.endswith("'"):
        return value[1:]

    # Representations like
    # <django.core.validators.RegexValidator object at 0x1047af050>
    # Should be presented as
    # <django.core.validators.RegexValidator object>
    return re.sub(' at 0x[0-9A-Fa-f]{4,32}>', '>', value)


def field_repr(field, force_many=False):
    kwargs = field._kwargs
    if force_many:
        kwargs = kwargs.copy()
        kwargs['many'] = True
        kwargs.pop('child', None)

    arg_string = ', '.join([smart_repr(val) for val in field._args])
    kwarg_string = ', '.join([
        '%s=%s' % (key, smart_repr(val))
        for key, val in sorted(kwargs.items())
    ])
    if arg_string and kwarg_string:
        arg_string += ', '

    if force_many:
        class_name = force_many.__class__.__name__
    else:
        class_name = field.__class__.__name__

    return "%s(%s%s)" % (class_name, arg_string, kwarg_string)


def serializer_repr(serializer, indent, force_many=None):
    ret = field_repr(serializer, force_many) + ':'
    indent_str = '    ' * indent

    if force_many:
        fields = force_many.fields
    else:
        fields = serializer.fields

    for field_name, field in fields.items():
        ret += '\n' + indent_str + field_name + ' = '
        if hasattr(field, 'fields'):
            ret += serializer_repr(field, indent + 1)
        elif hasattr(field, 'child'):
            ret += list_repr(field, indent + 1)
        elif hasattr(field, 'child_relation'):
            ret += field_repr(field.child_relation, force_many=field.child_relation)
        else:
            ret += field_repr(field)

    if serializer.validators:
        ret += '\n' + indent_str + 'class Meta:'
        ret += '\n' + indent_str + '    validators = ' + smart_repr(serializer.validators)

    return ret


def list_repr(serializer, indent):
    child = serializer.child
    if hasattr(child, 'fields'):
        return serializer_repr(serializer, indent, force_many=child)
    return field_repr(serializer)
