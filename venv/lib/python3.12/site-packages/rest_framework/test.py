# Note that we import as `DjangoRequestFactory` and `DjangoClient` in order
# to make it harder for the user to import the wrong thing without realizing.
import io
from importlib import import_module

import django
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.handlers.wsgi import WSGIHandler
from django.test import override_settings, testcases
from django.test.client import Client as DjangoClient
from django.test.client import ClientHandler
from django.test.client import RequestFactory as DjangoRequestFactory
from django.utils.encoding import force_bytes
from django.utils.http import urlencode

from rest_framework.compat import coreapi, requests
from rest_framework.settings import api_settings


def force_authenticate(request, user=None, token=None):
    request._force_auth_user = user
    request._force_auth_token = token


if requests is not None:
    class HeaderDict(requests.packages.urllib3._collections.HTTPHeaderDict):
        def get_all(self, key, default):
            return self.getheaders(key)

    class MockOriginalResponse:
        def __init__(self, headers):
            self.msg = HeaderDict(headers)
            self.closed = False

        def isclosed(self):
            return self.closed

        def close(self):
            self.closed = True

    class DjangoTestAdapter(requests.adapters.HTTPAdapter):
        """
        A transport adapter for `requests`, that makes requests via the
        Django WSGI app, rather than making actual HTTP requests over the network.
        """
        def __init__(self):
            self.app = WSGIHandler()
            self.factory = DjangoRequestFactory()

        def get_environ(self, request):
            """
            Given a `requests.PreparedRequest` instance, return a WSGI environ dict.
            """
            method = request.method
            url = request.url
            kwargs = {}

            # Set request content, if any exists.
            if request.body is not None:
                if hasattr(request.body, 'read'):
                    kwargs['data'] = request.body.read()
                else:
                    kwargs['data'] = request.body
            if 'content-type' in request.headers:
                kwargs['content_type'] = request.headers['content-type']

            # Set request headers.
            for key, value in request.headers.items():
                key = key.upper()
                if key in ('CONNECTION', 'CONTENT-LENGTH', 'CONTENT-TYPE'):
                    continue
                kwargs['HTTP_%s' % key.replace('-', '_')] = value

            return self.factory.generic(method, url, **kwargs).environ

        def send(self, request, *args, **kwargs):
            """
            Make an outgoing request to the Django WSGI application.
            """
            raw_kwargs = {}

            def start_response(wsgi_status, wsgi_headers, exc_info=None):
                status, _, reason = wsgi_status.partition(' ')
                raw_kwargs['status'] = int(status)
                raw_kwargs['reason'] = reason
                raw_kwargs['headers'] = wsgi_headers
                raw_kwargs['version'] = 11
                raw_kwargs['preload_content'] = False
                raw_kwargs['original_response'] = MockOriginalResponse(wsgi_headers)

            # Make the outgoing request via WSGI.
            environ = self.get_environ(request)
            wsgi_response = self.app(environ, start_response)

            # Build the underlying urllib3.HTTPResponse
            raw_kwargs['body'] = io.BytesIO(b''.join(wsgi_response))
            raw = requests.packages.urllib3.HTTPResponse(**raw_kwargs)

            # Build the requests.Response
            return self.build_response(request, raw)

        def close(self):
            pass

    class RequestsClient(requests.Session):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            adapter = DjangoTestAdapter()
            self.mount('http://', adapter)
            self.mount('https://', adapter)

        def request(self, method, url, *args, **kwargs):
            if not url.startswith('http'):
                raise ValueError('Missing "http:" or "https:". Use a fully qualified URL, eg "http://testserver%s"' % url)
            return super().request(method, url, *args, **kwargs)

else:
    def RequestsClient(*args, **kwargs):
        raise ImproperlyConfigured('requests must be installed in order to use RequestsClient.')


if coreapi is not None:
    class CoreAPIClient(coreapi.Client):
        def __init__(self, *args, **kwargs):
            self._session = RequestsClient()
            kwargs['transports'] = [coreapi.transports.HTTPTransport(session=self.session)]
            super().__init__(*args, **kwargs)

        @property
        def session(self):
            return self._session

else:
    def CoreAPIClient(*args, **kwargs):
        raise ImproperlyConfigured('coreapi must be installed in order to use CoreAPIClient.')


