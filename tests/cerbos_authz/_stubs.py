"""Lightweight stand-ins for ``frappe`` and the ``cerbos`` SDK.

Installed by each test module via ``install_stubs()`` BEFORE importing
``erpnext.cerbos_authz.*`` (because ``erpnext/__init__.py`` itself imports
``frappe`` at module load time).
"""

from __future__ import annotations

import sys
import types
from typing import Any, Dict, List, Optional


# --- frappe stub -------------------------------------------------------------


class _FakeDB:
    def __init__(self, owner: "FakeFrappe"):
        self._owner = owner

    def get_value(self, doctype, filters=None, fieldname=None, **kw):
        return self._owner.db_values.get((doctype, _hashable(filters), fieldname))

    def get_default(self, key, user=None):
        return self._owner.user_defaults.get((user, key))

    def escape(self, value):
        return f"'{value}'"


class _FakeDefaults:
    def __init__(self, owner: "FakeFrappe"):
        self._owner = owner

    def get_user_default(self, key, user=None):
        return self._owner.user_defaults.get((user, key))


class _FakeSession:
    def __init__(self):
        self.user = "Administrator"


class FakeFrappe(types.ModuleType):
    def __init__(self):
        super().__init__("frappe")
        self.db = _FakeDB(self)
        self.defaults = _FakeDefaults(self)
        self.session = _FakeSession()
        self.conf: Dict[str, Any] = {}
        self.user_roles: Dict[str, List[str]] = {}
        self.get_all_results: Dict[str, List[Dict[str, Any]]] = {}
        self.db_values: Dict[tuple, Any] = {}
        self.user_defaults: Dict[tuple, Any] = {}
        self.logged_errors: List[Dict[str, str]] = []

    def get_roles(self, user):
        return list(self.user_roles.get(user, []))

    def get_all(self, doctype, filters=None, fields=None, **kw):
        rows = list(self.get_all_results.get(doctype, []))
        if filters:
            rows = [r for r in rows if _matches(r, filters)]
        if fields:
            rows = [{f: r.get(f) for f in fields} for r in rows]
        return rows

    def log_error(self, title=None, message=None):
        self.logged_errors.append({"title": title or "", "message": message or ""})

    def _(self, s):
        return s


def _matches(row: Dict[str, Any], filters) -> bool:
    if isinstance(filters, dict):
        return all(row.get(k) == v for k, v in filters.items())
    if isinstance(filters, list):
        for f in filters:
            _, field, op, value = f
            if op == "in":
                if row.get(field) not in value:
                    return False
            elif row.get(field) != value:
                return False
        return True
    return True


def _hashable(x):
    if isinstance(x, dict):
        return tuple(sorted(x.items()))
    return x


# --- cerbos SDK stub ---------------------------------------------------------


class FakePrincipal:
    def __init__(self, id, roles, attr=None):
        self.id = id
        self.roles = list(roles)
        self.attr = dict(attr or {})

    def __repr__(self):
        return f"FakePrincipal({self.id!r}, {self.roles!r}, {self.attr!r})"


class FakeResource:
    def __init__(self, id, kind, attr=None):
        self.id = id
        self.kind = kind
        self.attr = dict(attr or {})

    def __repr__(self):
        return f"FakeResource({self.id!r}, {self.kind!r}, {self.attr!r})"


class FakeCerbosClient:
    def __init__(self, host=None, tls_verify=False, **kw):
        self.host = host
        self.tls_verify = tls_verify
        self.calls: List[tuple] = []
        self.next_decision: bool = True
        self.raise_on_call: Optional[Exception] = None

    def is_allowed(self, action, principal, resource):
        self.calls.append((action, principal, resource))
        if self.raise_on_call is not None:
            raise self.raise_on_call
        return self.next_decision


# --- module installation -----------------------------------------------------


def install_stubs() -> FakeFrappe:
    """Install fake ``frappe`` + ``cerbos.sdk.*`` modules in ``sys.modules``.

    Also installs a minimal ``erpnext`` package shim so ``import
    erpnext.cerbos_authz.*`` resolves without executing
    ``erpnext/__init__.py`` (which would pull in the full Frappe stack).

    Always replaces any existing entries — calling between tests gives each
    one a clean slate.
    """
    fake_frappe = _make_frappe_package()
    sys.modules["frappe"] = fake_frappe

    utils = types.ModuleType("frappe.utils")
    utils.__path__ = []
    user_mod = types.ModuleType("frappe.utils.user")

    def is_website_user(user=None):
        roles = fake_frappe.user_roles.get(user or fake_frappe.session.user, [])
        return any(r in ("Customer", "Supplier", "Guest") for r in roles)

    user_mod.is_website_user = is_website_user
    utils.user = user_mod
    sys.modules["frappe.utils"] = utils
    sys.modules["frappe.utils.user"] = user_mod
    fake_frappe.utils = utils

    # frappe.model.document.Document — referenced by erpnext/__init__.py if it
    # ever loads. We install it so the shim doesn't crash on accidental
    # re-import paths.
    model_pkg = types.ModuleType("frappe.model")
    model_pkg.__path__ = []
    document_mod = types.ModuleType("frappe.model.document")
    document_mod.Document = type("Document", (), {})
    model_pkg.document = document_mod
    fake_frappe.model = model_pkg
    sys.modules["frappe.model"] = model_pkg
    sys.modules["frappe.model.document"] = document_mod

    cerbos_pkg = types.ModuleType("cerbos")
    cerbos_pkg.__path__ = []
    sdk_pkg = types.ModuleType("cerbos.sdk")
    sdk_pkg.__path__ = []
    model_mod = types.ModuleType("cerbos.sdk.model")
    grpc_pkg = types.ModuleType("cerbos.sdk.grpc")
    grpc_pkg.__path__ = []
    grpc_client_mod = types.ModuleType("cerbos.sdk.grpc.client")

    model_mod.Principal = FakePrincipal
    model_mod.Resource = FakeResource
    grpc_client_mod.CerbosClient = FakeCerbosClient

    sdk_pkg.model = model_mod
    sdk_pkg.grpc = grpc_pkg
    grpc_pkg.client = grpc_client_mod
    cerbos_pkg.sdk = sdk_pkg

    sys.modules["cerbos"] = cerbos_pkg
    sys.modules["cerbos.sdk"] = sdk_pkg
    sys.modules["cerbos.sdk.model"] = model_mod
    sys.modules["cerbos.sdk.grpc"] = grpc_pkg
    sys.modules["cerbos.sdk.grpc.client"] = grpc_client_mod

    # Drop any cached erpnext.* and tests.cerbos_authz._stubs-driven imports so
    # the next ``import erpnext.cerbos_authz.X`` re-binds against the freshly
    # installed stubs.
    for mod in list(sys.modules):
        if mod.startswith("erpnext"):
            sys.modules.pop(mod, None)

    # Install a shim ``erpnext`` package whose __path__ points at the real
    # source dir, but whose __init__ does NOT execute. This lets us import
    # submodules without dragging in the full erpnext bootstrap.
    import os.path
    here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    erpnext_path = os.path.join(here, "erpnext")
    erpnext_pkg = types.ModuleType("erpnext")
    erpnext_pkg.__path__ = [erpnext_path]
    sys.modules["erpnext"] = erpnext_pkg

    return fake_frappe


def _make_frappe_package() -> FakeFrappe:
    """Build a fresh ``FakeFrappe`` configured as a Python package."""
    f = FakeFrappe()
    # Mark as a package so submodule imports resolve.
    f.__path__ = []  # type: ignore[attr-defined]
    return f
