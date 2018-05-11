# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class EmployeeBenefitApplication(Document):
	def before_submit(self):
		self.validate_duplicate_on_payroll_period()

	def validate_duplicate_on_payroll_period(self):
		application = frappe.db.exists(
			"Employee Benefit Application",
			{
				'employee': self.employee,
				'payroll_period': self.payroll_period,
				'docstatus': 1
			}
		)
		if application:
			frappe.throw(_("Employee {0} already submited an apllication {1} for the payroll period {2}").format(self.employee, application, self.payroll_period))
