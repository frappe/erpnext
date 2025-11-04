# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _, qb
from frappe.query_builder import Criterion
from frappe.query_builder.functions import Abs
from frappe.utils import flt, getdate

from erpnext.accounts.report.accounts_receivable.accounts_receivable import ReceivablePayableReport


def execute(filters=None):
	if not filters:
		filters = {}

	validate_filters(filters)

	columns = get_columns(filters)
	entries = get_entries(filters)
	invoice_details = get_invoice_posting_date_map(filters)

	data = []
	for d in entries:
		invoice = invoice_details.get(d.against_voucher_no) or frappe._dict()
		payment_amount = d.amount

		d.update({"range1": 0, "range2": 0, "range3": 0, "range4": 0, "outstanding": payment_amount})

		if d.against_voucher_no:
			ReceivablePayableReport(filters).get_ageing_data(invoice.posting_date, d)

		row = [
			d.voucher_type,
			d.voucher_no,
			d.party_type,
			d.party,
			d.posting_date,
			d.against_voucher_no,
			invoice.posting_date,
			invoice.due_date,
			d.amount,
			d.remarks,
			d.age,
			d.range1,
			d.range2,
			d.range3,
			d.range4,
		]

		if invoice.due_date:
			row.append((getdate(d.posting_date) - getdate(invoice.due_date)).days or 0)

		data.append(row)

	return columns, data


def validate_filters(filters):
	if (filters.get("payment_type") == _("Incoming") and filters.get("party_type") == "Supplier") or (
		filters.get("payment_type") == _("Outgoing") and filters.get("party_type") == "Customer"
	):
		frappe.throw(
			_("{0} payment entries can not be filtered by {1}").format(
				filters.payment_type, filters.party_type
			)
		)


def get_columns(filters):
	return [
		{
			"fieldname": "payment_document",
			"label": _("Payment Document Type"),
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"fieldname": "payment_entry",
			"label": _("Payment Document"),
			"fieldtype": "Dynamic Link",
			"options": "payment_document",
			"width": 160,
		},
		{"fieldname": "party_type", "label": _("Party Type"), "fieldtype": "Data", "width": 100},
		{
			"fieldname": "party",
			"label": _("Party"),
			"fieldtype": "Dynamic Link",
			"options": "party_type",
			"width": 160,
		},
		{"fieldname": "posting_date", "label": _("Posting Date"), "fieldtype": "Date", "width": 100},
		{
			"fieldname": "invoice",
			"label": _("Invoice"),
			"fieldtype": "Link",
			"options": "Purchase Invoice"
			if filters.get("payment_type") == _("Outgoing")
			else "Sales Invoice",
			"width": 160,
		},
		{
			"fieldname": "invoice_posting_date",
			"label": _("Invoice Posting Date"),
			"fieldtype": "Date",
			"width": 100,
		},
		{"fieldname": "due_date", "label": _("Payment Due Date"), "fieldtype": "Date", "width": 100},
		{"fieldname": "amount", "label": _("Amount"), "fieldtype": "Currency", "width": 140},
		{"fieldname": "remarks", "label": _("Remarks"), "fieldtype": "Data", "width": 200},
		{"fieldname": "age", "label": _("Age"), "fieldtype": "Int", "width": 50},
		{"fieldname": "range1", "label": _("0-30"), "fieldtype": "Currency", "width": 140},
		{"fieldname": "range2", "label": _("30-60"), "fieldtype": "Currency", "width": 140},
		{"fieldname": "range3", "label": _("60-90"), "fieldtype": "Currency", "width": 140},
		{"fieldname": "range4", "label": _("90 Above"), "fieldtype": "Currency", "width": 140},
		{
			"fieldname": "delay_in_payment",
			"label": _("Delay in payment (Days)"),
			"fieldtype": "Int",
			"width": 100,
		},
	]


def get_conditions(filters):
	ple = qb.DocType("Payment Ledger Entry")
	conditions = []

	conditions.append(ple.delinked.eq(0))
	if filters.payment_type == _("Outgoing"):
		conditions.append(ple.party_type.eq("Supplier"))
		conditions.append(ple.against_voucher_type.eq("Purchase Invoice"))
	else:
		conditions.append(ple.party_type.eq("Customer"))
		conditions.append(ple.against_voucher_type.eq("Sales Invoice"))

	if filters.party:
		conditions.append(ple.party.eq(filters.party))

	if filters.get("from_date"):
		conditions.append(ple.posting_date.gte(filters.get("from_date")))

	if filters.get("to_date"):
		conditions.append(ple.posting_date.lte(filters.get("to_date")))

	if filters.get("company"):
		conditions.append(ple.company.eq(filters.get("company")))

	return conditions


def get_entries(filters):
	ple = qb.DocType("Payment Ledger Entry")
	conditions = get_conditions(filters)

	query = (
		qb.from_(ple)
		.select(
			ple.voucher_type,
			ple.voucher_no,
			ple.party_type,
			ple.party,
			ple.posting_date,
			Abs(ple.amount).as_("amount"),
			ple.remarks,
			ple.against_voucher_no,
		)
		.where(Criterion.all(conditions))
	)
	res = query.run(as_dict=True)
	return res


def get_invoice_posting_date_map(filters):
	invoice_details = {}
	dt = (
		qb.DocType("Sales Invoice")
		if filters.get("payment_type") == _("Incoming")
		else qb.DocType("Purchase Invoice")
	)
	res = (
		qb.from_(dt)
		.select(dt.name, dt.posting_date, dt.due_date)
		.where((dt.docstatus.eq(1)) & (dt.company.eq(filters.get("company"))))
		.run(as_dict=1)
	)
	for t in res:
		invoice_details[t.name] = t

	return invoice_details
