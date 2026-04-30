"""Hook callbacks ERPNext registers with Frappe for Cerbos-managed doctypes.

Wired in ``erpnext/hooks.py`` via ``has_permission`` and
``permission_query_conditions``.
"""

from __future__ import annotations

from typing import Optional

import frappe
from frappe import _

from erpnext.cerbos_authz.client import fail_closed, get_client
from erpnext.cerbos_authz.principal import build_principal
from erpnext.cerbos_authz.resources import DOCTYPE_TO_RESOURCE, build_resource


# Mapping from Frappe ptype → Cerbos action name. They line up 1:1 today, but
# this indirection keeps room for future divergence (e.g. compound actions).
_PTYPE_TO_ACTION = {
    "read": "read",
    "write": "write",
    "create": "create",
    "delete": "delete",
    "submit": "submit",
    "cancel": "cancel",
    "amend": "amend",
    "print": "print",
    "email": "email",
    "export": "export",
    "import": "import",
    "share": "share",
    "report": "report",
}


def cerbos_has_permission(doc, ptype: str = "read", user: Optional[str] = None) -> bool:
    """``has_permission`` hook callback for any Cerbos-managed doctype.

    Returns:
        True if the PDP says ``EFFECT_ALLOW``, False otherwise. On PDP errors
        we honour ``cerbos_fail_closed`` (default: deny).
    """
    user = user or frappe.session.user

    # Administrator bypass keeps install/migration scripts working.
    if user == "Administrator":
        return True

    doctype = getattr(doc, "doctype", None) or (doc.get("doctype") if hasattr(doc, "get") else None)
    if not doctype or doctype not in DOCTYPE_TO_RESOURCE:
        # Not under Cerbos management — defer to the framework default by
        # returning None so Frappe applies its own logic.
        return None  # type: ignore[return-value]

    action = _PTYPE_TO_ACTION.get(ptype, ptype)

    try:
        principal = build_principal(user)
        resource = build_resource(doctype, doc)
        if resource is None:
            return None  # type: ignore[return-value]
        client = get_client()
        decision = client.is_allowed(action, principal, resource)
        return bool(decision)
    except Exception:
        frappe.log_error(
            title="Cerbos PDP error",
            message=f"doctype={doctype} ptype={ptype} user={user}",
        )
        if fail_closed():
            return False
        # Fall back to the framework default.
        return None  # type: ignore[return-value]


def cerbos_permission_query_conditions(user: Optional[str] = None) -> str:
    """``permission_query_conditions`` callback used to filter list views.

    For Customer/Supplier portal users we restrict the result set to documents
    linked to their party. Internal users currently see everything they have
    framework-level access to — per-row filtering for them is left to Frappe's
    User Permission system to keep query overhead low.
    """
    user = user or frappe.session.user
    if user in ("Administrator", "Guest"):
        return ""

    from erpnext.cerbos_authz.principal import _linked_party  # type: ignore

    parts = []
    customer_filters = _linked_party(user, "Customer")
    if customer_filters:
        joined = ", ".join(frappe.db.escape(c) for c in customer_filters)
        parts.append(f"`tab{{doctype}}`.`customer` in ({joined})")

    supplier_filters = _linked_party(user, "Supplier")
    if supplier_filters:
        joined = ", ".join(frappe.db.escape(s) for s in supplier_filters)
        parts.append(f"`tab{{doctype}}`.`supplier` in ({joined})")

    if not parts:
        return ""
    return " or ".join(parts)


# --- per-doctype thunks ------------------------------------------------------
# Frappe registers each ``has_permission`` entry against a single doctype.
# These thunks let us reference one callable per doctype in ``hooks.py`` while
# delegating to the shared implementation above.


def _make_thunk(doctype: str):
    def _thunk(doc, ptype: str = "read", user: Optional[str] = None) -> bool:
        if not getattr(doc, "doctype", None) and hasattr(doc, "get"):
            # Some callers pass a dict. Inject the doctype so the dispatch
            # works.
            doc["doctype"] = doctype
        return cerbos_has_permission(doc, ptype=ptype, user=user)

    _thunk.__name__ = f"has_permission_{doctype.lower().replace(' ', '_')}"
    return _thunk


HAS_PERMISSION_HOOKS = {
    doctype: _make_thunk(doctype) for doctype in DOCTYPE_TO_RESOURCE.keys()
}
