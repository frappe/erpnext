import functools
import inspect
from typing import Any, TypeVar
from collections.abc import Callable

import frappe
from frappe.model.document import Document
from frappe.utils.user import is_website_user

__version__ = "16.0.1-dev"

T = TypeVar("T")


def get_default_company(user: str | None = None) -> str | None:
    """Return the default company for the given user (or session user)."""
    from frappe.defaults import get_user_default_as_list

    user = user or frappe.session.user
    companies = get_user_default_as_list("company", user)
    return companies[0] if companies else frappe.db.get_single_value(
        "Global Defaults", "default_company"
    )


def get_default_currency() -> str | None:
    """Return the currency of the default company."""
    company = get_default_company()
    return frappe.get_cached_value("Company", company, "default_currency") if company else None


def get_default_cost_center(company: str | None) -> str | None:
    """Return the default cost center of the given company."""
    if not company:
        return None

    if not hasattr(frappe.flags, "company_cost_center"):
        frappe.flags.company_cost_center = {}

    if company not in frappe.flags.company_cost_center:
        frappe.flags.company_cost_center[company] = frappe.get_cached_value(
            "Company", company, "cost_center"
        )
    return frappe.flags.company_cost_center[company]


def get_company_currency(company: str) -> str | None:
    """Return the default currency for the given company."""
    if not hasattr(frappe.flags, "company_currency"):
        frappe.flags.company_currency = {}

    if company not in frappe.flags.company_currency:
        frappe.flags.company_currency[company] = frappe.db.get_value(
            "Company", company, "default_currency", cache=True
        )
    return frappe.flags.company_currency[company]


def set_perpetual_inventory(enable: int = 1, company: str | None = None) -> None:
    """Enable or disable perpetual inventory for a given company."""
    company = company or ("_Test Company" if getattr(frappe.flags, "in_test", False) else get_default_company())
    if not company:
        raise frappe.ValidationError(
            "Cannot set perpetual inventory: no company provided and no default company configured."
        )

    doc = frappe.get_doc("Company", company)
    doc.enable_perpetual_inventory = enable
    doc.save()

    # Keep request-local cache consistent
    if not hasattr(frappe.local, "enable_perpetual_inventory"):
        frappe.local.enable_perpetual_inventory = {}
    frappe.local.enable_perpetual_inventory[company] = enable or 0


def encode_company_abbr(name: str, company: str | None = None, abbr: str | None = None) -> str:
    """Return name encoded with the company abbreviation."""
    company_abbr = abbr or frappe.get_cached_value("Company", company, "abbr")
    parts = name.rsplit(" - ", 1)
    if parts[-1].lower() != company_abbr.lower():
        parts.append(company_abbr)
    return " - ".join(parts)


def is_perpetual_inventory_enabled(company: str | None = None) -> int:
    """Return whether perpetual inventory is enabled for the given company."""
    company = company or ("_Test Company" if getattr(frappe.flags, "in_test", False) else get_default_company())
    if not hasattr(frappe.local, "enable_perpetual_inventory"):
        frappe.local.enable_perpetual_inventory = {}

    if company not in frappe.local.enable_perpetual_inventory:
        frappe.local.enable_perpetual_inventory[company] = (
            frappe.get_cached_value("Company", company, "enable_perpetual_inventory") or 0
        )
    return frappe.local.enable_perpetual_inventory[company]


def get_default_finance_book(company: str | None = None) -> str | None:
    """Return the default finance book for the given company."""
    company = company or get_default_company()
    if not company:
        return None

    if not hasattr(frappe.local, "default_finance_book"):
        frappe.local.default_finance_book = {}

    if company not in frappe.local.default_finance_book:
        frappe.local.default_finance_book[company] = frappe.get_cached_value(
            "Company", company, "default_finance_book"
        )
    return frappe.local.default_finance_book[company]


def get_party_account_type(party_type: str) -> str:
    """Return the account type for the given party type."""
    if not hasattr(frappe.local, "party_account_types"):
        frappe.local.party_account_types = {}

    if party_type not in frappe.local.party_account_types:
        frappe.local.party_account_types[party_type] = frappe.db.get_value(
            "Party Type", party_type, "account_type"
        ) or ""
    return frappe.local.party_account_types[party_type]


def get_region(company: str | None = None) -> str:
    """Return the default country based on flags, company, or global settings."""
    company = company or getattr(frappe.local.flags, "company", None)
    if company:
        return frappe.get_cached_value("Company", company, "country")
    return frappe.flags.country or frappe.get_system_settings("country")


def allow_regional(fn: Callable) -> Callable:
    """Decorator to make a function regionally overridable."""
    @functools.wraps(fn)
    def caller(*args, **kwargs):
        overrides = frappe.get_hooks("regional_overrides", {}).get(get_region())
        function_path = f"{inspect.getmodule(fn).__name__}.{fn.__name__}"
        if not overrides or function_path not in overrides:
            return fn(*args, **kwargs)

        # Priority given to last installed app
        return frappe.get_attr(overrides[function_path][-1])(*args, **kwargs)

    return caller


def check_app_permission() -> bool:
    """Check whether the current session user has app permissions."""
    if frappe.session.user == "Administrator":
        return True
    return not is_website_user()


def normalize_ctx_input(expected_type: type[T]) -> Callable[..., Any]:
    """
    Decorator: Normalize the first argument (`ctx`) of the decorated function by:
    - Converting Document objects to dict
    - Parsing JSON strings
    - Casting the result to the specified type
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func, assigned=(a for a in functools.WRAPPER_ASSIGNMENTS if a != "__annotations__"))
        def wrapper(ctx: T | Document | dict | str, *args, **kwargs) -> Any:
            if isinstance(ctx, expected_type):
                pass
            elif isinstance(ctx, Document):
                ctx = expected_type(**ctx.as_dict())
            elif isinstance(ctx, dict):
                ctx = expected_type(**ctx)
            elif isinstance(ctx, str):
                ctx = expected_type(**frappe.parse_json(ctx))
            else:
                raise TypeError(
                    f"Unsupported ctx type: {type(ctx)!r}; expected {expected_type}, Document, dict, or JSON string"
                )
            return func(ctx, *args, **kwargs)

        # preserve annotations but exclude ctx
        wrapper.__annotations__.update({k: v for k, v in func.__annotations__.items() if k != "ctx"})
        return wrapper
    retur
