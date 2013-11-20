# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

def execute():
	stock_entries = webnotes.conn.sql("""select ste_item.serial_no, ste.name 
		from `tabStock Entry Detail` ste_item, `tabStock Entry` ste
		where ste.name = ste_item.parent
		and ifnull(ste_item.serial_no, '') != '' 
		and ste.purpose='Material Transfer'
		and ste.modified>='2013-08-14'
		order by ste.posting_date desc, ste.posting_time desc, ste.name desc""", as_dict=1)
		
	for d in stock_entries:
		serial_nos = d.serial_no.split("\n")
		for sr in serial_nos:
			serial_no = sr.strip()
			if serial_no and webnotes.conn.exists("Serial No", serial_no):
				serial_bean = webnotes.bean("Serial No", serial_no)
				if serial_bean.doc.status == "Not Available":
					latest_sle = webnotes.conn.sql("""select voucher_no from `tabStock Ledger Entry`
						where item_code=%s and warehouse=%s and serial_no like %s 
						order by name desc limit 1""", (serial_bean.doc.item_code, 
							serial_bean.doc.warehouse, "%%%s%%" % serial_no))
					
					if latest_sle and latest_sle[0][0] == d.name:
						serial_bean.doc.status = "Available"
						serial_bean.save()