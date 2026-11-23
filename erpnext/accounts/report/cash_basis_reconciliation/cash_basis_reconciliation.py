# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Cash Basis Reconciliation (section 10): the bridge, the exceptions, the cumulative difference."""

from collections import defaultdict

import frappe
from frappe import _
from frappe.desk.reportview import build_match_conditions
from frappe.query_builder.functions import Sum
from frappe.utils import flt, getdate
from pypika.terms import Bracket, LiteralValue

from erpnext.accounts.cash_basis import CASH, get_cash_method_countries, is_cash_method_available
from erpnext.accounts.cash_basis.adjustments import (
	DEFERRAL,
	NON_CASH,
	RECOGNITION,
	REVALUATION,
	SCHEDULE_REMOVAL,
	UNAPPLIED,
)
from erpnext.accounts.cash_basis.calculation import filter_and_group
from erpnext.accounts.cash_basis.exceptions import get_reason_label
from erpnext.accounts.cash_basis.reports import (
	PERIOD_CLOSING_VOUCHER,
	get_report_result,
	resolve_accounting_method,
	set_report_end,
)
from erpnext.accounts.report.financial_statements import apply_additional_conditions
from erpnext.accounts.report.utils import has_gl_entry_restrictions
from erpnext.accounts.utils import get_currency_precision


def execute(filters=None):
	filters = frappe._dict(filters or {})
	validate_filters(filters)
	filters.accounting_method = CASH
	resolve_accounting_method(filters)
	set_report_end(filters, filters.to_date)
	result = get_report_result(filters, filters.to_date)
	accounts = get_account_details(filters.company)
	currency = frappe.get_cached_value("Company", filters.company, "default_currency")

	data = get_bridge(filters, result.rows, accounts, currency)
	data += get_exception_rows(result.exceptions, currency)
	data += get_cumulative_difference(filters, result.rows, accounts, currency)
	return get_columns(), data


def validate_filters(filters):
	labels = {"company": _("Company"), "from_date": _("From Date"), "to_date": _("To Date")}
	for fieldname, label in labels.items():
		if not filters.get(fieldname):
			frappe.throw(_("{0} is mandatory.").format(frappe.bold(label)), title=_("Missing Filter"))
	if getdate(filters.from_date) > getdate(filters.to_date):
		frappe.throw(_("From Date must be before To Date."), title=_("Invalid Dates"))
	frappe.has_permission("Company", "read", filters.company, throw=True)
	if not is_cash_method_available(filters.company):
		countries = get_cash_method_countries()
		message = (
			_("The cash basis is available only for a company in these countries: {0}.").format(
				", ".join(countries)
			)
			if countries
			else _("The cash basis is not available.")
		)
		frappe.throw(message, title=_("Accounting Method Not Available"))


def get_bridge(filters, rows, accounts, currency) -> list[dict]:
	"""Section 10.1: accrual net profit, each difference, cash net profit."""
	period_rows = filter_and_group(rows, filters.from_date, filters.to_date, "row", filters.company, filters)
	differences = defaultdict(float)
	for row in period_rows:
		category = get_bridge_category(row, accounts)
		if category:
			differences[category] += flt(row["credit"]) - flt(row["debit"])

	accrual_profit = get_accrual_net_profit(filters)
	lines = [section_row(_("Bridge"))]
	lines.append(amount_row(_("Accrual net profit"), accrual_profit, currency, indent=1))
	for category, label in get_bridge_labels().items():
		lines.append(amount_row(label, differences.get(category, 0.0), currency, indent=1))
	cash_profit = accrual_profit + sum(differences.values())
	lines.append(amount_row(_("Cash net profit"), cash_profit, currency, indent=1, bold=True))
	return lines


def get_bridge_labels() -> dict:
	return {
		"income": _("Effect of unpaid convertible income on profit"),
		"expense": _("Effect of unpaid convertible expense on profit"),
		"unapplied": _("Effect of unapplied cash on profit"),
		"non_cash": _("Effect of non-cash settlements on profit"),
		"revaluation": _("Effect of unrealised exchange differences on party accounts on profit"),
	}


def get_bridge_category(row, accounts) -> str | None:
	account = accounts.get(row["account"])
	if not account or account.report_type != "Profit and Loss":
		return None
	if row["voucher_type"] == PERIOD_CLOSING_VOUCHER:
		return None
	remark = row["remarks"]
	# The removal of a deferred schedule moves convertible income or expense, as a deferral does.
	if remark in (DEFERRAL, RECOGNITION, SCHEDULE_REMOVAL):
		return "income" if account.root_type == "Income" else "expense"
	return {UNAPPLIED: "unapplied", NON_CASH: "non_cash", REVALUATION: "revaluation"}.get(remark)


