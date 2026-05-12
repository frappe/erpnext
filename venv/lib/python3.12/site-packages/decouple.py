# coding: utf-8
import os
import sys
import string
from shlex import shlex
from io import open
from collections import OrderedDict

# Useful for very coarse version differentiation.
PYVERSION = sys.version_info


if PYVERSION >= (3, 0, 0):
    from configparser import ConfigParser, NoOptionError
    text_type = str
else:
    from ConfigParser import SafeConfigParser as ConfigParser, NoOptionError
    text_type = unicode

if PYVERSION >= (3, 2, 0):
    read_config = lambda parser, file: parser.read_file(file)
else:
    read_config = lambda parser, file: parser.readfp(file)


DEFAULT_ENCODING = 'UTF-8'


# Python 3.10 don't have strtobool anymore. So we move it here.
TRUE_VALUES = {"y", "yes", "t", "true", "on", "1"}
FALSE_VALUES = {"n", "no", "f", "false", "off", "0"}

def strtobool(value):
    if isinstance(value, bool):
        return value
    value = value.lower()

    if value in TRUE_VALUES:
        return True
    elif value in FALSE_VALUES:
        return False

    raise ValueError("Invalid truth value: " + value)


class UndefinedValueError(Exception):
    pass


class Undefined(object):
    """
    Class to represent undefined type.
    """
    pass


# Reference instance to represent undefined values
undefined = Undefined()


class Config(object):
    """
    Handle .env file format used by Foreman.
    """

    def __init__(self, repository):
        self.repository = repository

    def _cast_boolean(self, value):
        """
        Helper to convert config values to boolean as ConfigParser do.
        """
        value = str(value)
        return bool(value) if value == '' else bool(strtobool(value))

    @staticmethod
    def _cast_do_nothing(value):
        return value

    def get(self, option, default=undefined, cast=undefined):
        """
        Return the value for option or default if defined.
        """

        # We can't avoid __contains__ because value may be empty.
        if option in os.environ:
            value = os.environ[option]
        elif option in self.repository:
            value = self.repository[option]
        else:
            if isinstance(default, Undefined):
                raise UndefinedValueError('{} not found. Declare it as envvar or define a default value.'.format(option))

            value = default

        if isinstance(cast, Undefined):
            cast = self._cast_do_nothing
        elif cast is bool:
            cast = self._cast_boolean

        return cast(value)

    def __call__(self, *args, **kwargs):
        """
        Convenient shortcut to get.
        """
        return self.get(*args, **kwargs)


class RepositoryEmpty(object):
    def __init__(self, source='', encoding=DEFAULT_ENCODING):
        pass

    def __contains__(self, key):
        return False

    def __getitem__(self, key):
        return None


class RepositoryIni(RepositoryEmpty):
    """
    Retrieves option keys from .ini files.
    """
    SECTION = 'settings'

    def __init__(self, source, encoding=DEFAULT_ENCODING):
        self.parser = ConfigParser()
        with open(source, encoding=encoding) as file_:
            read_config(self.parser, file_)

    def __contains__(self, key):
        return (key in os.environ or
                self.parser.has_option(self.SECTION, key))

    def __getitem__(self, key):
        try:
            return self.parser.get(self.SECTION, key)
        except NoOptionError:
            raise KeyError(key)


class RepositoryEnv(RepositoryEmpty):
    """
    Retrieves option keys from .env files with fall back to os.environ.
    """
    def __init__(self, source, encoding=DEFAULT_ENCODING):
        self.data = {}

        with open(source, encoding=encoding) as file_:
            for line in file_:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                k, v = line.split('=', 1)
                k = k.strip()
                v = v.strip()
                if len(v) >= 2 and ((v[0] == "'" and v[-1] == "'") or (v[0] == '"' and v[-1] == '"')):
                    v = v[1:-1]
                self.data[k] = v

    def __contains__(self, key):
        return key in os.environ or key in self.data

    def __getitem__(self, key):
        return self.data[key]


