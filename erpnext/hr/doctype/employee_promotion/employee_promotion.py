# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate
from erpnext.hr.utils import update_employee

class EmployeePromotion(Document):
	def validate(self):
		if frappe.get_value("Employee", self.employee, "status") == "Left":
			frappe.throw(_("Cannot promote Employee with status Left"))

	def before_submit(self):
		if getdate(self.promotion_date) > getdate():
			frappe.throw(_("Employee Promotion cannot be submitted before Promotion Date "),
				frappe.DocstatusTransitionError)

	def on_submit(self):
		employee = frappe.get_doc("Employee", self.employee)
		employee = update_employee(employee, self.promotion_details, date=self.promotion_date)
		employee.save()

	def on_cancel(self):
		employee = frappe.get_doc("Employee", self.employee)
		employee = update_employee(employee, self.promotion_details, cancel=True)
		employee.save()
