# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import nowdate, getdate

def execute(filters=None):
	if not filters: filters = {}
	from erpnext.accounts.utils import get_balance_on
	balance_as_per_system = get_balance_on(filters["account"])
	columns = get_columns()
	#~ columns += ["Mad",[],balance_as_per_system]
	data = get_entries(filters)
	#~ print "MAdness",data
	#~ data += ["mad",{_("Payment Entry"):[]},"","","",{_("Against Account"):filters["account"]},balance_as_per_system]
	data.insert(0, {})
	data.insert(0, {"payment_doc":_("Amount")+": "+str(balance_as_per_system)})
	data.insert(0, {"payment_doc":filters["account"]})
	data.insert(0,{})
	return columns, data

def get_columns():
	return [
		{
			"fieldname": "payment_doc",
			"label": _("Payment Document"),
			"fieldtype": "Data",
			"width": 200
		},
		{
			"fieldname": "payment_entry",
			"label": _("Payment Entry"),
			"fieldtype": "Dynamic Link",
			"options": "payment_document",
			"width": 150
		},
		{
			"fieldname": "posting_date",
			"label": _("Posting Date"),
			"fieldtype": "Date",
			"width": 110
		},
		{
			"fieldname": "reference_no",
			"label": _("Reference No"),
			"fieldtype": "Data",
			"width": 130
		},
		{
			"fieldname": "clearance_date",
			"label": _("Clearance Date"),
			"fieldtype": "Date",
			"width": 110
		},
		{
			"fieldname": "against_account",
			"label": _("Against Account"),
			"fieldtype": "Link",
			"options": "Account",
			"width": 200
		},
		{
			"fieldname": "amount",
			"label": _("Amount"),
			"fieldtype": "Currency",
			"options": "account_currency",
			"width": 120
		},

	]


def get_conditions(filters):
	conditions = ""

	if filters.get("from_date"): conditions += " and posting_date>=%(from_date)s"
	if filters.get("to_date"): conditions += " and posting_date<=%(to_date)s"

	return conditions

def get_entries(filters):
	conditions = get_conditions(filters)
	journal_entries =  frappe.db.sql("""select "Journal Entry", jv.name, jv.posting_date,
		jv.cheque_no, jv.clearance_date, jvd.against_account, (jvd.debit - jvd.credit)
		from `tabJournal Entry Account` jvd, `tabJournal Entry` jv
		where jvd.parent = jv.name and jv.docstatus=1 and jvd.account = %(account)s {0}
		order by posting_date DESC, jv.name DESC""".format(conditions), filters, as_list=1)

	payment_entries =  frappe.db.sql("""select "Payment Entry", name, posting_date,
		reference_no, clearance_date, party, if(paid_from=%(account)s, paid_amount, received_amount)
		from `tabPayment Entry`
		where docstatus=1 and (paid_from = %(account)s or paid_to = %(account)s) {0}
		order by posting_date DESC, name DESC""".format(conditions), filters, as_list=1)

	return sorted(journal_entries + payment_entries, key=lambda k: k[2] or getdate(nowdate()))
