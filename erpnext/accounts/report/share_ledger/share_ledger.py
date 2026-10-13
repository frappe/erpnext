# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint

from erpnext.accounts.shareholding.report_permissions import apply_report_filters


def execute(filters=None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{"fieldname": "source_doctype", "label": _("Source Type"), "fieldtype": "Data", "width": 155},
		{
			"fieldname": "source_name",
			"label": _("Source Document"),
			"fieldtype": "Dynamic Link",
			"options": "source_doctype",
			"width": 155,
		},
		{"fieldname": "posting_date", "label": _("Posting Date"), "fieldtype": "Date", "width": 110},
		{"fieldname": "posting_sequence", "label": _("Sequence"), "fieldtype": "Int", "width": 80},
		{
			"fieldname": "company",
			"label": _("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"width": 150,
		},
		{
			"fieldname": "share_transaction",
			"label": _("Share Transaction"),
			"fieldtype": "Link",
			"options": "Share Transaction",
			"width": 140,
		},
		{"fieldname": "transaction_type", "label": _("Type"), "fieldtype": "Data", "width": 100},
		{
			"fieldname": "share_class",
			"label": _("Share Class"),
			"fieldtype": "Link",
			"options": "Share Class",
			"width": 130,
		},
		{
			"fieldname": "share_folio",
			"label": _("Share Folio"),
			"fieldtype": "Link",
			"options": "Share Folio",
			"width": 130,
		},
		{
			"fieldname": "shareholder",
			"label": _("Shareholder"),
			"fieldtype": "Link",
			"options": "Shareholder",
			"width": 150,
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
			"fieldname": "currency",
			"label": _("Currency"),
			"fieldtype": "Link",
			"options": "Currency",
			"width": 85,
		},
		{"fieldname": "is_reversal", "label": _("Reversal"), "fieldtype": "Check", "width": 75},
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
	return query.orderby(entry.posting_date, entry.posting_sequence, entry.creation).run(as_dict=True)
