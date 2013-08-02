# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

def execute():
	webnotes.reload_doc("hr", "doctype", "hr_settings")
	webnotes.reload_doc("setup", "doctype", "global_defaults")
	
	hr = webnotes.bean("HR Settings", "HR Settings")
	hr.doc.emp_created_by = webnotes.conn.get_value("Global Defaults", "Global Defaults", "emp_created_by")
	
	if webnotes.conn.sql("""select name from `tabSalary Slip` where docstatus=1 limit 1"""):
		hr.doc.include_holidays_in_total_working_days = 1
	
	hr.save()
	
	webnotes.conn.sql("""delete from `tabSingles` where doctype = 'Global Defaults' 
		and field = 'emp_created_by'""")