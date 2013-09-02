# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
import webnotes.defaults
from webnotes.utils import cint

def execute():
	if not cint(webnotes.defaults.get_global_default("auto_inventory_accounting")):
		return
	
	# fix delivery note
	for dn in webnotes.conn.sql_list("""select name from `tabDelivery Note` where docstatus=1
		and posting_date >= "2013-08-06" """):
			recreate_gl_entries("Delivery Note", dn, "delivery_note_details")
	
	# fix sales invoice
	for si in webnotes.conn.sql_list("""select name from `tabSales Invoice` where docstatus=1
		and update_stock=1 and posting_date >= "2013-08-06" """):
			recreate_gl_entries("Sales Invoice", si, "entries")
	
def recreate_gl_entries(doctype, name, parentfield):
	# remove gl entries
	webnotes.conn.sql("""delete from `tabGL Entry` where voucher_type=%s
		and voucher_no=%s""", (doctype, name))
	
	# calculate buying amount and make gl entries
	bean = webnotes.bean(doctype, name)
	bean.run_method("set_buying_amount")
	
	# update missing expense account and cost center
	for item in bean.doclist.get({"parentfield": parentfield}):
		if item.buying_amount and not (item.expense_account and item.cost_center):
			item_values = webnotes.conn.get_value("Item", item.item_code, 
				["purchase_account", "default_sales_cost_center"])
			company_values = webnotes.conn.get_value("Company", bean.doc.company, 
				["default_expense_account", "cost_center"])
			if not item.expense_account:
				item.expense_account = (item_values and item_values[0]) or (company_values and company_values[0])
			if not item.cost_center:
				item.cost_center = (item_values and item_values[1]) or (company_values and company_values[1])
			
			webnotes.conn.set_value(item.doctype, item.name, "expense_account", item.expense_account)
			webnotes.conn.set_value(item.doctype, item.name, "cost_center", item.cost_center)
		
	bean.run_method("make_gl_entries")