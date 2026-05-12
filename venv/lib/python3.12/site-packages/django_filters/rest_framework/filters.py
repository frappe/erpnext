from django_filters import filters

from ..filters import *  # noqa
from ..widgets import BooleanWidget

__all__ = filters.__all__


class BooleanFilter(filters.BooleanFilter):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", BooleanWidget)

        super().__init__(*args, **kwargs)
