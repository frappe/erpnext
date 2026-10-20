# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint

from erpnext.accounts.shareholding.report_permissions import apply_report_filters, require_company


def execute(filters=None):
	filters = frappe._dict(filters or {})
	require_company(filters)
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{
			"fieldname": "shareholder",
			"label": _("Shareholder"),
			"fieldtype": "Link",
			"options": "Shareholder",
			"width": 160,
		},
		{"fieldname": "posting_date", "label": _("Posting Date"), "fieldtype": "Date", "width": 110},
		{"fieldname": "transaction_type", "label": _("Type"), "fieldtype": "Data", "width": 100},
		{
			"fieldname": "share_transaction",
			"label": _("Share Transaction"),
			"fieldtype": "Link",
			"options": "Share Transaction",
			"width": 140,
		},
		{
			"fieldname": "share_class",
			"label": _("Share Class"),
			"fieldtype": "Link",
			"options": "Share Class",
			"width": 130,
		},
		{"fieldname": "from_share_number", "label": _("From Share No."), "fieldtype": "Int", "width": 105},
		{"fieldname": "to_share_number", "label": _("To Share No."), "fieldtype": "Int", "width": 105},
		{"fieldname": "quantity_change", "label": _("Quantity Change"), "fieldtype": "Int", "width": 120},
		{
			"fieldname": "face_value_per_share",
			"label": _("Face Value"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 100,
		},
		{
			"fieldname": "treasury_cost_change",
			"label": _("Treasury Cost Change"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 145,
		},
		{
			"fieldname": "reversal_of",
			"label": _("Reversal Of"),
			"fieldtype": "Link",
			"options": "Share Ledger Entry",
			"width": 125,
		},
	]


def get_data(filters):
	entry = frappe.qb.DocType("Share Ledger Entry")
	folio = frappe.qb.DocType("Share Folio")
	fields = (
		"name",
		"source_doctype",
		"source_name",
		"posting_date",
		"posting_sequence",
		"company",
		"share_transaction",
		"transaction_type",
		"share_class",
		"share_folio",
		"from_share_number",
		"to_share_number",
		"quantity_change",
		"face_value_per_share",
		"treasury_cost_change",
		"currency",
		"is_reversal",
		"reversal_of",
	)
	query = (
		frappe.qb.from_(entry)
		.left_join(folio)
		.on(folio.name == entry.share_folio)
		.select(*(entry[field] for field in fields), folio.shareholder)
	)
	query = apply_report_filters(query, entry, folio, filters)
	if not cint(filters.get("include_reversals", 1)):
		query = query.where(entry.is_reversal == 0)
	return query.orderby(folio.shareholder, entry.posting_date, entry.posting_sequence, entry.creation).run(
		as_dict=True
	)
