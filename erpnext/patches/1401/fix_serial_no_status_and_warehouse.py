# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes


def execute():	
	serial_nos = webnotes.conn.sql("""select name from `tabSerial No` where docstatus=0 
		and status in ('Available', 'Sales Returned') and ifnull(warehouse, '') = ''""")
	for sr in serial_nos:
		try:
			last_sle = webnotes.bean("Serial No", sr[0]).make_controller().get_last_sle()
			if last_sle.actual_qty > 0:
				webnotes.conn.set_value("Serial No", sr[0], "warehouse", last_sle.warehouse)
				
			webnotes.conn.commit()
		except:
			pass