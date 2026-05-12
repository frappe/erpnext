from __future__ import annotations

from django.dispatch import Signal

# If any attached handler returns Truthy, CORS will be allowed for the request.
# This can be used to build custom logic into the request handling when the
# configuration doesn't work.
check_request_enabled = Signal()
