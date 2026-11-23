# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Accounting Method (Accrual or Cash) for the financial reports.

The ledger stays accrual. With the method "Cash", a report adds adjustment
rows in memory. This module holds the settings, the country policy, and the
public entry points.
"""

import frappe
from frappe import _

import erpnext

ACCRUAL = "Accrual"
CASH = "Cash"
ACCOUNTING_METHODS = (ACCRUAL, CASH)

# Phased rollout: the United States first. Other countries follow on need, when the feature is mature.
# This is not a statement about tax law.
CASH_METHOD_COUNTRIES = ("United States",)


def get_core_notice() -> str:
	return _(
		"The ledger stays on the accrual basis. Only the financial reports change. "
		"Statutory financial statements use the accrual basis in most countries. "
		"Confirm with your tax adviser that your business can use the cash method."
	)


def is_cash_method_available(company: str) -> bool:
	return is_cash_method_available_for_country(erpnext.get_region(company))


def is_cash_method_available_for_country(country: str | None) -> bool:
	return country in get_cash_method_countries()


def get_cash_method_countries() -> tuple[str, ...]:
	"""The countries in the rollout scope, read at call time, so that a change of the module
	attribute applies to every reader."""
	return CASH_METHOD_COUNTRIES


def get_accounting_method(filters: dict | None) -> str:
	"""Return the method for one report run: filter value, then Company default, then Accrual.

	For a company outside the rollout scope, the result is always Accrual.
	"""
	filters = filters or {}
	company = filters.get("company")
	method = filters.get("accounting_method")
	if not method and company:
		method = frappe.get_cached_value("Company", company, "accounting_method")

	method = method or ACCRUAL
	if method not in ACCOUNTING_METHODS:
		frappe.throw(
			_("Accounting Method {0} is not valid. Select Accrual or Cash.").format(frappe.bold(method)),
			title=_("Invalid Accounting Method"),
		)

	if method == CASH and not (company and is_cash_method_available(company)):
		return ACCRUAL

	return method


def is_cash_basis(filters: dict | None) -> bool:
	return get_accounting_method(filters) == CASH


@erpnext.allow_regional
def get_accounting_method_advisories(company: str) -> list[dict]:
	"""Messages for the Company form. Each: {"title", "message", "indicator"}."""
	return []


@frappe.whitelist()
def get_accounting_method_messages(company: str | None = None) -> dict:
	"""Return the core notice, and the regional advisories of a saved company, for the Company form."""
	messages = {"notice": get_core_notice(), "advisories": []}
	if not company:
		return messages

	frappe.has_permission("Company", "read", company, throw=True)
	messages["advisories"] = get_advisories_for_company(company)
	return messages


def get_advisories_for_company(company: str) -> list[dict]:
	# allow_regional finds the country from this flag, not from the arguments.
	previous_company = frappe.flags.company
	frappe.flags.company = company
	try:
		return get_accounting_method_advisories(company) or []
	finally:
		frappe.flags.company = previous_company


def get_cash_adjustments(*args, **kwargs) -> list[dict]:
	"""Public entry point of section 7.2. See calculation.get_cash_adjustments."""
	from erpnext.accounts.cash_basis.calculation import get_cash_adjustments

	return get_cash_adjustments(*args, **kwargs)


def get_exceptions(*args, **kwargs) -> list[dict]:
	"""Public entry point of section 7.2. See calculation.get_exceptions."""
	from erpnext.accounts.cash_basis.calculation import get_exceptions

	return get_exceptions(*args, **kwargs)