class RepositorySecret(RepositoryEmpty):
    """
    Retrieves option keys from files,
    where title of file is a key, content of file is a value
    e.g. Docker swarm secrets
    """

    def __init__(self, source='/run/secrets/'):
        self.data = {}

        ls = os.listdir(source)
        for file in ls:
            with open(os.path.join(source, file), 'r') as f:
                self.data[file] = f.read()

    def __contains__(self, key):
        return key in os.environ or key in self.data

    def __getitem__(self, key):
        return self.data[key]


class AutoConfig(object):
    """
    Autodetects the config file and type.

    Parameters
    ----------
    search_path : str, optional
        Initial search path. If empty, the default search path is the
        caller's path.

    """
    SUPPORTED = OrderedDict([
        ('settings.ini', RepositoryIni),
        ('.env', RepositoryEnv),
    ])

    encoding = DEFAULT_ENCODING

    def __init__(self, search_path=None):
        self.search_path = search_path
        self.config = None

    def _find_file(self, path):
        # look for all files in the current path
        for configfile in self.SUPPORTED:
            filename = os.path.join(path, configfile)
            if os.path.isfile(filename):
                return filename

        # search the parent
        parent = os.path.dirname(path)
        if parent and os.path.normcase(parent) != os.path.normcase(os.path.abspath(os.sep)):
            return self._find_file(parent)

        # reached root without finding any files.
        return ''

    def _load(self, path):
        # Avoid unintended permission errors
        try:
            filename = self._find_file(os.path.abspath(path))
        except Exception:
            filename = ''
        Repository = self.SUPPORTED.get(os.path.basename(filename), RepositoryEmpty)

        self.config = Config(Repository(filename, encoding=self.encoding))

    def _caller_path(self):
        # MAGIC! Get the caller's module path.
        frame = sys._getframe()
        path = os.path.dirname(frame.f_back.f_back.f_code.co_filename)
        return path

    def __call__(self, *args, **kwargs):
        if not self.config:
            self._load(self.search_path or self._caller_path())

        return self.config(*args, **kwargs)


# A pré-instantiated AutoConfig to improve decouple's usability
# now just import config and start using with no configuration.
config = AutoConfig()

# Helpers

class Csv(object):
    """
    Produces a csv parser that return a list of transformed elements.
    """

    def __init__(self, cast=text_type, delimiter=',', strip=string.whitespace, post_process=list):
        """
        Parameters:
        cast -- callable that transforms the item just before it's added to the list.
        delimiter -- string of delimiters chars passed to shlex.
        strip -- string of non-relevant characters to be passed to str.strip after the split.
        post_process -- callable to post process all casted values. Default is `list`.
        """
        self.cast = cast
        self.delimiter = delimiter
        self.strip = strip
        self.post_process = post_process

    def __call__(self, value):
        """The actual transformation"""
        if value is None:
            return self.post_process()

        transform = lambda s: self.cast(s.strip(self.strip))

        splitter = shlex(value, posix=True)
        splitter.whitespace = self.delimiter
        splitter.whitespace_split = True

        return self.post_process(transform(s) for s in splitter)


class Choices(object):
    """
    Allows for cast and validation based on a list of choices.
    """

    def __init__(self, flat=None, cast=text_type, choices=None):
        """
        Parameters:
        flat -- a flat list of valid choices.
        cast -- callable that transforms value before validation.
        choices -- tuple of Django-like choices.
        """
        self.flat = flat or []
        self.cast = cast
        self.choices = choices or []

        self._valid_values = []
        self._valid_values.extend(self.flat)
        self._valid_values.extend([value for value, _ in self.choices])

    def __call__(self, value):
        transform = self.cast(value)
        if transform not in self._valid_values:
            raise ValueError((
                    'Value not in list: {!r}; valid values are {!r}'
                ).format(value, self._valid_values))
        else:
            return transform
