# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

def execute():
	webnotes.reload_doc("support", "doctype", "maintenance_schedule_detail")
	webnotes.reload_doc("support", "doctype", "maintenance_schedule_item")
	
	webnotes.conn.sql("""update `tabMaintenance Schedule Detail` set sales_person=incharge_name""")
	webnotes.conn.sql("""update `tabMaintenance Schedule Item` set sales_person=incharge_name""")