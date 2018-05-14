# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import formatdate, format_datetime
from frappe.utils import getdate, get_datetime
from frappe.model.document import Document
from frappe.desk.form import assign_to

class EmployeeBoardingController(Document):
	'''
		Create the project and the task for the boarding process
		Assign to the concerned person and roles as per the onboarding/separation template
	'''
	def validate(self):
		# remove the task if linked before submitting the form
		if self.amended_from:
			for activity in self.activities:
				activity.task = ''

	def on_submit(self):
		# create the project for the given employee onboarding
		project_name = _(self.doctype) + " : " + self.employee_name
		if self.doctype == "Employee Onboarding":
			project_name += " (" + self.job_applicant + ")"
		else:
			project_name += " (" + self.employee + ")"
		project = frappe.get_doc({
				"doctype": "Project",
				"project_name": project_name,
				"expected_start_date": self.date_of_joining if self.doctype == "Employee Onboarding" else self.resignation_letter_date,
				"department": self.department,
				"company": self.company
			}).insert(ignore_permissions=True)
		self.db_set("project", project.name)

		# create the task for the given project and assign to the concerned person
		for activity in self.activities:
			task = frappe.get_doc({
					"doctype": "Task",
					"project": project.name,
					"subject": activity.activity_name + " : " + self.employee_name,
					"description": activity.description,
					"department": self.department,
					"company": self.company
				}).insert(ignore_permissions=True)
			activity.db_set("task", task.name)
			users = [activity.user] if activity.user else []
			if activity.role:
				user_list = frappe.db.sql_list('''select distinct(parent) from `tabHas Role`
					where parenttype='User' and role=%s''', activity.role)
				users = users + user_list

			# assign the task the users
			if users:
				self.assign_task_to_users(task, set(users))

	def assign_task_to_users(self, task, users):
		for user in users:
			args = {
				'assign_to' 	:	user,
				'doctype'		:	task.doctype,
				'name'			:	task.name,
				'description'	:	task.description or task.subject,
			}
			assign_to.add(args)

	def on_cancel(self):
		# delete task project
		for task in frappe.get_all("Task", filters={"project": self.project}):
			frappe.delete_doc("Task", task.name)
		frappe.delete_doc("Project", self.project)
		self.db_set('project', '')
		for activity in self.activities:
			activity.db_set("task", "")


@frappe.whitelist()
def get_onboarding_details(parent, parenttype):
	return frappe.get_list("Employee Boarding Activity",
		fields=["activity_name", "role", "user", "required_for_employee_creation", "description"],
		filters={"parent": parent, "parenttype": parenttype},
		order_by= "idx")


def set_employee_name(doc):
	if doc.employee and not doc.employee_name:
		doc.employee_name = frappe.db.get_value("Employee", doc.employee, "employee_name")

def update_employee(employee, details, cancel=False):
	for item in details:
		fieldtype = frappe.get_meta("Employee").get_field(item.fieldname).fieldtype
		new_data = item.new if not cancel else item.current
		if fieldtype == "Date" and new_data:
			new_data = getdate(new_data)
		elif fieldtype =="Datetime" and new_data:
			new_data = get_datetime(new_data)
		setattr(employee, item.fieldname, new_data)
	return employee

@frappe.whitelist()
def get_employee_fields_label():
	fields = []
	for df in frappe.get_meta("Employee").get("fields"):
		if df.fieldtype in ["Data", "Date", "Datetime", "Float", "Int",
		"Link", "Percent", "Select", "Small Text"] and df.fieldname not in ["lft", "rgt", "old_parent"]:
			fields.append({"value": df.fieldname, "label": df.label})
	return fields

@frappe.whitelist()
def get_employee_field_property(employee, fieldname):
	if employee and fieldname:
		field = frappe.get_meta("Employee").get_field(fieldname)
		value = frappe.db.get_value("Employee", employee, fieldname)
		options = field.options
		if field.fieldtype == "Date":
			value = formatdate(value)
		elif field.fieldtype == "Datetime":
			value = format_datetime(value)
		return {
			"value" : value,
			"datatype" : field.fieldtype,
			"label" : field.label,
			"options" : options
		}
	else:
		return False

def update_employee(employee, details, cancel=False):
	for item in details:
		fieldtype = frappe.get_meta("Employee").get_field(item.fieldname).fieldtype
		new_data = item.new if not cancel else item.current
		if fieldtype == "Date" and new_data:
			new_data = getdate(new_data)
		elif fieldtype =="Datetime" and new_data:
			new_data = get_datetime(new_data)
		setattr(employee, item.fieldname, new_data)
	return employee

def validate_tax_declaration(declarations):
	subcategories = []
	for declaration in declarations:
		if declaration.exemption_sub_category in  subcategories:
			frappe.throw(_("More than one selection for {0} not \
			allowed").format(declaration.exemption_sub_category), frappe.ValidationError)
		subcategories.append(declaration.exemption_sub_category)
		max_amount = frappe.db.get_value("Employee Tax Exemption Sub Category", \
		declaration.exemption_sub_category, "max_amount")
		if declaration.amount > max_amount:
			frappe.throw(_("Max exemption amount for {0} is {1}").format(\
			declaration.exemption_sub_category, max_amount), frappe.ValidationError)

def get_leave_period(from_date, to_date, company):
	leave_period = frappe.db.sql("""
		select name, from_date, to_date
		from `tabLeave Period`
		where company=%(company)s and is_active=1
			and (from_date between %(from_date)s and %(to_date)s
				or to_date between %(from_date)s and %(to_date)s
				or (from_date < %(from_date)s and to_date > %(to_date)s))
	""", {
		"from_date": from_date,
		"to_date": to_date,
		"company": company
	}, as_dict=1)

	if leave_period:
		return leave_period

