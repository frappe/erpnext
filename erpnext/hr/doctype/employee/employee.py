# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import getdate, validate_email_add, today, add_years, format_datetime
from frappe.model.naming import set_name_by_naming_series
from frappe import throw, _, scrub
from frappe.permissions import add_user_permission, remove_user_permission, \
	set_user_permission_if_allowed, has_permission
from frappe.model.document import Document
from erpnext.utilities.transaction_base import delete_events
from frappe.utils.nestedset import NestedSet

class EmployeeUserDisabledError(frappe.ValidationError): pass
class EmployeeLeftValidationError(frappe.ValidationError): pass

class Employee(NestedSet):
	nsm_parent_field = 'reports_to'

	def autoname(self):
		naming_method = frappe.db.get_value("HR Settings", None, "emp_created_by")
		if not naming_method:
			throw(_("Please setup Employee Naming System in Human Resource > HR Settings"))
		else:
			if naming_method == 'Naming Series':
				set_name_by_naming_series(self)
			elif naming_method == 'Employee Number':
				self.name = self.employee_number
			elif naming_method == 'Full Name':
				self.set_employee_name()
				self.name = self.employee_name

		self.employee = self.name

	def validate(self):
		from erpnext.controllers.status_updater import validate_status
		validate_status(self.status, ["Active", "Temporary Leave", "Left"])

		self.employee = self.name
		self.set_employee_name()
		self.validate_date()
		self.validate_email()
		self.validate_status()
		self.validate_reports_to()
		self.validate_preferred_email()
		if self.job_applicant:
			self.validate_onboarding_process()

		if self.user_id:
			self.validate_user_details()
		else:
			existing_user_id = frappe.db.get_value("Employee", self.name, "user_id")
			if existing_user_id:
				remove_user_permission(
					"Employee", self.name, existing_user_id)

	def set_employee_name(self):
		self.employee_name = ' '.join(filter(lambda x: x, [self.first_name, self.middle_name, self.last_name]))

	def validate_user_details(self):
		data = frappe.db.get_value('User',
			self.user_id, ['enabled', 'user_image'], as_dict=1)

		self.image = data.get("user_image")
		self.validate_for_enabled_user_id(data.get("enabled", 0))
		self.validate_duplicate_user_id()

	def update_nsm_model(self):
		frappe.utils.nestedset.update_nsm(self)

	def on_update(self):
		self.update_nsm_model()
		if self.user_id:
			self.update_user()
			self.update_user_permissions()

	def update_user_permissions(self):
		if not self.create_user_permission: return
		if not has_permission('User Permission', ptype='write'): return

		add_user_permission("Employee", self.name, self.user_id)
		set_user_permission_if_allowed("Company", self.company, self.user_id)

	def update_user(self):
		# add employee role if missing
		user = frappe.get_doc("User", self.user_id)
		user.flags.ignore_permissions = True

		if "Employee" not in user.get("roles"):
			user.append_roles("Employee")

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
						"doctype": "File",
						"file_name": self.image,
						"attached_to_doctype": "User",
						"attached_to_name": self.user_id
					}).insert()
				except frappe.DuplicateEntryError:
					# already exists
					pass

		user.save()

	def validate_date(self):
		if self.date_of_birth and getdate(self.date_of_birth) > getdate(today()):
			throw(_("Date of Birth cannot be greater than today."))

		if self.date_of_birth and self.date_of_joining and getdate(self.date_of_birth) >= getdate(self.date_of_joining):
			throw(_("Date of Joining must be greater than Date of Birth"))

		elif self.date_of_retirement and self.date_of_joining and (getdate(self.date_of_retirement) <= getdate(self.date_of_joining)):
			throw(_("Date Of Retirement must be greater than Date of Joining"))

		elif self.relieving_date and self.date_of_joining and (getdate(self.relieving_date) <= getdate(self.date_of_joining)):
			throw(_("Relieving Date must be greater than Date of Joining"))

		elif self.contract_end_date and self.date_of_joining and (getdate(self.contract_end_date) <= getdate(self.date_of_joining)):
			throw(_("Contract End Date must be greater than Date of Joining"))

	def validate_email(self):
		if self.company_email:
			validate_email_add(self.company_email, True)
		if self.personal_email:
			validate_email_add(self.personal_email, True)

	def validate_status(self):
		if self.status == 'Left':
			reports_to = frappe.db.sql("""select name,reports_to from `tabEmployee` where
				reports_to=%s""", (self.name), as_dict=True)
			if reports_to:
				employee_names = []
				for row in reports_to:
					employee_names.append(row.name)
				link_to_employees = [frappe.utils.get_link_to_form('Employee', employee_name) for employee_name in employee_names]
				throw(_("Employee status cannot be set to 'Left' as following employees are currently reporting to this employee:&nbsp;")
					+ ', '.join(link_to_employees), EmployeeLeftValidationError)
			if not self.relieving_date:
				throw(_("Please enter relieving date."))

	def validate_for_enabled_user_id(self, enabled):
		if not self.status == 'Active':
			return

		if enabled is None:
			frappe.throw(_("User {0} does not exist").format(self.user_id))
		if enabled == 0:
			frappe.throw(_("User {0} is disabled").format(self.user_id), EmployeeUserDisabledError)

	def validate_duplicate_user_id(self):
		employee = frappe.db.sql_list("""select name from `tabEmployee` where
			user_id=%s and status='Active' and name!=%s""", (self.user_id, self.name))
		if employee:
			throw(_("User {0} is already assigned to Employee {1}").format(
				self.user_id, employee[0]), frappe.DuplicateEntryError)

	def validate_reports_to(self):
		if self.reports_to == self.name:
			throw(_("Employee cannot report to himself."))

	def on_trash(self):
		self.update_nsm_model()
		delete_events(self.doctype, self.name)
		if frappe.db.exists("Employee Transfer", {'new_employee_id': self.name, 'docstatus': 1}):
			emp_transfer = frappe.get_doc("Employee Transfer", {'new_employee_id': self.name, 'docstatus': 1})
			emp_transfer.db_set("new_employee_id", '')

	def validate_preferred_email(self):
		if self.prefered_contact_email and not self.get(scrub(self.prefered_contact_email)):
			frappe.msgprint(_("Please enter " + self.prefered_contact_email))

	def validate_onboarding_process(self):
		employee_onboarding = frappe.get_all("Employee Onboarding",
			filters={"job_applicant": self.job_applicant, "docstatus": 1, "boarding_status": ("!=", "Completed")})
		if employee_onboarding:
			doc = frappe.get_doc("Employee Onboarding", employee_onboarding[0].name)
			doc.validate_employee_creation()
			doc.db_set("employee", self.name)

