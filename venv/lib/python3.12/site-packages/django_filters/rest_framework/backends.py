import warnings

from django.template import loader

from .. import compat, utils
from . import filters, filterset


class DjangoFilterBackend:
    filterset_base = filterset.FilterSet
    raise_exception = True

    @property
    def template(self):
        if compat.is_crispy():
            return "django_filters/rest_framework/crispy_form.html"
        return "django_filters/rest_framework/form.html"

    def get_filterset(self, request, queryset, view):
        filterset_class = self.get_filterset_class(view, queryset)
        if filterset_class is None:
            return None

        kwargs = self.get_filterset_kwargs(request, queryset, view)
        return filterset_class(**kwargs)

    def get_filterset_class(self, view, queryset=None):
        """
        Return the `FilterSet` class used to filter the queryset.
        """
        filterset_class = getattr(view, "filterset_class", None)
        filterset_fields = getattr(view, "filterset_fields", None)

        if filterset_class:
            filterset_model = filterset_class._meta.model

            # FilterSets do not need to specify a Meta class
            if filterset_model and queryset is not None:
                assert issubclass(
                    queryset.model, filterset_model
                ), "FilterSet model %s does not match queryset model %s" % (
                    filterset_model,
                    queryset.model,
                )

            return filterset_class

        if filterset_fields and queryset is not None:
            MetaBase = getattr(self.filterset_base, "Meta", object)

            class AutoFilterSet(self.filterset_base):
                class Meta(MetaBase):
                    model = queryset.model
                    fields = filterset_fields

            return AutoFilterSet

        return None

    def get_filterset_kwargs(self, request, queryset, view):
        return {
            "data": request.query_params,
            "queryset": queryset,
            "request": request,
        }

    def filter_queryset(self, request, queryset, view):
        filterset = self.get_filterset(request, queryset, view)
        if filterset is None:
            return queryset

        if not filterset.is_valid() and self.raise_exception:
            raise utils.translate_validation(filterset.errors)
        return filterset.qs

    def to_html(self, request, queryset, view):
        filterset = self.get_filterset(request, queryset, view)
        if filterset is None:
            return None

        template = loader.get_template(self.template)
        context = {"filter": filterset}
        return template.render(context, request)

    def get_coreschema_field(self, field):
        if isinstance(field, filters.NumberFilter):
            field_cls = compat.coreschema.Number
        else:
            field_cls = compat.coreschema.String
        return field_cls(description=str(field.extra.get("help_text", "")))

    def get_schema_fields(self, view):
        # This is not compatible with widgets where the query param differs from the
        # filter's attribute name. Notably, this includes `MultiWidget`, where query
        # params will be of the format `<name>_0`, `<name>_1`, etc...
        assert (
            compat.coreapi is not None
        ), "coreapi must be installed to use `get_schema_fields()`"
        assert (
            compat.coreschema is not None
        ), "coreschema must be installed to use `get_schema_fields()`"

        try:
            queryset = view.get_queryset()
        except Exception:
            queryset = None
            warnings.warn(
                "{} is not compatible with schema generation".format(view.__class__)
            )

        filterset_class = self.get_filterset_class(view, queryset)

        return (
            []
            if not filterset_class
            else [
                compat.coreapi.Field(
                    name=field_name,
                    required=field.extra["required"],
                    location="query",
                    schema=self.get_coreschema_field(field),
                )
                for field_name, field in filterset_class.base_filters.items()
            ]
        )

    def get_schema_operation_parameters(self, view):
        try:
            queryset = view.get_queryset()
        except Exception:
            queryset = None
            warnings.warn(
                "{} is not compatible with schema generation".format(view.__class__)
            )

        filterset_class = self.get_filterset_class(view, queryset)

        if not filterset_class:
            return []

        parameters = []
        for field_name, field in filterset_class.base_filters.items():
            parameter = {
                "name": field_name,
                "required": field.extra["required"],
                "in": "query",
                "description": field.label if field.label is not None else field_name,
                "schema": {
                    "type": "string",
                },
            }
            if field.extra and "choices" in field.extra:
                parameter["schema"]["enum"] = [c[0] for c in field.extra["choices"]]
            parameters.append(parameter)
        return parameters
