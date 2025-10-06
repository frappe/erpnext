# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _, qb
from frappe.query_builder import CustomFunction
from frappe.query_builder.custom import ConstantColumn


def execute(filters=None):
	columns = get_columns()
	data = build_data(filters)
	return columns, data


def build_payment_entry_dict(row: dict) -> dict:
	row_dict = frappe._dict()
	row_dict.update(
		{
			"payment_document": row.get("doctype"),
			"payment_entry": row.get("name"),
			"posting_date": row.get("posting_date"),
			"clearance_date": row.get("clearance_date"),
		}
	)
	if row.get("payment_type") == "Receive" and row.get("party_type") in ["Customer", "Supplier"]:
		row_dict.update(
			{
				"debit": row.get("amount"),
				"credit": 0,
			}
		)
	else:
		row_dict.update(
			{
				"debit": 0,
				"credit": row.get("amount"),
			}
		)
	return row_dict


def build_journal_entry_dict(row: dict) -> dict:
	row_dict = frappe._dict()
	row_dict.update(
		{
			"payment_document": row.get("doctype"),
			"payment_entry": row.get("name"),
			"posting_date": row.get("posting_date"),
			"clearance_date": row.get("clearance_date"),
			"debit": row.get("debit_in_account_currency"),
			"credit": row.get("credit_in_account_currency"),
		}
	)
	return row_dict


def build_data(filters):
	vouchers = get_amounts_not_reflected_in_system_for_bank_reconciliation_statement(filters)
	data = []
	for x in vouchers:
		if x.doctype == "Payment Entry":
			data.append(build_payment_entry_dict(x))
		elif x.doctype == "Journal Entry":
			data.append(build_journal_entry_dict(x))
	return data


def get_amounts_not_reflected_in_system_for_bank_reconciliation_statement(filters):
	je = qb.DocType("Journal Entry")
	jea = qb.DocType("Journal Entry Account")
	doctype_name = ConstantColumn("Journal Entry")

	journals = (
		qb.from_(je)
		.inner_join(jea)
		.on(je.name == jea.parent)
		.select(
			doctype_name.as_("doctype"),
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
	doctype_name = ConstantColumn("Payment Entry")
	payments = (
		qb.from_(pe)
		.select(
			doctype_name.as_("doctype"),
			pe.name,
			ifelse(pe.paid_from.eq(filters.account), pe.paid_amount, pe.received_amount).as_("amount"),
			pe.payment_type,
			pe.party_type,
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