class APIRequestFactory(DjangoRequestFactory):
    renderer_classes_list = api_settings.TEST_REQUEST_RENDERER_CLASSES
    default_format = api_settings.TEST_REQUEST_DEFAULT_FORMAT

    def __init__(self, enforce_csrf_checks=False, **defaults):
        self.enforce_csrf_checks = enforce_csrf_checks
        self.renderer_classes = {}
        for cls in self.renderer_classes_list:
            self.renderer_classes[cls.format] = cls
        super().__init__(**defaults)

    def _encode_data(self, data, format=None, content_type=None):
        """
        Encode the data returning a two tuple of (bytes, content_type)
        """

        if data is None:
            return ('', content_type)

        assert format is None or content_type is None, (
            'You may not set both `format` and `content_type`.'
        )

        if content_type:
            # Content type specified explicitly, treat data as a raw bytestring
            ret = force_bytes(data, settings.DEFAULT_CHARSET)

        else:
            format = format or self.default_format

            assert format in self.renderer_classes, (
                "Invalid format '{}'. Available formats are {}. "
                "Set TEST_REQUEST_RENDERER_CLASSES to enable "
                "extra request formats.".format(
                    format,
                    ', '.join(["'" + fmt + "'" for fmt in self.renderer_classes])
                )
            )

            # Use format and render the data into a bytestring
            renderer = self.renderer_classes[format]()
            ret = renderer.render(data)

            # Determine the content-type header from the renderer
            content_type = renderer.media_type
            if renderer.charset:
                content_type = "{}; charset={}".format(
                    content_type, renderer.charset
                )

            # Coerce text to bytes if required.
            if isinstance(ret, str):
                ret = ret.encode(renderer.charset)

        return ret, content_type

    def get(self, path, data=None, **extra):
        r = {
            'QUERY_STRING': urlencode(data or {}, doseq=True),
        }
        if not data and '?' in path:
            # Fix to support old behavior where you have the arguments in the
            # url. See #1461.
            query_string = force_bytes(path.split('?')[1])
            query_string = query_string.decode('iso-8859-1')
            r['QUERY_STRING'] = query_string
        r.update(extra)
        return self.generic('GET', path, **r)

    def post(self, path, data=None, format=None, content_type=None, **extra):
        data, content_type = self._encode_data(data, format, content_type)
        return self.generic('POST', path, data, content_type, **extra)

    def put(self, path, data=None, format=None, content_type=None, **extra):
        data, content_type = self._encode_data(data, format, content_type)
        return self.generic('PUT', path, data, content_type, **extra)

    def patch(self, path, data=None, format=None, content_type=None, **extra):
        data, content_type = self._encode_data(data, format, content_type)
        return self.generic('PATCH', path, data, content_type, **extra)

    def delete(self, path, data=None, format=None, content_type=None, **extra):
        data, content_type = self._encode_data(data, format, content_type)
        return self.generic('DELETE', path, data, content_type, **extra)

    def options(self, path, data=None, format=None, content_type=None, **extra):
        data, content_type = self._encode_data(data, format, content_type)
        return self.generic('OPTIONS', path, data, content_type, **extra)

    def generic(self, method, path, data='',
                content_type='application/octet-stream', secure=False, **extra):
        # Include the CONTENT_TYPE, regardless of whether or not data is empty.
        if content_type is not None:
            extra['CONTENT_TYPE'] = str(content_type)

        return super().generic(
            method, path, data, content_type, secure, **extra)

    def request(self, **kwargs):
        request = super().request(**kwargs)
        request._dont_enforce_csrf_checks = not self.enforce_csrf_checks
        return request


class ForceAuthClientHandler(ClientHandler):
    """
    A patched version of ClientHandler that can enforce authentication
    on the outgoing requests.
    """

    def __init__(self, *args, **kwargs):
        self._force_user = None
        self._force_token = None
        super().__init__(*args, **kwargs)

    def get_response(self, request):
        # This is the simplest place we can hook into to patch the
        # request object.
        force_authenticate(request, self._force_user, self._force_token)
        return super().get_response(request)


