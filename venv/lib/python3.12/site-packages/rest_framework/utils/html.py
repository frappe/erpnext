"""
Helpers for dealing with HTML input.
"""
import re

from django.utils.datastructures import MultiValueDict


def is_html_input(dictionary):
    # MultiDict type datastructures are used to represent HTML form input,
    # which may have more than one value for each key.
    return hasattr(dictionary, 'getlist')


def parse_html_list(dictionary, prefix='', default=None):
    """
    Used to support list values in HTML forms.
    Supports lists of primitives and/or dictionaries.

    * List of primitives.

    {
        '[0]': 'abc',
        '[1]': 'def',
        '[2]': 'hij'
    }
        -->
    [
        'abc',
        'def',
        'hij'
    ]

    * List of dictionaries.

    {
        '[0]foo': 'abc',
        '[0]bar': 'def',
        '[1]foo': 'hij',
        '[1]bar': 'klm',
    }
        -->
    [
        {'foo': 'abc', 'bar': 'def'},
        {'foo': 'hij', 'bar': 'klm'}
    ]

    :returns a list of objects, or the value specified in ``default`` if the list is empty
    """
    ret = {}
    regex = re.compile(r'^%s\[([0-9]+)\](.*)$' % re.escape(prefix))
    for field, value in dictionary.items():
        match = regex.match(field)
        if not match:
            continue
        index, key = match.groups()
        index = int(index)
        if not key:
            ret[index] = value
        elif isinstance(ret.get(index), dict):
            ret[index][key] = value
        else:
            ret[index] = MultiValueDict({key: [value]})

    # return the items of the ``ret`` dict, sorted by key, or ``default`` if the dict is empty
    return [ret[item] for item in sorted(ret)] if ret else default


def parse_html_dict(dictionary, prefix=''):
    """
    Used to support dictionary values in HTML forms.

    {
        'profile.username': 'example',
        'profile.email': 'example@example.com',
    }
        -->
    {
        'profile': {
            'username': 'example',
            'email': 'example@example.com'
        }
    }
    """
    ret = MultiValueDict()
    regex = re.compile(r'^%s\.(.+)$' % re.escape(prefix))
    for field in dictionary:
        match = regex.match(field)
        if not match:
            continue
        key = match.groups()[0]
        value = dictionary.getlist(field)
        ret.setlist(key, value)

    return ret
