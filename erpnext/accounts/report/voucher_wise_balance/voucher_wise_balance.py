# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder.functions import Sum


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"label": _("Voucher Type"), "fieldname": "voucher_type", "width": 300},
		{
			"label": _("Voucher No"),
			"fieldname": "voucher_no",
			"fieldtype": "Dynamic Link",
			"options": "voucher_type",
			"width": 300,
		},
		{
			"fieldname": "debit",
			"label": _("Debit"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 300,
		},
		{
			"fieldname": "credit",
			"label": _("Credit"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 300,
		},
	]


def get_data(filters):
	gle = frappe.qb.DocType("GL Entry")
	query = (
		frappe.qb.from_(gle)
		.select(
			gle.voucher_type, gle.voucher_no, Sum(gle.debit).as_("debit"), Sum(gle.credit).as_("credit")
		)
		.where(gle.is_cancelled == 0)
		.groupby(gle.voucher_no)
	)
	query = apply_filters(query, filters, gle)
	gl_entries = query.run(as_dict=True)
	unmatched = [entry for entry in gl_entries if entry.debit != entry.credit]
	return unmatched


def apply_filters(query, filters, gle):
	if filters.get("company"):
		query = query.where(gle.company == filters.company)
	if filters.get("voucher_type"):
		query = query.where(gle.voucher_type == filters.voucher_type)
	if filters.get("from_date"):
		query = query.where(gle.posting_date >= filters.from_date)
	if filters.get("to_date"):
		query = query.where(gle.posting_date <= filters.to_date)
	return query
