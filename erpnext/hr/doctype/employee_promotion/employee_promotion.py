# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from erpnext.hr.utils import update_employee_work_history, validate_active_employee


class EmployeePromotion(Document):
	def validate(self):
		validate_active_employee(self.employee)

	def before_submit(self):
		if getdate(self.promotion_date) > getdate():
			frappe.throw(
				_("Employee Promotion cannot be submitted before Promotion Date"),
				frappe.DocstatusTransitionError,
			)

	def on_submit(self):
		employee = frappe.get_doc("Employee", self.employee)
		employee = update_employee_work_history(
			employee, self.promotion_details, date=self.promotion_date
		)

		if self.revised_ctc:
			employee.ctc = self.revised_ctc

		employee.save()

	def on_cancel(self):
		employee = frappe.get_doc("Employee", self.employee)
		employee = update_employee_work_history(employee, self.promotion_details, cancel=True)

		if self.revised_ctc:
			employee.ctc = self.current_ctc

		employee.save()
