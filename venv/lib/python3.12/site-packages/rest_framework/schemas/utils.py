"""
utils.py        # Shared helper functions

See schemas.__init__.py for package overview.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _

from rest_framework.mixins import RetrieveModelMixin


def is_list_view(path, method, view):
    """
    Return True if the given path/method appears to represent a list view.
    """
    if hasattr(view, 'action'):
        # Viewsets have an explicitly defined action, which we can inspect.
        return view.action == 'list'

    if method.lower() != 'get':
        return False
    if isinstance(view, RetrieveModelMixin):
        return False
    path_components = path.strip('/').split('/')
    if path_components and '{' in path_components[-1]:
        return False
    return True


def get_pk_description(model, model_field):
    if isinstance(model_field, models.AutoField):
        value_type = _('unique integer value')
    elif isinstance(model_field, models.UUIDField):
        value_type = _('UUID string')
    else:
        value_type = _('unique value')

    return _('A {value_type} identifying this {name}.').format(
        value_type=value_type,
        name=model._meta.verbose_name,
    )
