# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
import json
from six import string_types
from frappe import _, bold
from frappe.utils import add_days, get_datetime, today
from frappe.model.document import Document

class EmployeeGrievance(Document):
	def on_submit(self):
		if self.status not in ["Invalid", "Resolved"]:
			frappe.throw(_("Only Employee Grievance with status {0} and {1} can be submitted").format(
				bold("Invalid"),
				bold("Resolved"))
			)

	def before_cancel(self):
		if self.suspended_from and self.suspended_to and not self.unsuspended_on:
			frappe.throw(_("You need to Unsuspend Employee before Cancellation"))

@frappe.whitelist()
def create_additional_salary(doc):
	import json
	from six import string_types

	if isinstance(doc, string_types):
		doc = frappe._dict(json.loads(doc))

	if not frappe.db.exists("Additional Salary", {"ref_docname": doc.name}):
		additional_salary = frappe.new_doc("Additional Salary")
		additional_salary.employee = doc.employee_responsible
		additional_salary.company = frappe.db.get_value("Employee", doc.employee_responsible, "company")
		additional_salary.overwrite_salary_structure_amount = 0
		additional_salary.ref_doctype = doc.doctype
		additional_salary.ref_docname = doc.name
		additional_salary.is_recurring = 1
		additional_salary.from_date = doc.suspended_from
		additional_salary.to_date = doc.suspended_to
		additional_salary.type = "Deduction"
	else:
		frappe.throw(_("Additional Salary of type Deduction is already created for pay cut"))

	return additional_salary


@frappe.whitelist()
def unsuspend_employee(doc):
	if isinstance(doc, string_types):
		doc = json.loads(grievance)
		doc = frappe._dict(doc)

	frappe.db.set_value("Employee Grievance", doc.name, "unsuspended_on", today())
	frappe.db.set_value("Employee", doc.employee_responsible, "status", "Active")


@frappe.whitelist()
def suspend_employee(doc):
	if isinstance(doc, string_types):
		doc = json.loads(grievance)
		doc = frappe._dict(doc)

	if not doc.suspension_period_in_days:
		frappe.throw(_("Grievance Type: {0} is not applicable for suspension").format(doc.grievance_type))

	frappe.db.set_value("Employee Grievance", doc.name, {
		"suspended_from": today(),
		"suspended_to": add_days(today(), doc.suspension_period_in_days),
	})

	frappe.db.set_value("Employee", doc.employee_responsible, "status", "Suspended")


@frappe.whitelist()
def check_and_unsuspend_employees():
	data = frappe.get_all("Employee Grievance", filters={
		"docstatus": 1,
		"suspended_to": ("<=", today()),
		"unsuspended_on": ""
	}, fields = ["name", "suspended_to"])

	for d in data:
		if d.suspended_to:
			unsuspend_employee(d.name)

