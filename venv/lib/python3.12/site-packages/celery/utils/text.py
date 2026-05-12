"""Text formatting utilities."""
import io
import re
from collections.abc import Callable
from functools import partial
from pprint import pformat
from textwrap import fill
from typing import Any, List, Mapping, Pattern

__all__ = (
    'abbr', 'abbrtask', 'dedent', 'dedent_initial',
    'ensure_newlines', 'ensure_sep',
    'fill_paragraphs', 'indent', 'join',
    'pluralize', 'pretty', 'str_to_list', 'simple_format', 'truncate',
)

UNKNOWN_SIMPLE_FORMAT_KEY = """
Unknown format %{0} in string {1!r}.
Possible causes: Did you forget to escape the expand sign (use '%%{0!r}'),
or did you escape and the value was expanded twice? (%%N -> %N -> %hostname)?
""".strip()

RE_FORMAT = re.compile(r'%(\w)')


def str_to_list(s):
    # type: (str) -> List[str]
    """Convert string to list."""
    if isinstance(s, str):
        return s.split(',')
    return s


def dedent_initial(s, n=4):
    # type: (str, int) -> str
    """Remove indentation from first line of text."""
    return s[n:] if s[:n] == ' ' * n else s


def dedent(s, n=4, sep='\n'):
    # type: (str, int, str) -> str
    """Remove indentation."""
    return sep.join(dedent_initial(l) for l in s.splitlines())


def fill_paragraphs(s, width, sep='\n'):
    # type: (str, int, str) -> str
    """Fill paragraphs with newlines (or custom separator)."""
    return sep.join(fill(p, width) for p in s.split(sep))


def join(l, sep='\n'):
    # type: (str, str) -> str
    """Concatenate list of strings."""
    return sep.join(v for v in l if v)


def ensure_sep(sep, s, n=2):
    # type: (str, str, int) -> str
    """Ensure text s ends in separator sep'."""
    return s + sep * (n - s.count(sep))


ensure_newlines = partial(ensure_sep, '\n')


def abbr(S, max, ellipsis='...'):
    # type: (str, int, str) -> str
    """Abbreviate word."""
    if S is None:
        return '???'
    if len(S) > max:
        return ellipsis and (S[:max - len(ellipsis)] + ellipsis) or S[:max]
    return S


def abbrtask(S, max):
    # type: (str, int) -> str
    """Abbreviate task name."""
    if S is None:
        return '???'
    if len(S) > max:
        module, _, cls = S.rpartition('.')
        module = abbr(module, max - len(cls) - 3, False)
        return module + '[.]' + cls
    return S


def indent(t, indent=0, sep='\n'):
    # type: (str, int, str) -> str
    """Indent text."""
    return sep.join(' ' * indent + p for p in t.split(sep))


def truncate(s, maxlen=128, suffix='...'):
    # type: (str, int, str) -> str
    """Truncate text to a maximum number of characters."""
    if maxlen and len(s) >= maxlen:
        return s[:maxlen].rsplit(' ', 1)[0] + suffix
    return s


def pluralize(n, text, suffix='s'):
    # type: (int, str, str) -> str
    """Pluralize term when n is greater than one."""
    if n != 1:
        return text + suffix
    return text


def pretty(value, width=80, nl_width=80, sep='\n', **kw):
    # type: (str, int, int, str, **Any) -> str
    """Format value for printing to console."""
    if isinstance(value, dict):
        return f'{{{sep} {pformat(value, 4, nl_width)[1:]}'
    elif isinstance(value, tuple):
        return '{}{}{}'.format(
            sep, ' ' * 4, pformat(value, width=nl_width, **kw),
        )
    else:
        return pformat(value, width=width, **kw)


def match_case(s, other):
    # type: (str, str) -> str
    return s.upper() if other.isupper() else s.lower()


def simple_format(s, keys, pattern=RE_FORMAT, expand=r'\1'):
    # type: (str, Mapping[str, str], Pattern, str) -> str
    """Format string, expanding abbreviations in keys'."""
    if s:
        keys.setdefault('%', '%')

        def resolve(match):
            key = match.expand(expand)
            try:
                resolver = keys[key]
            except KeyError:
                raise ValueError(UNKNOWN_SIMPLE_FORMAT_KEY.format(key, s))
            if isinstance(resolver, Callable):
                return resolver()
            return resolver

        return pattern.sub(resolve, s)
    return s


def remove_repeating_from_task(task_name, s):
    # type: (str, str) -> str
    """Given task name, remove repeating module names.

    Example:
        >>> remove_repeating_from_task(
        ...     'tasks.add',
        ...     'tasks.add(2, 2), tasks.mul(3), tasks.div(4)')
        'tasks.add(2, 2), mul(3), div(4)'
    """
    # This is used by e.g. repr(chain), to remove repeating module names.
    #  - extract the module part of the task name
    module = str(task_name).rpartition('.')[0] + '.'
    return remove_repeating(module, s)


def remove_repeating(substr, s):
    # type: (str, str) -> str
    """Remove repeating module names from string.

    Arguments:
        task_name (str): Task name (full path including module),
            to use as the basis for removing module names.
        s (str): The string we want to work on.

    Example:

        >>> _shorten_names(
        ...    'x.tasks.add',
        ...    'x.tasks.add(2, 2) | x.tasks.add(4) | x.tasks.mul(8)',
        ... )
        'x.tasks.add(2, 2) | add(4) | mul(8)'
    """
    # find the first occurrence of substr in the string.
    index = s.find(substr)
    if index >= 0:
        return ''.join([
            # leave the first occurrence of substr untouched.
            s[:index + len(substr)],
            # strip seen substr from the rest of the string.
            s[index + len(substr):].replace(substr, ''),
        ])
    return s


StringIO = io.StringIO
_SIO_write = StringIO.write
_SIO_init = StringIO.__init__


class WhateverIO(StringIO):
    """StringIO that takes bytes or str."""

    def __init__(self, v=None, *a, **kw):
        _SIO_init(self, v.decode() if isinstance(v, bytes) else v, *a, **kw)

    def write(self, data):
        _SIO_write(self, data.decode() if isinstance(data, bytes) else data)
