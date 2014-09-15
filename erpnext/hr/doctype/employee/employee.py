# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import getdate, validate_email_add, cint
from frappe.model.naming import make_autoname
from frappe import throw, _, msgprint
import frappe.permissions
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc

class EmployeeUserDisabledError(frappe.ValidationError): pass

class Employee(Document):
	def onload(self):
		self.get("__onload").salary_structure_exists = frappe.db.get_value("Salary Structure",
			{"employee": self.name, "is_active": "Yes", "docstatus": ["!=", 2]})

	def autoname(self):
		naming_method = frappe.db.get_value("HR Settings", None, "emp_created_by")
		if not naming_method:
			throw(_("Please setup Employee Naming System in Human Resource > HR Settings"))
		else:
			if naming_method=='Naming Series':
				self.name = make_autoname(self.naming_series + '.####')
			elif naming_method=='Employee Number':
				self.name = self.employee_number

		self.employee = self.name

	def validate(self):
		from erpnext.utilities import validate_status
		validate_status(self.status, ["Active", "Left"])

		self.employee = self.name
		self.validate_date()
		self.validate_email()
		self.validate_status()
		self.validate_employee_leave_approver()

		if self.user_id:
			self.validate_for_enabled_user_id()
			self.validate_duplicate_user_id()

	def on_update(self):
		if self.user_id:
			self.update_user()
			self.update_user_permissions()

		self.update_dob_event()

	def update_user_permissions(self):
		frappe.permissions.add_user_permission("Employee", self.name, self.user_id)
		frappe.permissions.set_user_permission_if_allowed("Company", self.company, self.user_id)

	def update_user(self):
		# add employee role if missing
		user = frappe.get_doc("User", self.user_id)
		user.ignore_permissions = True

		if "Employee" not in user.get("user_roles"):
			user.add_roles("Employee")

		# copy details like Fullname, DOB and Image to User
		if self.employee_name and not (user.first_name and user.last_name):
			employee_name = self.employee_name.split(" ")
			if len(employee_name) >= 3:
				user.last_name = " ".join(employee_name[2:])
				user.middle_name = employee_name[1]
			elif len(employee_name) == 2:
				user.last_name = employee_name[1]

			user.first_name = employee_name[0]

		if self.date_of_birth:
			user.birth_date = self.date_of_birth

		if self.gender:
			user.gender = self.gender

		if self.image:
			if not user.user_image:
				user.user_image = self.image
				try:
					frappe.get_doc({
						"doctype": "File Data",
						"file_name": self.image,
						"attached_to_doctype": "User",
						"attached_to_name": self.user_id
					}).insert()
				except frappe.DuplicateEntryError:
					# already exists
					pass

		user.save()

	def validate_date(self):
		if self.date_of_birth and self.date_of_joining and getdate(self.date_of_birth) >= getdate(self.date_of_joining):
			throw(_("Date of Joining must be greater than Date of Birth"))

		elif self.date_of_retirement and self.date_of_joining and (getdate(self.date_of_retirement) <= getdate(self.date_of_joining)):
			throw(_("Date Of Retirement must be greater than Date of Joining"))

		elif self.relieving_date and self.date_of_joining and (getdate(self.relieving_date) <= getdate(self.date_of_joining)):
			throw(_("Relieving Date must be greater than Date of Joining"))

		elif self.contract_end_date and self.date_of_joining and (getdate(self.contract_end_date)<=getdate(self.date_of_joining)):
			throw(_("Contract End Date must be greater than Date of Joining"))

	def validate_email(self):
		if self.company_email and not validate_email_add(self.company_email):
			throw(_("Please enter valid Company Email"))
		if self.personal_email and not validate_email_add(self.personal_email):
			throw(_("Please enter valid Personal Email"))

	def validate_status(self):
		if self.status == 'Left' and not self.relieving_date:
			throw(_("Please enter relieving date."))

	def validate_for_enabled_user_id(self):
		if not self.status == 'Active':
			return
		enabled = frappe.db.sql("""select name from `tabUser` where
			name=%s and enabled=1""", self.user_id)
		if not enabled:
			throw(_("User {0} is disabled").format(self.user_id), EmployeeUserDisabledError)

	def validate_duplicate_user_id(self):
		employee = frappe.db.sql_list("""select name from `tabEmployee` where
			user_id=%s and status='Active' and name!=%s""", (self.user_id, self.name))
		if employee:
			throw(_("User {0} is already assigned to Employee {1}").format(self.user_id, employee[0]))

	def validate_employee_leave_approver(self):
		from erpnext.hr.doctype.leave_application.leave_application import InvalidLeaveApproverError

		for l in self.get("employee_leave_approvers")[:]:
			if "Leave Approver" not in frappe.get_roles(l.leave_approver):
				self.get("employee_leave_approvers").remove(l)
				msgprint(_("{0} is not a valid Leave Approver. Removing row #{1}.").format(l.leave_approver, l.idx))

	def update_dob_event(self):
		if self.status == "Active" and self.date_of_birth \
			and not cint(frappe.db.get_value("HR Settings", None, "stop_birthday_reminders")):
			birthday_event = frappe.db.sql("""select name from `tabEvent` where repeat_on='Every Year'
				and ref_type='Employee' and ref_name=%s""", self.name)

			starts_on = self.date_of_birth + " 00:00:00"
			ends_on = self.date_of_birth + " 00:15:00"

			if birthday_event:
				event = frappe.get_doc("Event", birthday_event[0][0])
				event.starts_on = starts_on
				event.ends_on = ends_on
				event.save()
			else:
				frappe.get_doc({
					"doctype": "Event",
					"subject": _("Birthday") + ": " + self.employee_name,
					"description": _("Happy Birthday!") + " " + self.employee_name,
					"starts_on": starts_on,
					"ends_on": ends_on,
					"event_type": "Public",
					"all_day": 1,
					"send_reminder": 1,
					"repeat_this_event": 1,
					"repeat_on": "Every Year",
					"ref_type": "Employee",
					"ref_name": self.name
				}).insert()
		else:
			frappe.db.sql("""delete from `tabEvent` where repeat_on='Every Year' and
				ref_type='Employee' and ref_name=%s""", self.name)

@frappe.whitelist()
def get_retirement_date(date_of_birth=None):
	import datetime
	ret = {}
	if date_of_birth:
		dt = getdate(date_of_birth) + datetime.timedelta(21915)
		ret = {'date_of_retirement': dt.strftime('%Y-%m-%d')}
	return ret

@frappe.whitelist()
def make_salary_structure(source_name, target=None):
	target = get_mapped_doc("Employee", source_name, {
		"Employee": {
			"doctype": "Salary Structure",
			"field_map": {
				"name": "employee"
			}
		}
	})
	target.make_earn_ded_table()
	return target

def validate_employee_role(doc, method):
	# called via User hook
	if "Employee" in [d.role for d in doc.get("user_roles")]:
		if not frappe.db.get_value("Employee", {"user_id": doc.name}):
			frappe.msgprint(_("Please set User ID field in an Employee record to set Employee Role"))
			doc.get("user_roles").remove(doc.get("user_roles", {"role": "Employee"})[0])

def update_user_permissions(doc, method):
	# called via User hook
	if "Employee" in [d.role for d in doc.get("user_roles")]:
		employee = frappe.get_doc("Employee", {"user_id": doc.name})
		employee.update_user_permissions()
