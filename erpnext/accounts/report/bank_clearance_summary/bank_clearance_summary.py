# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.query_builder import Case
from frappe.query_builder.custom import ConstantColumn
from frappe.utils import getdate
from pypika import Order


def execute(filters=None):
	if not filters:
		filters = {}

	columns = get_columns()
	data = get_entries(filters)

	return columns, data


def get_columns():
	columns = [
		{
			"label": _("Payment Document Type"),
			"fieldname": "payment_document_type",
			"fieldtype": "Data",
			"width": 130,
		},
		{
			"label": _("Payment Entry"),
			"fieldname": "payment_entry",
			"fieldtype": "Dynamic Link",
			"options": "payment_document_type",
			"width": 140,
		},
		{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 120},
		{"label": _("Cheque/Reference No"), "fieldname": "cheque_no", "width": 120},
		{"label": _("Clearance Date"), "fieldname": "clearance_date", "fieldtype": "Date", "width": 120},
		{
			"label": _("Against Account"),
			"fieldname": "against",
			"fieldtype": "Link",
			"options": "Account",
			"width": 200,
		},
		{"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 120},
	]

	return columns


def get_entries(filters):
	entries = []

	# get entries from all the apps
	for method_name in frappe.get_hooks("get_entries_for_bank_clearance_summary"):
		entries += (
			frappe.get_attr(method_name)(
				filters,
			)
			or []
		)

	return sorted(
		entries,
		key=lambda k: getdate(k[2]),
	)


def get_entries_for_bank_clearance_summary(filters):
	entries = []

	je = frappe.qb.DocType("Journal Entry")
	jea = frappe.qb.DocType("Journal Entry Account")

	journal_entries = (
		frappe.qb.from_(jea)
		.inner_join(je)
		.on(jea.parent == je.name)
		.select(
			ConstantColumn("Journal Entry").as_("payment_document"),
			je.name.as_("payment_entry"),
			je.posting_date,
			je.cheque_no,
			je.clearance_date,
			jea.against_account,
			jea.debit_in_account_currency - jea.credit_in_account_currency,
		)
		.where(
			(jea.account == filters.account)
			& (je.docstatus == 1)
			& (je.posting_date >= filters.from_date)
			& (je.posting_date <= filters.to_date)
			& ((je.is_opening == "No") | (je.is_opening.isnull()))
		)
		.orderby(je.posting_date, order=Order.desc)
		.orderby(je.name, order=Order.desc)
	).run(as_list=True)

	pe = frappe.qb.DocType("Payment Entry")
	payment_entries = (
		frappe.qb.from_(pe)
		.select(
			ConstantColumn("Payment Entry").as_("payment_document"),
			pe.name.as_("payment_entry"),
			pe.posting_date,
			pe.reference_no.as_("cheque_no"),
			pe.clearance_date,
			pe.party.as_("against_account"),
			Case()
			.when(
				(pe.paid_from == filters.account),
				((pe.paid_amount * -1) - pe.total_taxes_and_charges),
			)
			.else_(pe.received_amount),
		)
		.where((pe.paid_from == filters.account) | (pe.paid_to == filters.account))
		.where(
			(pe.docstatus == 1)
			& (pe.posting_date >= filters.from_date)
			& (pe.posting_date <= filters.to_date)
		)
		.orderby(pe.posting_date, order=Order.desc)
		.orderby(pe.name, order=Order.desc)
	).run(as_list=True)

	pi = frappe.qb.DocType("Purchase Invoice")
	purchase_invoices = (
		frappe.qb.from_(pi)
		.select(
			ConstantColumn("Purchase Invoice").as_("payment_document"),
			pi.name.as_("payment_entry"),
			pi.posting_date,
			pi.bill_no.as_("cheque_no"),
			pi.clearance_date,
			pi.supplier.as_("against_account"),
			(pi.paid_amount * -1).as_("amount"),
		)
		.where(
			(pi.docstatus == 1)
			& (pi.is_paid == 1)
			& (pi.cash_bank_account == filters.account)
			& (pi.posting_date >= filters.from_date)
			& (pi.posting_date <= filters.to_date)
		)
		.orderby(pi.posting_date, order=Order.desc)
		.orderby(pi.name, order=Order.desc)
	).run(as_list=True)

	entries = journal_entries + payment_entries + purchase_invoices

	return entries
