# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from erpnext.accounts.report.accounts_receivable.accounts_receivable import get_ageing_data
from frappe.utils import flt

def execute(filters=None):
	if not filters: filters = {}

	columns = get_columns()
	entries = get_entries(filters)
	invoice_posting_date_map = get_invoice_posting_date_map(filters)
	against_date = ""
	outstanding_amount = 0.0

	data = []
	for d in entries:
		if d.against_voucher:
			against_date = d.against_voucher and invoice_posting_date_map[d.against_voucher] or ""
			outstanding_amount = flt(d.debit) or -1 * flt(d.credit)
		else:
			against_date = d.against_invoice and invoice_posting_date_map[d.against_invoice] or ""
			outstanding_amount = flt(d.credit) or -1 * flt(d.debit)

		row = [d.name, d.account, d.posting_date, d.against_voucher or d.against_invoice,
			against_date, d.debit, d.credit, d.cheque_no, d.cheque_date, d.remark]

		if d.against_voucher or d.against_invoice:
			row += get_ageing_data(30, 60, 90, d.posting_date, against_date, outstanding_amount)
		else:
			row += ["", "", "", "", ""]

		data.append(row)

	return columns, data

def get_columns():
	return [_("Journal Entry") + ":Link/Journal Entry:140", _("Account") + ":Link/Account:140",
		_("Posting Date") + ":Date:100", _("Against Invoice") + ":Link/Purchase Invoice:130",
		_("Against Invoice Posting Date") + ":Date:130", _("Debit") + ":Currency:120", _("Credit") + ":Currency:120",
		_("Reference No") + "::100", _("Reference Date") + ":Date:100", _("Remarks") + "::150", _("Age") +":Int:40",
		"0-30:Currency:100", "30-60:Currency:100", "60-90:Currency:100", _("90-Above") + ":Currency:100"
	]

def get_conditions(filters):
	conditions = ""
	party = None

	if filters.get("account"):
		party = filters["account"]
	else:
		conditions += " and company = '%s'" % frappe.db.escape(filters["company"])

		account_type = "Receivable" if filters.get("payment_type") == "Incoming" else "Payable"

		conditions += """ and account in
			(select name from tabAccount
				where account_type = '{0}'
				and company='{1}')""".format(account_type, frappe.db.escape(filters["company"]))

	if party:
		conditions += " and jvd.party = '%s'" % frappe.db.escape(party)
	else:
		conditions += " and ifnull(jvd.party, '') != ''"

	if filters.get("from_date"):
		conditions += " and jv.posting_date >= '%s'" % filters["from_date"]
	if filters.get("to_date"):
		conditions += " and jv.posting_date <= '%s'" % filters["to_date"]

	return conditions

def get_entries(filters):
	conditions = get_conditions(filters)
	entries =  frappe.db.sql("""select jv.name, jvd.account, jv.posting_date,
		jvd.against_voucher, jvd.against_invoice, jvd.debit, jvd.credit,
		jv.cheque_no, jv.cheque_date, jv.remark
		from `tabJournal Entry Account` jvd, `tabJournal Entry` jv
		where jvd.parent = jv.name and jv.docstatus=1 %s order by jv.name DESC""" %
		conditions, as_dict=1, debug=1)

	return entries

def get_invoice_posting_date_map(filters):
	invoice_posting_date_map = {}
	if filters.get("payment_type") == "Incoming":
		for t in frappe.db.sql("""select name, posting_date from `tabSales Invoice`"""):
			invoice_posting_date_map[t[0]] = t[1]
	else:
		for t in frappe.db.sql("""select name, posting_date from `tabPurchase Invoice`"""):
			invoice_posting_date_map[t[0]] = t[1]

	return invoice_posting_date_map
