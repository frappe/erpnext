from __future__ import unicode_literals

import frappe


def execute():
    global_search_settings = frappe.get_single("Global Search Settings")

    if "Purchase Order" in (
        dt.document_type for dt in global_search_settings.allowed_in_global_search
    ):
        return

    global_search_settings.append(
        "allowed_in_global_search", {"document_type": "Purchase Order"}
    )

    global_search_settings.save(ignore_permissions=True)
