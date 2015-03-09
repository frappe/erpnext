# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from erpnext.stock.stock_ledger import NegativeStockError

def execute():
	si_list = frappe.db.sql("""select distinct si.name 
		from `tabSales Invoice Item` si_item, `tabSales Invoice` si 
		where si.name = si_item.parent and si.modified > '2015-02-16' and si.docstatus=1 
		and ifnull(si_item.warehouse, '') = '' and ifnull(si.update_stock, 0) = 1 
		order by posting_date, posting_time""", as_dict=1)
		
	failed_list = []
	for si in si_list:
		try:
			si_doc = frappe.get_doc("Sales Invoice", si.name)		
			si_doc.docstatus = 2
			si_doc.on_cancel()

			si_doc.docstatus = 1
			si_doc.set_missing_item_details()
			si_doc.on_submit()
			frappe.db.commit()
		except:
			failed_list.append(si.name)
			frappe.local.stockledger_exceptions = None
			frappe.db.rollback()

	print "Failed to repost: ", failed_list
					
		
	