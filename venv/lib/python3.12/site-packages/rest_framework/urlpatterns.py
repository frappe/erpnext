from django.urls import URLResolver, include, path, re_path, register_converter
from django.urls.resolvers import RoutePattern

from rest_framework.settings import api_settings


def _get_format_path_converter(suffix_kwarg, allowed):
    if allowed:
        if len(allowed) == 1:
            allowed_pattern = allowed[0]
        else:
            allowed_pattern = '(?:%s)' % '|'.join(allowed)
        suffix_pattern = r"\.%s/?" % allowed_pattern
    else:
        suffix_pattern = r"\.[a-z0-9]+/?"

    class FormatSuffixConverter:
        regex = suffix_pattern

        def to_python(self, value):
            return value.strip('./')

        def to_url(self, value):
            return '.' + value + '/'

    converter_name = 'drf_format_suffix'
    if allowed:
        converter_name += '_' + '_'.join(allowed)

    return converter_name, FormatSuffixConverter


def apply_suffix_patterns(urlpatterns, suffix_pattern, suffix_required, suffix_route=None):
    ret = []
    for urlpattern in urlpatterns:
        if isinstance(urlpattern, URLResolver):
            # Set of included URL patterns
            regex = urlpattern.pattern.regex.pattern
            namespace = urlpattern.namespace
            app_name = urlpattern.app_name
            kwargs = urlpattern.default_kwargs
            # Add in the included patterns, after applying the suffixes
            patterns = apply_suffix_patterns(urlpattern.url_patterns,
                                             suffix_pattern,
                                             suffix_required,
                                             suffix_route)

            # if the original pattern was a RoutePattern we need to preserve it
            if isinstance(urlpattern.pattern, RoutePattern):
                assert path is not None
                route = str(urlpattern.pattern)
                new_pattern = path(route, include((patterns, app_name), namespace), kwargs)
            else:
                new_pattern = re_path(regex, include((patterns, app_name), namespace), kwargs)

            ret.append(new_pattern)
        else:
            # Regular URL pattern
            regex = urlpattern.pattern.regex.pattern.rstrip('$').rstrip('/') + suffix_pattern
            view = urlpattern.callback
            kwargs = urlpattern.default_args
            name = urlpattern.name
            # Add in both the existing and the new urlpattern
            if not suffix_required:
                ret.append(urlpattern)

            # if the original pattern was a RoutePattern we need to preserve it
            if isinstance(urlpattern.pattern, RoutePattern):
                assert path is not None
                assert suffix_route is not None
                route = str(urlpattern.pattern).rstrip('$').rstrip('/') + suffix_route
                new_pattern = path(route, view, kwargs, name)
            else:
                new_pattern = re_path(regex, view, kwargs, name)

            ret.append(new_pattern)

    return ret


def format_suffix_patterns(urlpatterns, suffix_required=False, allowed=None):
    """
    Supplement existing urlpatterns with corresponding patterns that also
    include a '.format' suffix.  Retains urlpattern ordering.

    urlpatterns:
        A list of URL patterns.

    suffix_required:
        If `True`, only suffixed URLs will be generated, and non-suffixed
        URLs will not be used.  Defaults to `False`.

    allowed:
        An optional tuple/list of allowed suffixes.  eg ['json', 'api']
        Defaults to `None`, which allows any suffix.
    """
    suffix_kwarg = api_settings.FORMAT_SUFFIX_KWARG
    if allowed:
        if len(allowed) == 1:
            allowed_pattern = allowed[0]
        else:
            allowed_pattern = '(%s)' % '|'.join(allowed)
        suffix_pattern = r'\.(?P<%s>%s)/?$' % (suffix_kwarg, allowed_pattern)
    else:
        suffix_pattern = r'\.(?P<%s>[a-z0-9]+)/?$' % suffix_kwarg

    converter_name, suffix_converter = _get_format_path_converter(suffix_kwarg, allowed)
    register_converter(suffix_converter, converter_name)

    suffix_route = '<%s:%s>' % (converter_name, suffix_kwarg)

    return apply_suffix_patterns(urlpatterns, suffix_pattern, suffix_required, suffix_route)