def get_accrual_net_profit(filters) -> float:
	"""Credit less debit of the P&L accounts in the period, as the Profit and Loss Statement reads them."""
	gle = frappe.qb.DocType("GL Entry")
	account = frappe.qb.DocType("Account")
	query = (
		frappe.qb.from_(gle)
		.join(account)
		.on(account.name == gle.account)
		.select(Sum(gle.credit - gle.debit))
		.where(
			(gle.company == filters.company)
			& (gle.is_cancelled == 0)
			& (gle.posting_date <= filters.to_date)
			& (account.report_type == "Profit and Loss")
		)
	)
	query = apply_additional_conditions("GL Entry", query, filters.from_date, True, filters)
	# The same user permissions as the Profit and Loss, so the bridge ends at its net profit.
	if match_conditions := build_match_conditions("GL Entry"):
		query = query.where(Bracket(LiteralValue(match_conditions)))
	result = query.run()
	return flt(result[0][0]) if result and result[0][0] else 0.0


def get_exception_rows(exceptions, currency) -> list[dict]:
	"""Section 10.2: the list of section 6.9, with a link to each voucher."""
	lines = [section_row(_("Exceptions"))]
	if has_gl_entry_restrictions():
		lines.append({"description": _("The list needs access to all GL rows of the company."), "indent": 1})
		return lines
	if not exceptions:
		lines.append({"description": _("No exception"), "indent": 1})
	for item in exceptions:
		lines.append(
			{
				"description": get_reason_label(item["reason"]),
				"voucher_type": item["voucher_type"],
				"voucher_no": item["voucher_no"],
				"posting_date": item["posting_date"],
				"party": item["party"],
				"amount": flt(item["amount"], get_precision()),
				"currency": currency,
				"indent": 1,
			}
		)
	return lines


def get_cumulative_difference(filters, rows, accounts, currency) -> list[dict]:
	"""Section 10.3: accrual retained earnings less cash retained earnings, at the to date."""
	all_rows = filter_and_group(rows, None, filters.to_date, "row", filters.company, filters)
	difference = sum(
		flt(row["debit"]) - flt(row["credit"])
		for row in all_rows
		if accounts.get(row["account"])
		and accounts[row["account"]].report_type == "Profit and Loss"
		and row["voucher_type"] != PERIOD_CLOSING_VOUCHER
	)
	lines = [section_row(_("Cumulative Difference"))]
	lines.append(
		amount_row(_("Accrual retained earnings less cash retained earnings"), difference, currency, indent=1)
	)
	labels = {
		"Sales Invoice": _("Opening sales invoices, not converted ({0})"),
		"Purchase Invoice": _("Opening purchase invoices, not converted ({0})"),
	}
	for doctype, (count, total) in get_opening_invoices(filters).items():
		if count:
			lines.append(amount_row(labels[doctype].format(count), total, currency, indent=1))
	return lines


def get_opening_invoices(filters) -> dict[str, tuple[int, float]]:
	result = {}
	for doctype in ("Sales Invoice", "Purchase Invoice"):
		rows = frappe.get_all(
			doctype,
			filters={
				"company": filters.company,
				"docstatus": 1,
				"is_opening": "Yes",
				"posting_date": ("<=", filters.to_date),
			},
			fields=["base_grand_total"],
		)
		result[doctype] = (len(rows), sum(flt(row.base_grand_total) for row in rows))
	return result


def get_account_details(company) -> dict:
	rows = frappe.get_all(
		"Account", filters={"company": company}, fields=["name", "report_type", "root_type"]
	)
	return {row.name: row for row in rows}


def section_row(label) -> dict:
	return {"description": label, "indent": 0, "bold": 1}


@frappe.request_cache
def get_precision() -> int:
	return get_currency_precision() or 2


def amount_row(label, amount, currency, indent=0, bold=False) -> dict:
	return {
		"description": label,
		"amount": flt(amount, get_precision()),
		"currency": currency,
		"indent": indent,
		"bold": int(bold),
	}


def get_columns() -> list[dict]:
	return [
		{"fieldname": "description", "label": _("Description"), "fieldtype": "Data", "width": 420},
		{
			"fieldname": "amount",
			"label": _("Amount"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 140,
		},
		{
			"fieldname": "voucher_type",
			"label": _("Voucher Type"),
			"fieldtype": "Link",
			"options": "DocType",
			"width": 140,
		},
		{
			"fieldname": "voucher_no",
			"label": _("Voucher"),
			"fieldtype": "Dynamic Link",
			"options": "voucher_type",
			"width": 180,
		},
		{"fieldname": "posting_date", "label": _("Posting Date"), "fieldtype": "Date", "width": 110},
		{"fieldname": "party", "label": _("Party"), "fieldtype": "Data", "width": 160},
		{
			"fieldname": "currency",
			"label": _("Currency"),
			"fieldtype": "Link",
			"options": "Currency",
			"hidden": 1,
		},
	]
