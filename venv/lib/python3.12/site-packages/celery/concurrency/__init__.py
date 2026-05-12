"""Pool implementation abstract factory, and alias definitions."""

# Import from kombu directly as it's used
# early in the import stage, where celery.utils loads
# too much (e.g., for eventlet patching)
from kombu.utils.imports import symbol_by_name

__all__ = ('get_implementation', 'get_available_pool_names',)

ALIASES = {
    'prefork': 'celery.concurrency.prefork:TaskPool',
    'eventlet': 'celery.concurrency.eventlet:TaskPool',
    'gevent': 'celery.concurrency.gevent:TaskPool',
    'solo': 'celery.concurrency.solo:TaskPool',
    'processes': 'celery.concurrency.prefork:TaskPool',  # XXX compat alias
}

try:
    import concurrent.futures  # noqa: F401
except ImportError:
    pass
else:
    ALIASES['threads'] = 'celery.concurrency.thread:TaskPool'


def get_implementation(cls):
    """Return pool implementation by name."""
    return symbol_by_name(cls, ALIASES)


def get_available_pool_names():
    """Return all available pool type names."""
    return tuple(ALIASES.keys())
