"""Mapping of ERPNext DocTypes to Cerbos resource kinds + attribute extractors.

Each entry tells the integration:

- ``kind``         — the resource kind in the Cerbos policy (snake_case).
- ``attrs``        — a callable taking a Frappe ``Document`` (or dict) and
                     returning the dict of attributes the resource policy
                     expects, mirroring the JSON schema in
                     ``cerbos/policies/_schemas/resources/<kind>.json``.

To add a new doctype to the Cerbos integration, add an entry here and ship a
matching policy + schema under ``cerbos/policies/``.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

import frappe


# --- attribute builders ------------------------------------------------------


def _common(doc) -> Dict[str, Any]:
    return {
        "owner": doc.get("owner") or "",
        "docstatus": int(doc.get("docstatus") or 0),
    }


def _company_country(company: Optional[str]) -> Optional[str]:
    if not company:
        return None
    return frappe.db.get_value("Company", company, "country")


def _sales_invoice_attrs(doc) -> Dict[str, Any]:
    company = doc.get("company")
    return {
        **_common(doc),
        "company": company or "",
        "customer": doc.get("customer") or "",
        "is_return": bool(doc.get("is_return")),
        "country": _company_country(company) or "",
    }


def _purchase_invoice_attrs(doc) -> Dict[str, Any]:
    company = doc.get("company")
    return {
        **_common(doc),
        "company": company or "",
        "supplier": doc.get("supplier") or "",
        "is_return": bool(doc.get("is_return")),
        "country": _company_country(company) or "",
    }


def _payment_entry_attrs(doc) -> Dict[str, Any]:
    company = doc.get("company")
    return {
        **_common(doc),
        "company": company or "",
        "payment_type": doc.get("payment_type") or "Receive",
        "country": _company_country(company) or "",
    }


def _journal_entry_attrs(doc) -> Dict[str, Any]:
    return {**_common(doc), "company": doc.get("company") or ""}


def _customer_attrs(doc) -> Dict[str, Any]:
    return {
        "owner": doc.get("owner") or "",
        "territory": doc.get("territory") or "",
        "customer_group": doc.get("customer_group") or "",
        "disabled": bool(doc.get("disabled")),
    }


def _supplier_attrs(doc) -> Dict[str, Any]:
    return {
        "owner": doc.get("owner") or "",
        "supplier_group": doc.get("supplier_group") or "",
        "disabled": bool(doc.get("disabled")),
    }


def _quotation_attrs(doc) -> Dict[str, Any]:
    return {
        **_common(doc),
        "company": doc.get("company") or "",
        "customer": doc.get("party_name") or doc.get("customer") or "",
        "territory": doc.get("territory") or "",
        "status": doc.get("status") or "Draft",
    }


def _sales_order_attrs(doc) -> Dict[str, Any]:
    return {
        **_common(doc),
        "company": doc.get("company") or "",
        "customer": doc.get("customer") or "",
        "status": doc.get("status") or "Draft",
    }


def _delivery_note_attrs(doc) -> Dict[str, Any]:
    return {
        **_common(doc),
        "company": doc.get("company") or "",
        "customer": doc.get("customer") or "",
        "is_return": bool(doc.get("is_return")),
    }


def _purchase_order_attrs(doc) -> Dict[str, Any]:
    return {
        **_common(doc),
        "company": doc.get("company") or "",
        "supplier": doc.get("supplier") or "",
        "status": doc.get("status") or "Draft",
    }


def _purchase_receipt_attrs(doc) -> Dict[str, Any]:
    return {
        **_common(doc),
        "company": doc.get("company") or "",
        "supplier": doc.get("supplier") or "",
        "is_return": bool(doc.get("is_return")),
    }


def _item_attrs(doc) -> Dict[str, Any]:
    return {
        "owner": doc.get("owner") or "",
        "item_group": doc.get("item_group") or "",
        "disabled": bool(doc.get("disabled")),
        "is_stock_item": bool(doc.get("is_stock_item")),
    }


def _stock_entry_attrs(doc) -> Dict[str, Any]:
    return {
        **_common(doc),
        "company": doc.get("company") or "",
        "purpose": doc.get("purpose") or "Material Issue",
    }


def _employee_attrs(doc) -> Dict[str, Any]:
    return {
        "company": doc.get("company") or "",
        "owner": doc.get("owner") or "",
        "user_id": doc.get("user_id") or "",
        "department": doc.get("department") or "",
        "status": doc.get("status") or "Active",
    }


def _leave_application_attrs(doc) -> Dict[str, Any]:
    return {
        **_common(doc),
        "company": doc.get("company") or "",
        "employee": doc.get("employee") or "",
        "status": doc.get("status") or "Open",
        "leave_approver": doc.get("leave_approver") or "",
    }


def _expense_claim_attrs(doc) -> Dict[str, Any]:
    return {
        **_common(doc),
        "company": doc.get("company") or "",
        "employee": doc.get("employee") or "",
        "approval_status": doc.get("approval_status") or "Draft",
        "expense_approver": doc.get("expense_approver") or "",
    }


def _timesheet_attrs(doc) -> Dict[str, Any]:
    return {
        **_common(doc),
        "company": doc.get("company") or "",
        "employee": doc.get("employee") or "",
        "customer": doc.get("customer") or "",
    }


def _project_attrs(doc) -> Dict[str, Any]:
    return {
        "company": doc.get("company") or "",
        "owner": doc.get("owner") or "",
        "customer": doc.get("customer") or "",
        "status": doc.get("status") or "Open",
    }


def _task_attrs(doc) -> Dict[str, Any]:
    assigned = []
    raw = doc.get("_assign")
    if raw:
        try:
            import json
            assigned = json.loads(raw)
        except (TypeError, ValueError):
            assigned = []
    return {
        "owner": doc.get("owner") or "",
        "project": doc.get("project") or "",
        "status": doc.get("status") or "Open",
        "assigned_to": assigned,
    }


# --- registry ----------------------------------------------------------------

DOCTYPE_TO_RESOURCE: Dict[str, Dict[str, Any]] = {
    # accounts
    "Sales Invoice": {"kind": "sales_invoice", "attrs": _sales_invoice_attrs},
    "Purchase Invoice": {"kind": "purchase_invoice", "attrs": _purchase_invoice_attrs},
    "Payment Entry": {"kind": "payment_entry", "attrs": _payment_entry_attrs},
    "Journal Entry": {"kind": "journal_entry", "attrs": _journal_entry_attrs},
    # selling
    "Customer": {"kind": "customer", "attrs": _customer_attrs},
    "Quotation": {"kind": "quotation", "attrs": _quotation_attrs},
    "Sales Order": {"kind": "sales_order", "attrs": _sales_order_attrs},
    "Delivery Note": {"kind": "delivery_note", "attrs": _delivery_note_attrs},
    # buying
    "Supplier": {"kind": "supplier", "attrs": _supplier_attrs},
    "Purchase Order": {"kind": "purchase_order", "attrs": _purchase_order_attrs},
    "Purchase Receipt": {"kind": "purchase_receipt", "attrs": _purchase_receipt_attrs},
    # stock
    "Item": {"kind": "item", "attrs": _item_attrs},
    "Stock Entry": {"kind": "stock_entry", "attrs": _stock_entry_attrs},
    # hr
    "Employee": {"kind": "employee", "attrs": _employee_attrs},
    "Leave Application": {"kind": "leave_application", "attrs": _leave_application_attrs},
    "Expense Claim": {"kind": "expense_claim", "attrs": _expense_claim_attrs},
    "Timesheet": {"kind": "timesheet", "attrs": _timesheet_attrs},
    # projects
    "Project": {"kind": "project", "attrs": _project_attrs},
    "Task": {"kind": "task", "attrs": _task_attrs},
}


def build_resource(doctype: str, doc):
    """Build a Cerbos `Resource` for the given Frappe document.

    Returns ``None`` if the doctype is not under Cerbos management; the caller
    should defer to the framework default in that case.
    """
    spec = DOCTYPE_TO_RESOURCE.get(doctype)
    if not spec:
        return None

    from cerbos.sdk.model import Resource

    name = doc.get("name") or doc.get("id") or ""
    attrs = spec["attrs"](doc)
    return Resource(id=name, kind=spec["kind"], attr=attrs)
