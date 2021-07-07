# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from erpnext.accounts.report.accounts_receivable.accounts_receivable import ReceivablePayableReport
from frappe.utils import getdate, flt


def execute(filters=None):
	if not filters:
		filters = {}

	validate_filters(filters)

	columns = get_columns(filters)
	entries = get_entries(filters)
	invoice_details = get_invoice_posting_date_map(filters)

	data = []
	for d in entries:
		invoice = invoice_details.get(d.against_voucher) or frappe._dict()

		if d.reference_type == "Purchase Invoice":
			payment_amount = flt(d.debit) or -1 * flt(d.credit)
		else:
			payment_amount = flt(d.credit) or -1 * flt(d.debit)

		d.update({
			"range1": 0,
			"range2": 0,
			"range3": 0,
			"range4": 0,
			"outstanding": payment_amount
		})

		if d.against_voucher:
			ReceivablePayableReport(filters).get_ageing_data(invoice.posting_date, d)

		row = [
			d.voucher_type, d.voucher_no, d.party_type, d.party, d.posting_date, d.against_voucher,
			invoice.posting_date, invoice.due_date, d.debit, d.credit, d.remarks, 
			d.age, d.range1, d.range2, d.range3, d.range4
		]

		if invoice.due_date:
			row.append((getdate(d.posting_date) - getdate(invoice.due_date)).days or 0)

		data.append(row)

	return columns, data

def validate_filters(filters):
	if (filters.get("payment_type") == _("Incoming") and filters.get("party_type") == "Supplier") or \
		(filters.get("payment_type") == _("Outgoing") and filters.get("party_type") == "Customer"):
			frappe.throw(_("{0} payment entries can not be filtered by {1}")\
				.format(filters.payment_type, filters.party_type))

def get_columns(filters):
	return [
		{
			"fieldname": "payment_document",
			"label": _("Payment Document Type"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "payment_entry",
			"label": _("Payment Document"),
			"fieldtype": "Dynamic Link",
			"options": "payment_document",
			"width": 160
		},
		{
			"fieldname": "party_type",
			"label": _("Party Type"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "party",
			"label": _("Party"),
			"fieldtype": "Dynamic Link",
			"options": "party_type",
			"width": 160
		},
		{
			"fieldname": "posting_date",
			"label": _("Posting Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "invoice",
			"label": _("Invoice"),
			"fieldtype": "Link",
			"options": "Purchase Invoice" if filters.get("payment_type") == _("Outgoing") else "Sales Invoice",
			"width": 160
		},
		{
			"fieldname": "invoice_posting_date",
			"label": _("Invoice Posting Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "due_date",
			"label": _("Payment Due Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "debit",
			"label": _("Debit"),
			"fieldtype": "Currency",
			"width": 140
		},
		{
			"fieldname": "credit",
			"label": _("Credit"),
			"fieldtype": "Currency",
			"width": 140
		},
		{
			"fieldname": "remarks",
			"label": _("Remarks"),
			"fieldtype": "Data",
			"width": 200
		},
		{
			"fieldname": "age",
			"label": _("Age"),
			"fieldtype": "Int",
			"width": 50
		},
		{
			"fieldname": "range1",
			"label": "0-30",
			"fieldtype": "Currency",
			"width": 140
		},
		{
			"fieldname": "range2",
			"label": "30-60",
			"fieldtype": "Currency",
			"width": 140
		},
		{
			"fieldname": "range3",
			"label": "60-90",
			"fieldtype": "Currency",
			"width": 140
		},
		{
			"fieldname": "range4",
			"label": _("90 Above"),
			"fieldtype": "Currency",
			"width": 140
		},
			{
			"fieldname": "delay_in_payment",
			"label": _("Delay in payment (Days)"),
			"fieldtype": "Int",
			"width": 100
		}
	]

def get_conditions(filters):
	conditions = []

	if not filters.party_type:
		if filters.payment_type == _("Outgoing"):
			filters.party_type = "Supplier"
		else:
			filters.party_type = "Customer"

	if filters.party_type:
		conditions.append("party_type=%(party_type)s")

	if filters.party:
		conditions.append("party=%(party)s")

	if filters.party_type:
		conditions.append("against_voucher_type=%(reference_type)s")
		filters["reference_type"] = "Sales Invoice" if filters.party_type=="Customer" else "Purchase Invoice"

	if filters.get("from_date"):
		conditions.append("posting_date >= %(from_date)s")

	if filters.get("to_date"):
		conditions.append("posting_date <= %(to_date)s")

	return "and " + " and ".join(conditions) if conditions else ""

def get_entries(filters):
	return frappe.db.sql("""select
		voucher_type, voucher_no, party_type, party, posting_date, debit, credit, remarks, against_voucher
		from `tabGL Entry`
		where company=%(company)s and voucher_type in ('Journal Entry', 'Payment Entry') {0}
	""".format(get_conditions(filters)), filters, as_dict=1)

def get_invoice_posting_date_map(filters):
	invoice_details = {}
	dt = "Sales Invoice" if filters.get("payment_type") == _("Incoming") else "Purchase Invoice"
	for t in frappe.db.sql("select name, posting_date, due_date from `tab{0}`".format(dt), as_dict=1):
		invoice_details[t.name] = t

	return invoice_details
