# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

from webnotes.utils import getdate, validate_email_add, cstr, cint
from webnotes.model.doc import make_autoname
from webnotes import msgprint, _


class DocType:
	def __init__(self,doc,doclist=[]):
		self.doc = doc
		self.doclist = doclist
		
	def autoname(self):
		naming_method = webnotes.conn.get_value("HR Settings", None, "emp_created_by")
		if not naming_method:
			webnotes.throw(_("Please setup Employee Naming System in Human Resource > HR Settings"))
		else:
			if naming_method=='Naming Series':
				self.doc.name = make_autoname(self.doc.naming_series + '.####')
			elif naming_method=='Employee Number':
				self.doc.name = self.doc.employee_number

		self.doc.employee = self.doc.name

	def validate(self):
		import utilities
		utilities.validate_status(self.doc.status, ["Active", "Left"])

		self.doc.employee = self.doc.name
		self.validate_date()
		self.validate_email()
		self.validate_status()
		self.validate_employee_leave_approver()
		self.update_dob_event()
		
	def on_update(self):
		if self.doc.user_id:
			self.update_user_default()
			self.update_profile()
				
	def update_user_default(self):
		webnotes.conn.set_default("employee", self.doc.name, self.doc.user_id)
		webnotes.conn.set_default("employee_name", self.doc.employee_name, self.doc.user_id)
		webnotes.conn.set_default("company", self.doc.company, self.doc.user_id)
		self.set_default_leave_approver()
	
	def set_default_leave_approver(self):
		employee_leave_approvers = self.doclist.get({"parentfield": "employee_leave_approvers"})

		if len(employee_leave_approvers):
			webnotes.conn.set_default("leave_approver", employee_leave_approvers[0].leave_approver,
				self.doc.user_id)
		
		elif self.doc.reports_to:
			from webnotes.profile import Profile
			reports_to_user = webnotes.conn.get_value("Employee", self.doc.reports_to, "user_id")
			if "Leave Approver" in Profile(reports_to_user).get_roles():
				webnotes.conn.set_default("leave_approver", reports_to_user, self.doc.user_id)

	def update_profile(self):
		# add employee role if missing
		if not "Employee" in webnotes.conn.sql_list("""select role from tabUserRole
				where parent=%s""", self.doc.user_id):
			from webnotes.profile import add_role
			add_role(self.doc.user_id, "Employee")
			
		profile_wrapper = webnotes.bean("Profile", self.doc.user_id)
		
		# copy details like Fullname, DOB and Image to Profile
		if self.doc.employee_name:
			employee_name = self.doc.employee_name.split(" ")
			if len(employee_name) >= 3:
				profile_wrapper.doc.last_name = " ".join(employee_name[2:])
				profile_wrapper.doc.middle_name = employee_name[1]
			elif len(employee_name) == 2:
				profile_wrapper.doc.last_name = employee_name[1]
			
			profile_wrapper.doc.first_name = employee_name[0]
				
		if self.doc.date_of_birth:
			profile_wrapper.doc.birth_date = self.doc.date_of_birth
		
		if self.doc.gender:
			profile_wrapper.doc.gender = self.doc.gender
			
		if self.doc.image:
			if not profile_wrapper.doc.user_image == self.doc.image:
				profile_wrapper.doc.user_image = self.doc.image
				try:
					webnotes.doc({
						"doctype": "File Data",
						"file_name": self.doc.image,
						"attached_to_doctype": "Profile",
						"attached_to_name": self.doc.user_id
					}).insert()
				except webnotes.DuplicateEntryError, e:
					# already exists
					pass
		profile_wrapper.ignore_permissions = True
		profile_wrapper.save()
		
	def validate_date(self):
		if self.doc.date_of_birth and self.doc.date_of_joining and getdate(self.doc.date_of_birth) >= getdate(self.doc.date_of_joining):
			msgprint('Date of Joining must be greater than Date of Birth')
			raise Exception

		elif self.doc.scheduled_confirmation_date and self.doc.date_of_joining and (getdate(self.doc.scheduled_confirmation_date) < getdate(self.doc.date_of_joining)):
			msgprint('Scheduled Confirmation Date must be greater than Date of Joining')
			raise Exception
		
		elif self.doc.final_confirmation_date and self.doc.date_of_joining and (getdate(self.doc.final_confirmation_date) < getdate(self.doc.date_of_joining)):
			msgprint('Final Confirmation Date must be greater than Date of Joining')
			raise Exception
		
		elif self.doc.date_of_retirement and self.doc.date_of_joining and (getdate(self.doc.date_of_retirement) <= getdate(self.doc.date_of_joining)):
			msgprint('Date Of Retirement must be greater than Date of Joining')
			raise Exception
		
		elif self.doc.relieving_date and self.doc.date_of_joining and (getdate(self.doc.relieving_date) <= getdate(self.doc.date_of_joining)):
			msgprint('Relieving Date must be greater than Date of Joining')
			raise Exception
		
		elif self.doc.contract_end_date and self.doc.date_of_joining and (getdate(self.doc.contract_end_date)<=getdate(self.doc.date_of_joining)):
			msgprint('Contract End Date must be greater than Date of Joining')
			raise Exception
	 
	def validate_email(self):
		if self.doc.company_email and not validate_email_add(self.doc.company_email):
			msgprint("Please enter valid Company Email")
			raise Exception
		if self.doc.personal_email and not validate_email_add(self.doc.personal_email):
			msgprint("Please enter valid Personal Email")
			raise Exception
				
	def validate_status(self):
		if self.doc.status == 'Left' and not self.doc.relieving_date:
			msgprint("Please enter relieving date.")
			raise Exception
			
	def validate_employee_leave_approver(self):
		from webnotes.profile import Profile
		from hr.doctype.leave_application.leave_application import InvalidLeaveApproverError
		
		for l in self.doclist.get({"parentfield": "employee_leave_approvers"}):
			if "Leave Approver" not in Profile(l.leave_approver).get_roles():
				msgprint(_("Invalid Leave Approver") + ": \"" + l.leave_approver + "\"",
					raise_exception=InvalidLeaveApproverError)

	def update_dob_event(self):
		if self.doc.status == "Active" and self.doc.date_of_birth \
			and not cint(webnotes.conn.get_value("HR Settings", None, "stop_birthday_reminders")):
			birthday_event = webnotes.conn.sql("""select name from `tabEvent` where repeat_on='Every Year' 
				and ref_type='Employee' and ref_name=%s""", self.doc.name)
			
			starts_on = self.doc.date_of_birth + " 00:00:00"
			ends_on = self.doc.date_of_birth + " 00:15:00"

			if birthday_event:
				event = webnotes.bean("Event", birthday_event[0][0])
				event.doc.starts_on = starts_on
				event.doc.ends_on = ends_on
				event.save()
			else:
				webnotes.bean({
					"doctype": "Event",
					"subject": _("Birthday") + ": " + self.doc.employee_name,
					"description": _("Happy Birthday!") + " " + self.doc.employee_name,
					"starts_on": starts_on,
					"ends_on": ends_on,
					"event_type": "Public",
					"all_day": 1,
					"send_reminder": 1,
					"repeat_this_event": 1,
					"repeat_on": "Every Year",
					"ref_type": "Employee",
					"ref_name": self.doc.name
				}).insert()
		else:
			webnotes.conn.sql("""delete from `tabEvent` where repeat_on='Every Year' and
				ref_type='Employee' and ref_name=%s""", self.doc.name)

@webnotes.whitelist()
def get_retirement_date(date_of_birth=None):
	import datetime
	ret = {}
	if date_of_birth:
		dt = getdate(date_of_birth) + datetime.timedelta(21915)
		ret = {'date_of_retirement': dt.strftime('%Y-%m-%d')}
	return ret
