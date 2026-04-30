"""Thread-safe Cerbos client singleton.

Wraps the official `cerbos` Python SDK. The client is lazily initialised on
first use and reused for the lifetime of the worker process.
"""

from __future__ import annotations

import threading
from typing import Optional

import frappe


_lock = threading.Lock()
_client = None


def get_client():
    """Return a cached Cerbos gRPC client, creating it on first call."""
    global _client
    if _client is not None:
        return _client

    with _lock:
        if _client is not None:
            return _client

        from cerbos.sdk.grpc.client import CerbosClient

        host = frappe.conf.get("cerbos_host", "localhost:3593")
        use_tls = bool(frappe.conf.get("cerbos_tls", False))

        _client = CerbosClient(host=host, tls_verify=use_tls)
        return _client


def fail_closed() -> bool:
    """When the PDP is unreachable, deny rather than allow.

    Defaults to True. Set ``cerbos_fail_closed`` to ``false`` in
    ``site_config.json`` to fail open during local development.
    """
    return bool(frappe.conf.get("cerbos_fail_closed", True))


def reset_client_for_testing() -> None:
    """Drop the cached client. Used by unit tests."""
    global _client
    with _lock:
        _client = None
