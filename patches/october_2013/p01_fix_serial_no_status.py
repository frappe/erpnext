# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

def execute():	
	serial_nos = webnotes.conn.sql("""select name from `tabSerial No` where status!='Not in Use' 
		and docstatus=0""")
	for sr in serial_nos:
		try:
			sr_bean = webnotes.bean("Serial No", sr[0])
			sr_bean.make_controller().via_stock_ledger = True
			sr_bean.run_method("validate")
			sr_bean.save()
			webnotes.conn.commit()
		except:
			pass
			
	webnotes.conn.sql("""update `tabSerial No` set warehouse='' where status in 
		('Delivered', 'Purchase Returned')""")