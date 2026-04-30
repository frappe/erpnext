"""Build a Cerbos Principal from a Frappe user.

The principal mirrors the schema declared in
``cerbos/policies/_schemas/principal.json``: roles, default + allowed
companies, linked Employee/Customer/Supplier records, and approver lists.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

import frappe
from frappe.utils.user import is_website_user


def build_principal(user: Optional[str] = None):
    """Construct a `cerbos.sdk.model.Principal` for the given user.

    The result is per-request (not cached across users) but the underlying
    lookups against Frappe's DB are cheap because they're tiny indexed
    queries.
    """
    from cerbos.sdk.model import Principal

    user = user or frappe.session.user
    roles = frappe.get_roles(user)
    user_type = "Website User" if is_website_user(user) else "System User"

    attr = {
        "user_type": user_type,
        "company": _default_company(user) or "",
        "allowed_companies": _allowed_companies(user),
    }

    employee = _linked_employee(user)
    if employee:
        attr["employee"] = employee

    customers = _linked_party(user, "Customer")
    if customers:
        # Cerbos schema permits a single linked customer; pick the first.
        attr["customer"] = customers[0]

    suppliers = _linked_party(user, "Supplier")
    if suppliers:
        attr["supplier"] = suppliers[0]

    leave_for = _approver_for(user, "leave_approver")
    if leave_for:
        attr["leave_approver_for"] = leave_for

    expense_for = _approver_for(user, "expense_approver")
    if expense_for:
        attr["expense_approver_for"] = expense_for

    department = frappe.db.get_value("Employee", {"user_id": user}, "department")
    if department:
        attr["department"] = department

    territory = frappe.db.get_default("territory", user)
    if territory:
        attr["territory"] = territory

    return Principal(id=user, roles=roles, attr=attr)


def _default_company(user: str) -> Optional[str]:
    return frappe.defaults.get_user_default("company", user)


def _allowed_companies(user: str) -> list[str]:
    """Companies the user has User Permission rows for, plus their default.

    Frappe stores these in the `User Permission` doctype with
    ``allow == "Company"``. If a user has *no* User Permissions for Company,
    Frappe convention is unrestricted access — we represent that by adding
    every company to the list.
    """
    rows = frappe.get_all(
        "User Permission",
        filters={"user": user, "allow": "Company"},
        fields=["for_value"],
    )
    if rows:
        return [r["for_value"] for r in rows]
    # Unrestricted: return all companies.
    return [c["name"] for c in frappe.get_all("Company", fields=["name"])]


def _linked_employee(user: str) -> Optional[str]:
    return frappe.db.get_value("Employee", {"user_id": user}, "name")


def _linked_party(user: str, party_type: str) -> list[str]:
    """Return the list of `Customer`/`Supplier` records linked to this user
    via the `Portal User` child table."""
    if user in ("Administrator", "Guest"):
        return []
    return [
        row["parent"]
        for row in frappe.get_all(
            "Portal User",
            filters={"user": user, "parenttype": party_type},
            fields=["parent"],
        )
    ]


def _approver_for(user: str, fieldname: str) -> list[str]:
    """Employees for whom this user is the configured approver."""
    return [
        row["name"]
        for row in frappe.get_all(
            "Employee",
            filters={fieldname: user, "status": "Active"},
            fields=["name"],
        )
    ]
