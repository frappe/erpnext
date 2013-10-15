# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import webnotes

from webnotes.utils import cint

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
		
	def validate(self):
		self.original_stop_birthday_reminders = cint(webnotes.conn.get_value("HR Settings", 
			None, "stop_birthday_reminders"))
			
	def on_update(self):
		# reset birthday reminders
		if cint(self.doc.stop_birthday_reminders) != self.original_stop_birthday_reminders:
			webnotes.conn.sql("""delete from `tabEvent` where repeat_on='Every Year' and ref_type='Employee'""")
		
			if not self.doc.stop_birthday_reminders:
				for employee in webnotes.conn.sql_list("""select name from `tabEmployee` where status='Active' and 
					ifnull(date_of_birth, '')!=''"""):
					webnotes.get_obj("Employee", employee).update_dob_event()
					
			webnotes.msgprint(webnotes._("Updated Birthday Reminders"))