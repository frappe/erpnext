from django.core.management.base import BaseCommand
from django.utils.module_loading import import_string

from rest_framework import renderers
from rest_framework.schemas import coreapi
from rest_framework.schemas.openapi import SchemaGenerator

OPENAPI_MODE = 'openapi'
COREAPI_MODE = 'coreapi'


class Command(BaseCommand):
    help = "Generates configured API schema for project."

    def get_mode(self):
        return COREAPI_MODE if coreapi.is_enabled() else OPENAPI_MODE

    def add_arguments(self, parser):
        parser.add_argument('--title', dest="title", default='', type=str)
        parser.add_argument('--url', dest="url", default=None, type=str)
        parser.add_argument('--description', dest="description", default=None, type=str)
        if self.get_mode() == COREAPI_MODE:
            parser.add_argument('--format', dest="format", choices=['openapi', 'openapi-json', 'corejson'], default='openapi', type=str)
        else:
            parser.add_argument('--format', dest="format", choices=['openapi', 'openapi-json'], default='openapi', type=str)
        parser.add_argument('--urlconf', dest="urlconf", default=None, type=str)
        parser.add_argument('--generator_class', dest="generator_class", default=None, type=str)
        parser.add_argument('--file', dest="file", default=None, type=str)
        parser.add_argument('--api_version', dest="api_version", default='', type=str)

    def handle(self, *args, **options):
        if options['generator_class']:
            generator_class = import_string(options['generator_class'])
        else:
            generator_class = self.get_generator_class()
        generator = generator_class(
            url=options['url'],
            title=options['title'],
            description=options['description'],
            urlconf=options['urlconf'],
            version=options['api_version'],
        )
        schema = generator.get_schema(request=None, public=True)
        renderer = self.get_renderer(options['format'])
        output = renderer.render(schema, renderer_context={})

        if options['file']:
            with open(options['file'], 'wb') as f:
                f.write(output)
        else:
            self.stdout.write(output.decode())

    def get_renderer(self, format):
        if self.get_mode() == COREAPI_MODE:
            renderer_cls = {
                'corejson': renderers.CoreJSONRenderer,
                'openapi': renderers.CoreAPIOpenAPIRenderer,
                'openapi-json': renderers.CoreAPIJSONOpenAPIRenderer,
            }[format]
            return renderer_cls()

        renderer_cls = {
            'openapi': renderers.OpenAPIRenderer,
            'openapi-json': renderers.JSONOpenAPIRenderer,
        }[format]
        return renderer_cls()

    def get_generator_class(self):
        if self.get_mode() == COREAPI_MODE:
            return coreapi.SchemaGenerator
        return SchemaGenerator
