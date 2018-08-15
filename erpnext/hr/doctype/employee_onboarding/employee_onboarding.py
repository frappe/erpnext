# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from erpnext.hr.utils import EmployeeBoardingController
from frappe.model.mapper import get_mapped_doc

class IncompleteTaskError(frappe.ValidationError): pass

class EmployeeOnboarding(EmployeeBoardingController):
	def validate(self):
		super(EmployeeOnboarding, self).validate()

	def validate_employee_creation(self):
		if self.docstatus != 1:
			frappe.throw(_("Submit this to create the Employee record"))
		else:
			for activity in self.activities:
				if not activity.required_for_employee_creation:
					continue
				else:
					task_status = frappe.db.get_value("Task", activity.task, "status")
					if task_status not in ["Closed", "Cancelled"]:
						frappe.throw(_("All the mandatory Task for employee creation hasn't been done yet."), IncompleteTaskError)

	def on_submit(self):
		super(EmployeeOnboarding, self).on_submit()

	def on_cancel(self):
		super(EmployeeOnboarding, self).on_cancel()

@frappe.whitelist()
def make_employee(source_name, target_doc=None):
	doc = frappe.get_doc("Employee Onboarding", source_name)
	doc.validate_employee_creation()
	def set_missing_values(source, target):
		target.personal_email = frappe.db.get_value("Job Applicant", source.job_applicant, "email_id")
		target.status = "Active"
	doc = get_mapped_doc("Employee Onboarding", source_name, {
			"Employee Onboarding": {
				"doctype": "Employee",
				"field_map": {
					"first_name": "employee_name",
					"employee_grade": "grade",
				}}
		}, target_doc, set_missing_values)
	return doc

