# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from erpnext.accounts.report.accounts_receivable.accounts_receivable import get_ageing_data
from frappe.utils import flt, getdate

def execute(filters=None):
	if not filters: filters = {}
	validate_filters(filters)

	columns = get_columns(filters)
	entries = get_entries(filters)
	invoice_details = get_invoice_posting_date_map(filters)
	against_date = ""

	data = []
	for d in entries:
		invoice = invoice_details.get(d.reference_name) or frappe._dict()
		if d.reference_type=="Purchase Invoice":
			payment_amount = flt(d.debit) or -1 * flt(d.credit)
		else:
			payment_amount = flt(d.credit) or -1 * flt(d.debit)

		row = [d.name, d.party_type, d.party, d.posting_date, d.reference_name, invoice.posting_date, 
			invoice.due_date, d.debit, d.credit, d.cheque_no, d.cheque_date, d.remark]

		if d.reference_name:
			row += get_ageing_data(30, 60, 90, d.posting_date, against_date, payment_amount)
		else:
			row += ["", "", "", "", ""]
		if invoice.due_date:
			row.append((getdate(d.posting_date) - getdate(invoice.due_date)).days or 0)
		
		data.append(row)

	return columns, data

def validate_filters(filters):
	if (filters.get("payment_type") == "Incoming" and filters.get("party_type") == "Supplier") or \
		(filters.get("payment_type") == "Outgoing" and filters.get("party_type") == "Customer"):
			frappe.throw(_("{0} payment entries can not be filtered by {1}")\
				.format(filters.payment_type, filters.party_type))

def get_columns(filters):
	return [
		_("Journal Entry") + ":Link/Journal Entry:140",
		_("Party Type") + "::100", 
		_("Party") + ":Dynamic Link/Party Type:140",
		_("Posting Date") + ":Date:100",
		_("Invoice") + (":Link/Purchase Invoice:130" if filters.get("payment_type") == "Outgoing" else ":Link/Sales Invoice:130"),
		_("Invoice Posting Date") + ":Date:130", 
		_("Payment Due Date") + ":Date:130", 
		_("Debit") + ":Currency:120", 
		_("Credit") + ":Currency:120",
		_("Reference No") + "::100", 
		_("Reference Date") + ":Date:100", 
		_("Remarks") + "::150", 
		_("Age") +":Int:40",
		"0-30:Currency:100", 
		"30-60:Currency:100", 
		"60-90:Currency:100", 
		_("90-Above") + ":Currency:100",
		_("Delay in payment (Days)") + "::150"
	]

def get_conditions(filters):
	conditions = []

	if not filters.get("party_type"):
		if filters.get("payment_type") == "Outgoing":
			filters["party_type"] = "Supplier"
		else:
			filters["party_type"] = "Customer"

	if filters.get("party_type"):
		conditions.append("jvd.party_type=%(party_type)s")

	if filters.get("party"):
		conditions.append("jvd.party=%(party)s")
		
	if filters.get("party_type"):
		conditions.append("jvd.reference_type=%(reference_type)s")
		if filters.get("party_type") == "Customer":
			filters["reference_type"] = "Sales Invoice"
		else:
			filters["reference_type"] = "Purchase Invoice"
		
	if filters.get("company"):
		conditions.append("jv.company=%(company)s")

	if filters.get("from_date"):
		conditions.append("jv.posting_date >= %(from_date)s")
	if filters.get("to_date"):
		conditions.append("jv.posting_date <= %(to_date)s")

	return "and {}".format(" and ".join(conditions)) if conditions else ""

def get_entries(filters):
	conditions = get_conditions(filters)
	entries =  frappe.db.sql("""select jv.name, jvd.party_type, jvd.party, jv.posting_date,
		jvd.reference_type, jvd.reference_name, jvd.debit, jvd.credit,
		jv.cheque_no, jv.cheque_date, jv.remark
		from `tabJournal Entry Account` jvd, `tabJournal Entry` jv
		where jvd.parent = jv.name and jv.docstatus=1 %s order by jv.name DESC""" %
		conditions, filters, as_dict=1)

	return entries

def get_invoice_posting_date_map(filters):
	invoice_details = {}
	dt = "Sales Invoice" if filters.get("payment_type") == "Incoming" else "Purchase Invoice"
	for t in frappe.db.sql("select name, posting_date, due_date from `tab{0}`".format(dt), as_dict=1):
		invoice_details[t.name] = t

	return invoice_details
