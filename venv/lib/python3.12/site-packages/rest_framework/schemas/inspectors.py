"""
inspectors.py   # Per-endpoint view introspection

See schemas.__init__.py for package overview.
"""
import re
from weakref import WeakKeyDictionary

from django.utils.encoding import smart_str

from rest_framework.settings import api_settings
from rest_framework.utils import formatting


class ViewInspector:
    """
    Descriptor class on APIView.

    Provide subclass for per-view schema generation
    """

    # Used in _get_description_section()
    header_regex = re.compile('^[a-zA-Z][0-9A-Za-z_]*:')

    def __init__(self):
        self.instance_schemas = WeakKeyDictionary()

    def __get__(self, instance, owner):
        """
        Enables `ViewInspector` as a Python _Descriptor_.

        This is how `view.schema` knows about `view`.

        `__get__` is called when the descriptor is accessed on the owner.
        (That will be when view.schema is called in our case.)

        `owner` is always the owner class. (An APIView, or subclass for us.)
        `instance` is the view instance or `None` if accessed from the class,
        rather than an instance.

        See: https://docs.python.org/3/howto/descriptor.html for info on
        descriptor usage.
        """
        if instance in self.instance_schemas:
            return self.instance_schemas[instance]

        self.view = instance
        return self

    def __set__(self, instance, other):
        self.instance_schemas[instance] = other
        if other is not None:
            other.view = instance

    @property
    def view(self):
        """View property."""
        assert self._view is not None, (
            "Schema generation REQUIRES a view instance. (Hint: you accessed "
            "`schema` from the view class rather than an instance.)"
        )
        return self._view

    @view.setter
    def view(self, value):
        self._view = value

    @view.deleter
    def view(self):
        self._view = None

    def get_description(self, path, method):
        """
        Determine a path description.

        This will be based on the method docstring if one exists,
        or else the class docstring.
        """
        view = self.view

        method_name = getattr(view, 'action', method.lower())
        method_docstring = getattr(view, method_name, None).__doc__
        if method_docstring:
            # An explicit docstring on the method or action.
            return self._get_description_section(view, method.lower(), formatting.dedent(smart_str(method_docstring)))
        else:
            return self._get_description_section(view, getattr(view, 'action', method.lower()),
                                                 view.get_view_description())

    def _get_description_section(self, view, header, description):
        lines = [line for line in description.splitlines()]
        current_section = ''
        sections = {'': ''}

        for line in lines:
            if self.header_regex.match(line):
                current_section, separator, lead = line.partition(':')
                sections[current_section] = lead.strip()
            else:
                sections[current_section] += '\n' + line

        # TODO: SCHEMA_COERCE_METHOD_NAMES appears here and in `SchemaGenerator.get_keys`
        coerce_method_names = api_settings.SCHEMA_COERCE_METHOD_NAMES
        if header in sections:
            return sections[header].strip()
        if header in coerce_method_names:
            if coerce_method_names[header] in sections:
                return sections[coerce_method_names[header]].strip()
        return sections[''].strip()


class DefaultSchema(ViewInspector):
    """Allows overriding AutoSchema using DEFAULT_SCHEMA_CLASS setting"""
    def __get__(self, instance, owner):
        result = super().__get__(instance, owner)
        if not isinstance(result, DefaultSchema):
            return result

        inspector_class = api_settings.DEFAULT_SCHEMA_CLASS
        assert issubclass(inspector_class, ViewInspector), (
            "DEFAULT_SCHEMA_CLASS must be set to a ViewInspector (usually an AutoSchema) subclass"
        )
        inspector = inspector_class()
        inspector.view = instance
        return inspector
