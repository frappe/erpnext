# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

AMOUNT_FIELDS = ("invoiced_amount", "amount_eligible_for_commission", "total_commission")


def execute(filters: dict | None = None) -> tuple[list, list]:
	return get_columns(), get_data(frappe._dict(filters or {}))


def get_data(filters: frappe._dict) -> list[dict]:
	totals = {}
	for doctype in ("Sales Invoice", "POS Invoice"):
		if not frappe.has_permission(doctype, "read"):
			continue

		for row in get_partner_totals(doctype, filters):
			partner = totals.setdefault(row.sales_partner, dict.fromkeys(AMOUNT_FIELDS, 0.0))
			for field in AMOUNT_FIELDS:
				partner[field] += flt(row[field])

	return [get_row(partner, amounts) for partner, amounts in totals.items()]


def get_partner_totals(doctype: str, filters: frappe._dict) -> list[frappe._dict]:
	"""Commission per sales partner from the invoices the user is allowed to read."""
	return frappe.get_list(
		doctype,
		filters={"docstatus": 1, "total_commission": ["!=", 0]},
		fields=[
			"sales_partner",
			{"SUM": "base_net_total", "as": "invoiced_amount"},
			{"SUM": "amount_eligible_for_commission", "as": "amount_eligible_for_commission"},
			{"SUM": "total_commission", "as": "total_commission"},
		],
		group_by="sales_partner",
		order_by="sales_partner",
	)


def get_row(partner: str, amounts: dict) -> dict:
	eligible = amounts["amount_eligible_for_commission"]
	average_rate = amounts["total_commission"] * 100 / eligible if eligible else None
	return {"sales_partner": partner, **amounts, "average_commission_rate": average_rate}


def get_columns() -> list[dict]:
	return [
		{
			"label": _("Sales Partner"),
			"fieldname": "sales_partner",
			"fieldtype": "Link",
			"options": "Sales Partner",
			"width": 220,
		},
		{
			"label": _("Invoiced Amount (Excl. Tax)"),
			"fieldname": "invoiced_amount",
			"fieldtype": "Currency",
			"width": 220,
		},
		{
			"label": _("Amount Eligible for Commission"),
			"fieldname": "amount_eligible_for_commission",
			"fieldtype": "Currency",
			"width": 220,
		},
		{
			"label": _("Total Commission"),
			"fieldname": "total_commission",
			"fieldtype": "Currency",
			"width": 170,
		},
		{
			"label": _("Average Commission Rate"),
			"fieldname": "average_commission_rate",
			"fieldtype": "Percent",
			"width": 220,
		},
	]
