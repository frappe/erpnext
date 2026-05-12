"""
Python 'wcwidth' module.

https://github.com/jquast/wcwidth
"""

# re-export common and outermost functions & definitions, even a few private
# ones, some for convenience, others for legacy, only the items in __all__ are
# documented as public API

# local
from ._clip import clip
from .align import ljust, rjust, center
from ._width import width
from .bisearch import bisearch as _bisearch
from .grapheme import iter_graphemes, iter_graphemes_reverse, grapheme_boundary_before
from .textwrap import SequenceTextWrapper, wrap
from ._wcswidth import wcswidth
from .hyperlink import Hyperlink, HyperlinkParams
from .sgr_state import propagate_sgr
from .table_vs16 import VS16_NARROW_TO_WIDE
from .table_wide import WIDE_EASTASIAN
from .table_zero import ZERO_WIDTH
from .text_sizing import TextSizing, TextSizingParams
from .table_ambiguous import AMBIGUOUS_EASTASIAN
from .escape_sequences import iter_sequences, strip_sequences
from .unicode_versions import list_versions

# Pre-import the legacy submodule so that sys.modules['wcwidth.wcwidth'] is
# populated during package initialization.  This matches the 0.6.0 behavior
# where ``from .wcwidth import wcwidth`` would have already loaded the
# submodule.  Without this, a later ``import wcwidth.wcwidth`` triggers
# on-disk file discovery which rebinds wcwidth.wcwidth from the function to
# the module object.
#
# NOTE: this sort order is important for legacy import API compatibility before release 0.7.0
from . import wcwidth as _wcwidth_module  # isort:skip
from ._wcwidth import wcwidth, _wcmatch_version, _wcversion_value  # isort:skip


# The __all__ attribute defines the items exported from statement,
# 'from wcwidth import *', but also to say, "This is the public API".
__all__ = ('wcwidth', 'wcswidth', 'width', 'iter_sequences', 'iter_graphemes',
           'iter_graphemes_reverse', 'grapheme_boundary_before',
           'ljust', 'rjust', 'center', 'wrap', 'clip', 'strip_sequences',
           'list_versions', 'propagate_sgr', 'Hyperlink', 'HyperlinkParams',
           'TextSizing', 'TextSizingParams')

# Using 'hatchling', it does not seem to provide the pyproject.toml nicety, "dynamic = ['version']"
# like flit_core, maybe there is some better way but for now we have to duplicate it in both places
# Prefer the installed distribution version when available (helps test environments)
__version__ = '0.7.0'  # don't forget to also update pyproject.toml:version
