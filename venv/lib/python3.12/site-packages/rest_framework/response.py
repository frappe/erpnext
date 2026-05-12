"""
The Response class in REST framework is similar to HTTPResponse, except that
it is initialized with unrendered data, instead of a pre-rendered string.

The appropriate renderer is called during Django's template response rendering.
"""
from http.client import responses

from django.template.response import SimpleTemplateResponse

from rest_framework.serializers import Serializer


class Response(SimpleTemplateResponse):
    """
    An HttpResponse that allows its data to be rendered into
    arbitrary media types.
    """

    def __init__(self, data=None, status=None,
                 template_name=None, headers=None,
                 exception=False, content_type=None):
        """
        Alters the init arguments slightly.
        For example, drop 'template_name', and instead use 'data'.

        Setting 'renderer' and 'media_type' will typically be deferred,
        For example being set automatically by the `APIView`.
        """
        super().__init__(None, status=status)

        if isinstance(data, Serializer):
            msg = (
                'You passed a Serializer instance as data, but '
                'probably meant to pass serialized `.data` or '
                '`.error`. representation.'
            )
            raise AssertionError(msg)

        self.data = data
        self.template_name = template_name
        self.exception = exception
        self.content_type = content_type

        if headers:
            for name, value in headers.items():
                self[name] = value

    @property
    def rendered_content(self):
        renderer = getattr(self, 'accepted_renderer', None)
        accepted_media_type = getattr(self, 'accepted_media_type', None)
        context = getattr(self, 'renderer_context', None)

        assert renderer, ".accepted_renderer not set on Response"
        assert accepted_media_type, ".accepted_media_type not set on Response"
        assert context is not None, ".renderer_context not set on Response"
        context['response'] = self

        media_type = renderer.media_type
        charset = renderer.charset
        content_type = self.content_type

        if content_type is None and charset is not None:
            content_type = "{}; charset={}".format(media_type, charset)
        elif content_type is None:
            content_type = media_type
        self['Content-Type'] = content_type

        ret = renderer.render(self.data, accepted_media_type, context)
        if isinstance(ret, str):
            assert charset, (
                'renderer returned unicode, and did not specify '
                'a charset value.'
            )
            return ret.encode(charset)

        if not ret:
            del self['Content-Type']

        return ret

    @property
    def status_text(self):
        """
        Returns reason text corresponding to our HTTP response status code.
        Provided for convenience.
        """
        return responses.get(self.status_code, '')

    def __getstate__(self):
        """
        Remove attributes from the response that shouldn't be cached.
        """
        state = super().__getstate__()
        for key in (
            'accepted_renderer', 'renderer_context', 'resolver_match',
            'client', 'request', 'json', 'wsgi_request'
        ):
            if key in state:
                del state[key]
        state['_closable_objects'] = []
        return state
