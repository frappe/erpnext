"""ArangoDb result store backend."""

# pylint: disable=W1202,W0703

import json
import logging
from datetime import timedelta

from kombu.utils.objects import cached_property
from kombu.utils.url import _parse_url

from celery.exceptions import ImproperlyConfigured

from .base import KeyValueStoreBackend

try:
    from pyArango import connection as py_arango_connection
    from pyArango.theExceptions import AQLQueryError
except ImportError:
    py_arango_connection = AQLQueryError = None

__all__ = ('ArangoDbBackend',)


class ArangoDbBackend(KeyValueStoreBackend):
    """ArangoDb backend.

    Sample url
    "arangodb://username:password@host:port/database/collection"
    *arangodb_backend_settings* is where the settings are present
    (in the app.conf)
    Settings should contain the host, port, username, password, database name,
    collection name else the default will be chosen.
    Default database name and collection name is celery.

    Raises
    ------
    celery.exceptions.ImproperlyConfigured:
        if module :pypi:`pyArango` is not available.

    """

    host = '127.0.0.1'
    port = '8529'
    database = 'celery'
    collection = 'celery'
    username = None
    password = None
    # protocol is not supported in backend url (http is taken as default)
    http_protocol = 'http'
    verify = False

    # Use str as arangodb key not bytes
    key_t = str

    def __init__(self, url=None, *args, **kwargs):
        """Parse the url or load the settings from settings object."""
        super().__init__(*args, **kwargs)

        if py_arango_connection is None:
            raise ImproperlyConfigured(
                'You need to install the pyArango library to use the '
                'ArangoDb backend.',
            )

        self.url = url

        if url is None:
            host = port = database = collection = username = password = None
        else:
            (
                _schema, host, port, username, password,
                database_collection, _query
            ) = _parse_url(url)
            if database_collection is None:
                database = collection = None
            else:
                database, collection = database_collection.split('/')

        config = self.app.conf.get('arangodb_backend_settings', None)
        if config is not None:
            if not isinstance(config, dict):
                raise ImproperlyConfigured(
                    'ArangoDb backend settings should be grouped in a dict',
                )
        else:
            config = {}

        self.host = host or config.get('host', self.host)
        self.port = int(port or config.get('port', self.port))
        self.http_protocol = config.get('http_protocol', self.http_protocol)
        self.verify = config.get('verify', self.verify)
        self.database = database or config.get('database', self.database)
        self.collection = \
            collection or config.get('collection', self.collection)
        self.username = username or config.get('username', self.username)
        self.password = password or config.get('password', self.password)
        self.arangodb_url = "{http_protocol}://{host}:{port}".format(
            http_protocol=self.http_protocol, host=self.host, port=self.port
        )
        self._connection = None

    @property
    def connection(self):
        """Connect to the arangodb server."""
        if self._connection is None:
            self._connection = py_arango_connection.Connection(
                arangoURL=self.arangodb_url, username=self.username,
                password=self.password, verify=self.verify
            )
        return self._connection

    @property
    def db(self):
        """Database Object to the given database."""
        return self.connection[self.database]

    @cached_property
    def expires_delta(self):
        return timedelta(seconds=self.expires)

    def get(self, key):
        try:
            logging.debug(
                'RETURN DOCUMENT("{collection}/{key}").task'.format(
                    collection=self.collection, key=key
                )
            )
            query = self.db.AQLQuery(
                'RETURN DOCUMENT("{collection}/{key}").task'.format(
                    collection=self.collection, key=key
                )
            )
            result = query.response["result"][0]
            if result is None:
                return None
            return json.dumps(result)
        except AQLQueryError as aql_err:
            logging.error(aql_err)
            return None
        except Exception as err:
            logging.error(err)
            return None

    def set(self, key, value):
        """Insert a doc with value into task attribute and _key as key."""
        try:
            logging.debug(
                'INSERT {{ task: {task}, _key: "{key}" }} INTO {collection}'
                .format(
                    collection=self.collection, key=key, task=value
                )
            )
            self.db.AQLQuery(
                'INSERT {{ task: {task}, _key: "{key}" }} INTO {collection}'
                .format(
                    collection=self.collection, key=key, task=value
                )
            )
        except AQLQueryError as aql_err:
            logging.error(aql_err)
        except Exception as err:
            logging.error(err)

    def mget(self, keys):
        try:
            json_keys = json.dumps(keys)
            logging.debug(
                """
                FOR key in {keys}
                    RETURN DOCUMENT(CONCAT("{collection}/", key).task
                """.format(
                    collection=self.collection, keys=json_keys
                )
            )
            query = self.db.AQLQuery(
                """
                FOR key in {keys}
                    RETURN DOCUMENT(CONCAT("{collection}/", key).task
                """.format(
                    collection=self.collection, keys=json_keys
                )
            )
            results = []
            while True:
                results.extend(query.response['result'])
                query.nextBatch()
        except StopIteration:
            values = [
                result if result is None else json.dumps(result)
                for result in results
            ]
            return values
        except AQLQueryError as aql_err:
            logging.error(aql_err)
            return [None] * len(keys)
        except Exception as err:
            logging.error(err)
            return [None] * len(keys)

    def delete(self, key):
        try:
            logging.debug(
                'REMOVE {{ _key: "{key}" }} IN {collection}'.format(
                    key=key, collection=self.collection
                )
            )
            self.db.AQLQuery(
                'REMOVE {{ _key: "{key}" }} IN {collection}'.format(
                    key=key, collection=self.collection
                )
            )
        except AQLQueryError as aql_err:
            logging.error(aql_err)
        except Exception as err:
            logging.error(err)

    def cleanup(self):
        """Delete expired meta-data."""
        remove_before = (self.app.now() - self.expires_delta).isoformat()
        try:
            query = (
                'FOR item IN {collection} '
                'FILTER item.task.date_done < "{remove_before}" '
                'REMOVE item IN {collection}'
            ).format(collection=self.collection, remove_before=remove_before)
            logging.debug(query)
            self.db.AQLQuery(query)
        except AQLQueryError as aql_err:
            logging.error(aql_err)
        except Exception as err:
            logging.error(err)
