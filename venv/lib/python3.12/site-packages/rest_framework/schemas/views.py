"""
views.py        # Houses `SchemaView`, `APIView` subclass.

See schemas.__init__.py for package overview.
"""
from rest_framework import exceptions, renderers
from rest_framework.response import Response
from rest_framework.schemas import coreapi
from rest_framework.settings import api_settings
from rest_framework.views import APIView


class SchemaView(APIView):
    _ignore_model_permissions = True
    schema = None  # exclude from schema
    renderer_classes = None
    schema_generator = None
    public = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.renderer_classes is None:
            if coreapi.is_enabled():
                self.renderer_classes = [
                    renderers.CoreAPIOpenAPIRenderer,
                    renderers.CoreJSONRenderer
                ]
            else:
                self.renderer_classes = [
                    renderers.OpenAPIRenderer,
                    renderers.JSONOpenAPIRenderer,
                ]
            if renderers.BrowsableAPIRenderer in api_settings.DEFAULT_RENDERER_CLASSES:
                self.renderer_classes += [renderers.BrowsableAPIRenderer]

    def get(self, request, *args, **kwargs):
        schema = self.schema_generator.get_schema(request, self.public)
        if schema is None:
            raise exceptions.PermissionDenied()
        return Response(schema)

    def handle_exception(self, exc):
        # Schema renderers do not render exceptions, so re-perform content
        # negotiation with default renderers.
        self.renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES
        neg = self.perform_content_negotiation(self.request, force=True)
        self.request.accepted_renderer, self.request.accepted_media_type = neg
        return super().handle_exception(exc)
