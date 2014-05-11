# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

def execute():
	webnotes.reload_doc("core", "doctype", "event")
	webnotes.conn.sql("""delete from `tabEvent` where repeat_on='Every Year' and ref_type='Employee'""")
	for employee in webnotes.conn.sql_list("""select name from `tabEmployee` where status='Active' and 
		ifnull(date_of_birth, '')!=''"""):
			obj = webnotes.get_obj("Employee", employee)
			obj.update_dob_event()
		