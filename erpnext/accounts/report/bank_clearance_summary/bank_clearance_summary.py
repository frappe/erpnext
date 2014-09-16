# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, msgprint

def execute(filters=None):
	if not filters: filters = {}
	
	columns = get_columns()
	data = get_entries(filters)
	
	return columns, data
	
def get_columns():
	return [_("Journal Voucher") + ":Link/Journal Voucher:140", _("Account") + ":Link/Account:140", 
		_("Posting Date") + ":Date:100", _("Clearance Date") + ":Date:110", _("Against Account") + ":Link/Account:200", 
		_("Debit") + ":Currency:120", _("Credit") + ":Currency:120"
	]

def get_conditions(filters):
	conditions = ""
	if not filters.get("account"):
		msgprint(_("Please select Bank Account"), raise_exception=1)
	else:
		conditions += " and jvd.account = %(account)s"
		
	if filters.get("from_date"): conditions += " and jv.posting_date>=%(from_date)s"
	if filters.get("to_date"): conditions += " and jv.posting_date<=%(to_date)s"
	
	return conditions
	
def get_entries(filters):
	conditions = get_conditions(filters)
	entries =  frappe.db.sql("""select jv.name, jvd.account, jv.posting_date, 
		jv.clearance_date, jvd.against_account, jvd.debit, jvd.credit
		from `tabJournal Voucher Detail` jvd, `tabJournal Voucher` jv 
		where jvd.parent = jv.name and jv.docstatus=1 %s
		order by jv.name DESC""" % conditions, filters, as_list=1)
	return entries