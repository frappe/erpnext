# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import nowdate, getdate

def execute(filters=None):
	if not filters: filters = {}

	columns = get_columns()
	data = get_entries(filters)

	return columns, data

def qc(fn, label, w, ft="Data", opt=None):
	col = { "fieldname": fn, "label": label, "fieldtype": ft, "width": w }
	if opt is not None:
		col["options"] = opt
	return col

def get_columns():
	return [
		qc("payment_document", _("Payment DocType"),     130),
		qc("from_document",    _("From Document"),       110, "Dynamic Link", "from_doc_type"),
		qc("posting_date",     _("Posting Date"),        100, "Date"),
		qc("ref_no",           _("Cheque/Reference No"), 120),
		qc("clearance_date",   _("Clearance Date"),      100, "Date"),
		qc("against_account",  _("Against Account"),     170, "Link",         "Account"),
		qc("amount",           _("Amount"),              120, "Currency"),
		qc("from_doc_type",    _("From DocType"),        120),
		qc("payment_entry",    _("Payment Entry"),       110, "Dynamic Link", "payment_document")
	]

def get_conditions(filters):
	conditions = ""

	if filters.get("from_date"): conditions += " and posting_date>=%(from_date)s"
	if filters.get("to_date"): conditions += " and posting_date<=%(to_date)s"

	return conditions

def get_entries(filters):
	conditions = get_conditions(filters)
	# We have four payment document types that could contribute reconciled payments:
	# (1) Journal Entry Account
	query = """SELECT
			"Journal Entry Account" as payment_document, jvd.name as payment_entry, jv.posting_date, jv.cheque_no as ref_no,
			jvd.clearance_date, jvd.against_account, jvd.debit - jvd.credit as amount, "Journal Entry" as from_doc_type, jv.name as from_document
		FROM
			`tabJournal Entry Account` jvd, `tabJournal Entry` jv
		WHERE
			jvd.parent = jv.name and jv.docstatus=1 and jvd.account = %(account)s
	"""
	query += conditions
	query += 'ORDER BY jv.name DESC'

	jea_payments =  frappe.db.sql(query, filters, as_dict=1)

	# (2) Payment Entry
	query =  """SELECT
			"Payment Entry" as payment_document, name as payment_entry, posting_date, reference_no as ref_no, clearance_date, party as against_account,
			if(paid_from=%(account)s, paid_amount * -1, received_amount) as amount, "Payment Entry" as from_doc_type, name as from_document
		FROM 
			`tabPayment Entry`
		WHERE
			docstatus=1 and (paid_from = %(account)s or paid_to = %(account)s)
	"""
	query += conditions
	query += 'ORDER BY name DESC'

	pe_payments = frappe.db.sql(query, filters, as_dict=1)

	# (3) Sales Invoice Payment
	query = """SELECT
			"Sales Invoice Payment" as payment_document, sip.name as payment_entry, si.posting_date, si.remarks as ref_no, sip.clearance_date, customer_name as against_account,
			sip.amount, "Sales Invoice" as from_doc_type, si.name as from_document
		FROM
			`tabSales Invoice Payment` sip
		JOIN
			`tabSales Invoice` as si ON sip.parent = si.name
		WHERE
			si.docstatus = 1 and sip.account = %(account)s
	"""
	query += conditions
	query += 'ORDER BY si.name DESC'

	sip_payments = frappe.db.sql(query, filters, as_dict=1)

	# (4) Purchase Invoice documents with Cash/Bank Account
	query = """SELECT
			"Purchase Invoice" as payment_document, name as payment_entry, posting_date, bill_no as ref_no, clearance_date, supplier_name as against_account,
			paid_amount as amount, "Purchase Invoice" as from_doc_type, name as from_document
		FROM
			`tabPurchase Invoice`
		WHERE
			docstatus = 1 and cash_bank_account = %(account)s
	"""
	query += conditions
	query += 'ORDER BY name DESC'

	pi_payments = frappe.db.sql(query, filters, as_dict=1)

	return sorted(jea_payments + pe_payments + sip_payments + pi_payments,
		key=lambda k: k["posting_date"] or getdate(nowdate()))