class APIClient(APIRequestFactory, DjangoClient):
    def __init__(self, enforce_csrf_checks=False, **defaults):
        super().__init__(**defaults)
        self.handler = ForceAuthClientHandler(enforce_csrf_checks)
        self._credentials = {}

    def credentials(self, **kwargs):
        """
        Sets headers that will be used on every outgoing request.
        """
        self._credentials = kwargs

    def force_authenticate(self, user=None, token=None):
        """
        Forcibly authenticates outgoing requests with the given
        user and/or token.
        """
        self.handler._force_user = user
        self.handler._force_token = token
        if user is None and token is None:
            self.logout()  # Also clear any possible session info if required

    def request(self, **kwargs):
        # Ensure that any credentials set get added to every request.
        kwargs.update(self._credentials)
        return super().request(**kwargs)

    def get(self, path, data=None, follow=False, **extra):
        response = super().get(path, data=data, **extra)
        if follow:
            response = self._handle_redirects(response, data=data, **extra)
        return response

    def post(self, path, data=None, format=None, content_type=None,
             follow=False, **extra):
        response = super().post(
            path, data=data, format=format, content_type=content_type, **extra)
        if follow:
            response = self._handle_redirects(response, data=data, format=format, content_type=content_type, **extra)
        return response

    def put(self, path, data=None, format=None, content_type=None,
            follow=False, **extra):
        response = super().put(
            path, data=data, format=format, content_type=content_type, **extra)
        if follow:
            response = self._handle_redirects(response, data=data, format=format, content_type=content_type, **extra)
        return response

    def patch(self, path, data=None, format=None, content_type=None,
              follow=False, **extra):
        response = super().patch(
            path, data=data, format=format, content_type=content_type, **extra)
        if follow:
            response = self._handle_redirects(response, data=data, format=format, content_type=content_type, **extra)
        return response

    def delete(self, path, data=None, format=None, content_type=None,
               follow=False, **extra):
        response = super().delete(
            path, data=data, format=format, content_type=content_type, **extra)
        if follow:
            response = self._handle_redirects(response, data=data, format=format, content_type=content_type, **extra)
        return response

    def options(self, path, data=None, format=None, content_type=None,
                follow=False, **extra):
        response = super().options(
            path, data=data, format=format, content_type=content_type, **extra)
        if follow:
            response = self._handle_redirects(response, data=data, format=format, content_type=content_type, **extra)
        return response

    def logout(self):
        self._credentials = {}

        # Also clear any `force_authenticate`
        self.handler._force_user = None
        self.handler._force_token = None

        if self.session:
            super().logout()


class APITransactionTestCase(testcases.TransactionTestCase):
    client_class = APIClient


class APITestCase(testcases.TestCase):
    client_class = APIClient


class APISimpleTestCase(testcases.SimpleTestCase):
    client_class = APIClient


class APILiveServerTestCase(testcases.LiveServerTestCase):
    client_class = APIClient


def cleanup_url_patterns(cls):
    if hasattr(cls, '_module_urlpatterns'):
        cls._module.urlpatterns = cls._module_urlpatterns
    else:
        del cls._module.urlpatterns


class URLPatternsTestCase(testcases.SimpleTestCase):
    """
    Isolate URL patterns on a per-TestCase basis. For example,

    class ATestCase(URLPatternsTestCase):
        urlpatterns = [...]

        def test_something(self):
            ...

    class AnotherTestCase(URLPatternsTestCase):
        urlpatterns = [...]

        def test_something_else(self):
            ...
    """
    @classmethod
    def setUpClass(cls):
        # Get the module of the TestCase subclass
        cls._module = import_module(cls.__module__)
        cls._override = override_settings(ROOT_URLCONF=cls.__module__)

        if hasattr(cls._module, 'urlpatterns'):
            cls._module_urlpatterns = cls._module.urlpatterns

        cls._module.urlpatterns = cls.urlpatterns

        cls._override.enable()

        if django.VERSION > (4, 0):
            cls.addClassCleanup(cls._override.disable)
            cls.addClassCleanup(cleanup_url_patterns, cls)

        super().setUpClass()

    if django.VERSION < (4, 0):
        @classmethod
        def tearDownClass(cls):
            super().tearDownClass()
            cls._override.disable()

            if hasattr(cls, '_module_urlpatterns'):
                cls._module.urlpatterns = cls._module_urlpatterns
            else:
                del cls._module.urlpatterns
