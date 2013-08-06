# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

import webnotes
from webnotes.utils import now_datetime

def execute():
	webnotes.reload_doc("stock", "doctype", "delivery_note_item")
	webnotes.reload_doc("accounts", "doctype", "sales_invoice_item")

	webnotes.conn.auto_commit_on_many_writes = True
	for company in webnotes.conn.sql("select name from `tabCompany`"):
		stock_ledger_entries = webnotes.conn.sql("""select item_code, voucher_type, voucher_no,
			voucher_detail_no, posting_date, posting_time, stock_value, 
			warehouse, actual_qty as qty from `tabStock Ledger Entry` 
			where ifnull(`is_cancelled`, "No") = "No" and company = %s
			order by item_code desc, warehouse desc, 
			posting_date desc, posting_time desc, name desc""", company[0], as_dict=True)
		
		dn_list = webnotes.conn.sql("""select name from `tabDelivery Note` 
			where docstatus < 2 and company = %s""", company[0])
		
		for dn in dn_list:
			dn = webnotes.get_obj("Delivery Note", dn[0], with_children = 1)
			dn.set_buying_amount(stock_ledger_entries)
		
		si_list = webnotes.conn.sql("""select name from `tabSales Invoice` 
			where docstatus < 2	and company = %s""", company[0])
		for si in si_list:
			si = webnotes.get_obj("Sales Invoice", si[0], with_children = 1)
			si.set_buying_amount(stock_ledger_entries)
		
	webnotes.conn.auto_commit_on_many_writes = False