def get_timeline_data(doctype, name):
	'''Return timeline for attendance'''
	return dict(frappe.db.sql('''select unix_timestamp(attendance_date), count(*)
		from `tabAttendance` where employee=%s
			and attendance_date > date_sub(curdate(), interval 1 year)
			and status in ('Present', 'Half Day')
			group by attendance_date''', name))

@frappe.whitelist()
def get_retirement_date(date_of_birth=None):
	ret = {}
	if date_of_birth:
		try:
			retirement_age = int(frappe.db.get_single_value("HR Settings", "retirement_age") or 60)
			dt = add_years(getdate(date_of_birth),retirement_age)
			ret = {'date_of_retirement': dt.strftime('%Y-%m-%d')}
		except ValueError:
			# invalid date
			ret = {}

	return ret

def validate_employee_role(doc, method):
	# called via User hook
	if "Employee" in [d.role for d in doc.get("roles")]:
		if not frappe.db.get_value("Employee", {"user_id": doc.name}):
			frappe.msgprint(_("Please set User ID field in an Employee record to set Employee Role"))
			doc.get("roles").remove(doc.get("roles", {"role": "Employee"})[0])

def update_user_permissions(doc, method):
	# called via User hook
	if "Employee" in [d.role for d in doc.get("roles")]:
		if not has_permission('User Permission', ptype='write'): return
		employee = frappe.get_doc("Employee", {"user_id": doc.name})
		employee.update_user_permissions()

def send_birthday_reminders():
	"""Send Employee birthday reminders if no 'Stop Birthday Reminders' is not set."""
	if int(frappe.db.get_single_value("HR Settings", "stop_birthday_reminders") or 0):
		return

	birthdays = get_employees_who_are_born_today()

	if birthdays:
		employee_list = frappe.get_all('Employee',
			fields=['name','employee_name'],
			filters={'status': 'Active',
				'company': birthdays[0]['company']
		 	}
		)
		employee_emails = get_employee_emails(employee_list)
		birthday_names = [name["employee_name"] for name in birthdays]
		birthday_emails = [email["user_id"] or email["personal_email"] or email["company_email"] for email in birthdays]

		birthdays.append({'company_email': '','employee_name': '','personal_email': '','user_id': ''})

		for e in birthdays:
			if e['company_email'] or e['personal_email'] or e['user_id']:
				if len(birthday_names) == 1:
					continue
				recipients = e['company_email'] or e['personal_email'] or e['user_id']


			else:
				recipients = list(set(employee_emails) - set(birthday_emails))

			frappe.sendmail(recipients=recipients,
				subject=_("Birthday Reminder"),
				message=get_birthday_reminder_message(e, birthday_names),
				header=['Birthday Reminder', 'green'],
			)

