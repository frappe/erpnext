# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _, qb
from frappe.query_builder import CustomFunction


def execute(filters=None):
	columns = get_columns()
	data = build_data(filters)
	return columns, data


def build_data(filters):
	vouchers = get_amounts_not_reflected_in_system_for_bank_reconciliation_statement(filters)
	data = []
	for x in vouchers:
		data.append(
			frappe._dict(
				payment_document="Payment Entry",
				payment_entry=x.name,
				debit=x.amount,
				credit=0,
				posting_date=x.posting_date,
				clearance_date=x.clearance_date,
			)
		)
	return data


def get_amounts_not_reflected_in_system_for_bank_reconciliation_statement(filters):
	je = qb.DocType("Journal Entry")
	jea = qb.DocType("Journal Entry Account")

	journals = (
		qb.from_(je)
		.inner_join(jea)
		.on(je.name == jea.parent)
		.select(
			je.name,
			jea.debit_in_account_currency,
			jea.credit_in_account_currency,
			je.posting_date,
			je.clearance_date,
		)
		.where(
			je.docstatus.eq(1)
			& jea.account.eq(filters.account)
			& je.posting_date.gt(filters.report_date)
			& je.clearance_date.lte(filters.report_date)
			& (je.is_opening.isnull() | je.is_opening.eq("No"))
		)
		.run(as_dict=1)
	)

	ifelse = CustomFunction("IF", ["condition", "then", "else"])
	pe = qb.DocType("Payment Entry")
	payments = (
		qb.from_(pe)
		.select(
			pe.name,
			ifelse(pe.paid_from.eq(filters.account), pe.paid_amount, pe.received_amount).as_("amount"),
			pe.posting_date,
			pe.clearance_date,
		)
		.where(
			pe.docstatus.eq(1)
			& (pe.paid_from.eq(filters.account) | pe.paid_to.eq(filters.account))
			& pe.posting_date.gt(filters.report_date)
			& pe.clearance_date.lte(filters.report_date)
		)
		.run(as_dict=1)
	)

	return journals + payments


def get_columns():
	return [
		{"fieldname": "posting_date", "label": _("Posting Date"), "fieldtype": "Date", "width": 90},
		{
			"fieldname": "payment_document",
			"label": _("Payment Document Type"),
			"fieldtype": "Data",
			"width": 220,
		},
		{
			"fieldname": "payment_entry",
			"label": _("Payment Document"),
			"fieldtype": "Dynamic Link",
			"options": "payment_document",
			"width": 220,
		},
		{
			"fieldname": "debit",
			"label": _("Debit"),
			"fieldtype": "Currency",
			"options": "account_currency",
			"width": 120,
		},
		{
			"fieldname": "credit",
			"label": _("Credit"),
			"fieldtype": "Currency",
			"options": "account_currency",
			"width": 120,
		},
		{"fieldname": "posting_date", "label": _("Posting Date"), "fieldtype": "Date", "width": 110},
		{"fieldname": "clearance_date", "label": _("Clearance Date"), "fieldtype": "Date", "width": 110},
	]
