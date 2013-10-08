# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import flt

def execute():	
	serial_nos = webnotes.conn.sql("""select name, item_code, status from `tabSerial No` 
		where status!='Not in Use'""", as_dict=1)
	for sr in serial_nos:
		last_sle = webnotes.conn.sql("""select voucher_type, voucher_no, actual_qty 
			from `tabStock Ledger Entry` where serial_no like %s and item_code=%s
			order by name desc limit 1""", 
			("%%%s%%" % sr.name, sr.item_code), as_dict=1)

		if flt(last_sle[0].actual_qty) > 0:
			if last_sle[0].voucher_type == "Stock Entry" and webnotes.conn.get_value("Stock Entry", 
				last_sle[0].voucher_no, "purpose") == "Sales Return":
					status = "Sales Returned"
			else:
				status = "Available"
		else:
			if last_sle[0].voucher_type == "Stock Entry":
				purpose = webnotes.conn.get_value("Stock Entry", last_sle[0].voucher_no, "purpose")
				if purpose == "Purchase Return":
					status = "Purchase Returned"
				else:
					status = "Not Available"
			else:
				status = "Delivered"
		if sr.status != status:
			webnotes.conn.sql("""update `tabSerial No` set status=%s where name=%s""", 
				(status, sr.name))
			
	webnotes.conn.sql("""update `tabSerial No` set warehouse='' 
		where status in ('Delivered', 'Purchase Returned')""")
	
		
	