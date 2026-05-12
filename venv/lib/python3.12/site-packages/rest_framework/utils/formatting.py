"""
Utility functions to return a formatted name and description for a given view.
"""
import re

from django.utils.encoding import force_str
from django.utils.html import escape
from django.utils.safestring import mark_safe

from rest_framework.compat import apply_markdown


def remove_trailing_string(content, trailing):
    """
    Strip trailing component `trailing` from `content` if it exists.
    Used when generating names from view classes.
    """
    if content.endswith(trailing) and content != trailing:
        return content[:-len(trailing)]
    return content


def dedent(content):
    """
    Remove leading indent from a block of text.
    Used when generating descriptions from docstrings.

    Note that python's `textwrap.dedent` doesn't quite cut it,
    as it fails to dedent multiline docstrings that include
    unindented text on the initial line.
    """
    content = force_str(content)
    lines = [line for line in content.splitlines()[1:] if line.lstrip()]

    # unindent the content if needed
    if lines:
        whitespace_counts = min([len(line) - len(line.lstrip(' ')) for line in lines])
        tab_counts = min([len(line) - len(line.lstrip('\t')) for line in lines])
        if whitespace_counts:
            whitespace_pattern = '^' + (' ' * whitespace_counts)
            content = re.sub(re.compile(whitespace_pattern, re.MULTILINE), '', content)
        elif tab_counts:
            whitespace_pattern = '^' + ('\t' * tab_counts)
            content = re.sub(re.compile(whitespace_pattern, re.MULTILINE), '', content)
    return content.strip()


def camelcase_to_spaces(content):
    """
    Translate 'CamelCaseNames' to 'Camel Case Names'.
    Used when generating names from view classes.
    """
    camelcase_boundary = '(((?<=[a-z])[A-Z])|([A-Z](?![A-Z]|$)))'
    content = re.sub(camelcase_boundary, ' \\1', content).strip()
    return ' '.join(content.split('_')).title()


def markup_description(description):
    """
    Apply HTML markup to the given description.
    """
    if apply_markdown:
        description = apply_markdown(description)
    else:
        description = escape(description).replace('\n', '<br />')
        description = '<p>' + description + '</p>'
    return mark_safe(description)


class lazy_format:
    """
    Delay formatting until it's actually needed.

    Useful when the format string or one of the arguments is lazy.

    Not using Django's lazy because it is too slow.
    """
    __slots__ = ('format_string', 'args', 'kwargs', 'result')

    def __init__(self, format_string, *args, **kwargs):
        self.result = None
        self.format_string = format_string
        self.args = args
        self.kwargs = kwargs

    def __str__(self):
        if self.result is None:
            self.result = self.format_string.format(*self.args, **self.kwargs)
            self.format_string, self.args, self.kwargs = None, None, None
        return self.result

    def __mod__(self, value):
        return str(self) % value
