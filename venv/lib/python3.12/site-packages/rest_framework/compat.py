"""
The `compat` module provides support for backwards compatibility with older
versions of Django/Python, and compatibility wrappers around optional packages.
"""
import django
from django.conf import settings
from django.views.generic import View


def unicode_http_header(value):
    # Coerce HTTP header value to unicode.
    if isinstance(value, bytes):
        return value.decode('iso-8859-1')
    return value


def distinct(queryset, base):
    if settings.DATABASES[queryset.db]["ENGINE"] == "django.db.backends.oracle":
        # distinct analogue for Oracle users
        return base.filter(pk__in=set(queryset.values_list('pk', flat=True)))
    return queryset.distinct()


# django.contrib.postgres requires psycopg2
try:
    from django.contrib.postgres import fields as postgres_fields
except ImportError:
    postgres_fields = None


# coreapi is required for CoreAPI schema generation
try:
    import coreapi
except ImportError:
    coreapi = None

# uritemplate is required for OpenAPI and CoreAPI schema generation
try:
    import uritemplate
except ImportError:
    uritemplate = None


# coreschema is optional
try:
    import coreschema
except ImportError:
    coreschema = None


# pyyaml is optional
try:
    import yaml
except ImportError:
    yaml = None


# requests is optional
try:
    import requests
except ImportError:
    requests = None


# PATCH method is not implemented by Django
if 'patch' not in View.http_method_names:
    View.http_method_names = View.http_method_names + ['patch']


# Markdown is optional (version 3.0+ required)
try:
    import markdown

    HEADERID_EXT_PATH = 'markdown.extensions.toc'
    LEVEL_PARAM = 'baselevel'

    def apply_markdown(text):
        """
        Simple wrapper around :func:`markdown.markdown` to set the base level
        of '#' style headers to <h2>.
        """
        extensions = [HEADERID_EXT_PATH]
        extension_configs = {
            HEADERID_EXT_PATH: {
                LEVEL_PARAM: '2'
            }
        }
        md = markdown.Markdown(
            extensions=extensions, extension_configs=extension_configs
        )
        md_filter_add_syntax_highlight(md)
        return md.convert(text)
except ImportError:
    apply_markdown = None
    markdown = None


try:
    import pygments
    from pygments.formatters import HtmlFormatter
    from pygments.lexers import TextLexer, get_lexer_by_name

    def pygments_highlight(text, lang, style):
        lexer = get_lexer_by_name(lang, stripall=False)
        formatter = HtmlFormatter(nowrap=True, style=style)
        return pygments.highlight(text, lexer, formatter)

    def pygments_css(style):
        formatter = HtmlFormatter(style=style)
        return formatter.get_style_defs('.highlight')

except ImportError:
    pygments = None

    def pygments_highlight(text, lang, style):
        return text

    def pygments_css(style):
        return None

if markdown is not None and pygments is not None:
    # starting from this blogpost and modified to support current markdown extensions API
    # https://zerokspot.com/weblog/2008/06/18/syntax-highlighting-in-markdown-with-pygments/

    import re

    from markdown.preprocessors import Preprocessor

    class CodeBlockPreprocessor(Preprocessor):
        pattern = re.compile(
            r'^\s*``` *([^\n]+)\n(.+?)^\s*```', re.M | re.S)

        formatter = HtmlFormatter()

        def run(self, lines):
            def repl(m):
                try:
                    lexer = get_lexer_by_name(m.group(1))
                except (ValueError, NameError):
                    lexer = TextLexer()
                code = m.group(2).replace('\t', '    ')
                code = pygments.highlight(code, lexer, self.formatter)
                code = code.replace('\n\n', '\n&nbsp;\n').replace('\n', '<br />').replace('\\@', '@')
                return '\n\n%s\n\n' % code
            ret = self.pattern.sub(repl, "\n".join(lines))
            return ret.split("\n")

    def md_filter_add_syntax_highlight(md):
        md.preprocessors.register(CodeBlockPreprocessor(), 'highlight', 40)
        return True
else:
    def md_filter_add_syntax_highlight(md):
        return False


if django.VERSION >= (4, 2):
    # Django 4.2+: use the stock parse_header_parameters function
    # Note: Django 4.1 also has an implementation of parse_header_parameters
    #       which is slightly different from the one in 4.2, it needs
    #       the compatibility shim as well.
    from django.utils.http import parse_header_parameters
else:
    # Django <= 4.1: create a compatibility shim for parse_header_parameters
    from django.http.multipartparser import parse_header

    def parse_header_parameters(line):
        # parse_header works with bytes, but parse_header_parameters
        # works with strings. Call encode to convert the line to bytes.
        main_value_pair, params = parse_header(line.encode())
        return main_value_pair, {
            # parse_header will convert *some* values to string.
            # parse_header_parameters converts *all* values to string.
            # Make sure all values are converted by calling decode on
            # any remaining non-string values.
            k: v if isinstance(v, str) else v.decode()
            for k, v in params.items()
        }


# `separators` argument to `json.dumps()` differs between 2.x and 3.x
# See: https://bugs.python.org/issue22767
SHORT_SEPARATORS = (',', ':')
LONG_SEPARATORS = (', ', ': ')
INDENT_SEPARATORS = (',', ': ')
