"""Cerbos authorization integration for ERPNext.

Replaces ERPNext's reliance on Frappe DocType row-level permissions with calls
to an external Cerbos PDP. The PDP is configured via site_config:

    {
        "cerbos_host": "localhost:3593",   # gRPC endpoint
        "cerbos_tls":  false,
        "cerbos_fail_closed": true,        # deny on PDP errors (default true)
    }
"""

from erpnext.cerbos_authz.hooks import (
    cerbos_has_permission,
    cerbos_permission_query_conditions,
    DOCTYPE_TO_RESOURCE,
)

__all__ = [
    "cerbos_has_permission",
    "cerbos_permission_query_conditions",
    "DOCTYPE_TO_RESOURCE",
]
