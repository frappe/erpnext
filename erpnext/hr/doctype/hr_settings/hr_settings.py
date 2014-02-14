# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import cint

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
		
	def validate(self):
		self.update_birthday_reminders()

		from erpnext.setup.doctype.naming_series.naming_series import set_by_naming_series
		set_by_naming_series("Employee", "employee_number", 
			self.doc.get("emp_created_by")=="Naming Series", hide_name_field=True)
			
	def update_birthday_reminders(self):
		original_stop_birthday_reminders = cint(frappe.conn.get_value("HR Settings", 
			None, "stop_birthday_reminders"))

		# reset birthday reminders
		if cint(self.doc.stop_birthday_reminders) != original_stop_birthday_reminders:
			frappe.conn.sql("""delete from `tabEvent` where repeat_on='Every Year' and ref_type='Employee'""")
		
			if not self.doc.stop_birthday_reminders:
				for employee in frappe.conn.sql_list("""select name from `tabEmployee` where status='Active' and 
					ifnull(date_of_birth, '')!=''"""):
					frappe.get_obj("Employee", employee).update_dob_event()
					
			frappe.msgprint(frappe._("Updated Birthday Reminders"))