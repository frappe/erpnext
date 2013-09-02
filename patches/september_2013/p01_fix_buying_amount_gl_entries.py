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
			recreate_gl_entries("Delivery Note", dn)
	
	# fix sales invoice
	for si in webnotes.conn.sql_list("""select name from `tabSales Invoice` where docstatus=1
		and update_stock=1 and posting_date >= "2013-08-06" """):
			recreate_gl_entries("Sales Invoice", si)
	
def recreate_gl_entries(doctype, name):
	# remove gl entries
	webnotes.conn.sql("""delete from `tabGL Entry` where voucher_type=%s
		and voucher_no=%s""", (doctype, name))
	
	# calculate buying amount and make gl entries
	bean = webnotes.bean(doctype, name)
	bean.run_method("set_buying_amount")
	bean.run_method("make_gl_entries")