def get_birthday_reminder_message(employee, employee_names):
	"""Get employee birthday reminder message"""
	pattern = "</Li><Br><Li>"
	message = pattern.join(filter(lambda u: u not in (employee['employee_name']), employee_names))
	message = message.title()

	if pattern not in message:
		message = "Today is {0}'s birthday \U0001F603".format(message)

	else:
		message = "Today your colleagues are celebrating their birthdays \U0001F382<br><ul><strong><li> " + message +"</li></strong></ul>"

	return message


def get_employees_who_are_born_today():
	"""Get Employee properties whose birthday is today."""
	return frappe.db.get_values("Employee",
		fieldname=["name", "personal_email", "company", "company_email", "user_id", "employee_name"],
		filters={
			"date_of_birth": ("like", "%{}".format(format_datetime(getdate(), "-MM-dd"))),
			"status": "Active",
		},
		as_dict=True
	)


def get_holiday_list_for_employee(employee, raise_exception=True):
	if employee:
		holiday_list, company = frappe.db.get_value("Employee", employee, ["holiday_list", "company"])
	else:
		holiday_list=''
		company=frappe.db.get_value("Global Defaults", None, "default_company")

	if not holiday_list:
		holiday_list = frappe.get_cached_value('Company',  company,  "default_holiday_list")

	if not holiday_list and raise_exception:
		frappe.throw(_('Please set a default Holiday List for Employee {0} or Company {1}').format(employee, company))

	return holiday_list

def is_holiday(employee, date=None):
	'''Returns True if given Employee has an holiday on the given date
	:param employee: Employee `name`
	:param date: Date to check. Will check for today if None'''

	holiday_list = get_holiday_list_for_employee(employee)
	if not date:
		date = today()

	if holiday_list:
		return frappe.get_all('Holiday List', dict(name=holiday_list, holiday_date=date)) and True or False

@frappe.whitelist()
def deactivate_sales_person(status = None, employee = None):
	if status == "Left":
		sales_person = frappe.db.get_value("Sales Person", {"Employee": employee})
		if sales_person:
			frappe.db.set_value("Sales Person", sales_person, "enabled", 0)

@frappe.whitelist()
def create_user(employee, user = None, email=None):
	emp = frappe.get_doc("Employee", employee)

	employee_name = emp.employee_name.split(" ")
	middle_name = last_name = ""

	if len(employee_name) >= 3:
		last_name = " ".join(employee_name[2:])
		middle_name = employee_name[1]
	elif len(employee_name) == 2:
		last_name = employee_name[1]

	first_name = employee_name[0]

	if email:
		emp.prefered_email = email

	user = frappe.new_doc("User")
	user.update({
		"name": emp.employee_name,
		"email": emp.prefered_email,
		"enabled": 1,
		"first_name": first_name,
		"middle_name": middle_name,
		"last_name": last_name,
		"gender": emp.gender,
		"birth_date": emp.date_of_birth,
		"phone": emp.cell_number,
		"bio": emp.bio
	})
	user.insert()
	return user.name

def get_employee_emails(employee_list):
	'''Returns list of employee emails either based on user_id or company_email'''
	employee_emails = []
	for employee in employee_list:
		if not employee:
			continue
		user, company_email, personal_email = frappe.db.get_value('Employee', employee,
											['user_id', 'company_email', 'personal_email'])
		email = user or company_email or personal_email
		if email:
			employee_emails.append(email)
	return employee_emails

@frappe.whitelist()
def get_children(doctype, parent=None, company=None, is_root=False, is_tree=False):
	filters = [['company', '=', company]]
	fields = ['name as value', 'employee_name as title']

	if is_root:
		parent = ''
	if parent and company and parent!=company:
		filters.append(['reports_to', '=', parent])
	else:
		filters.append(['reports_to', '=', ''])

	employees = frappe.get_list(doctype, fields=fields,
		filters=filters, order_by='name')

	for employee in employees:
		is_expandable = frappe.get_all(doctype, filters=[
			['reports_to', '=', employee.get('value')]
		])
		employee.expandable = 1 if is_expandable else 0

	return employees


def on_doctype_update():
	frappe.db.add_index("Employee", ["lft", "rgt"])

def has_user_permission_for_employee(user_name, employee_name):
	return frappe.db.exists({
		'doctype': 'User Permission',
		'user': user_name,
		'allow': 'Employee',
		'for_value': employee_name
	})
