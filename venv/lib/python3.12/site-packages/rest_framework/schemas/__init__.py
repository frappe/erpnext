"""
rest_framework.schemas

schemas:
    __init__.py
    generators.py   # Top-down schema generation
    inspectors.py   # Per-endpoint view introspection
    utils.py        # Shared helper functions
    views.py        # Houses `SchemaView`, `APIView` subclass.

We expose a minimal "public" API directly from `schemas`. This covers the
basic use-cases:

    from rest_framework.schemas import (
        AutoSchema,
        ManualSchema,
        get_schema_view,
        SchemaGenerator,
    )

Other access should target the submodules directly
"""
from rest_framework.settings import api_settings

from . import coreapi, openapi
from .coreapi import AutoSchema, ManualSchema, SchemaGenerator  # noqa
from .inspectors import DefaultSchema  # noqa


def get_schema_view(
        title=None, url=None, description=None, urlconf=None, renderer_classes=None,
        public=False, patterns=None, generator_class=None,
        authentication_classes=api_settings.DEFAULT_AUTHENTICATION_CLASSES,
        permission_classes=api_settings.DEFAULT_PERMISSION_CLASSES,
        version=None):
    """
    Return a schema view.
    """
    if generator_class is None:
        if coreapi.is_enabled():
            generator_class = coreapi.SchemaGenerator
        else:
            generator_class = openapi.SchemaGenerator

    generator = generator_class(
        title=title, url=url, description=description,
        urlconf=urlconf, patterns=patterns, version=version
    )

    # Avoid import cycle on APIView
    from .views import SchemaView
    return SchemaView.as_view(
        renderer_classes=renderer_classes,
        schema_generator=generator,
        public=public,
        authentication_classes=authentication_classes,
        permission_classes=permission_classes,
    )
