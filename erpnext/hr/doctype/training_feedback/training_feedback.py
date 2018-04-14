# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class TrainingFeedback(Document):
	def validate(self):
		self.validate_emp()
		if self.workflow_state:
			if "Rejected" in self.workflow_state:
				self.docstatus = 1
				self.docstatus = 2

	def validate_emp(self):
		if self.employee:
			employee_user = frappe.get_value("Employee", filters={"name": self.employee}, fieldname="user_id")
			if self.get('__islocal') and employee_user:
				if u'CEO' in frappe.get_roles(employee_user):
					self.workflow_state = "Created By CEO"
				elif u'Director' in frappe.get_roles(employee_user):
					self.workflow_state = "Created By Director"
				elif u'Manager' in frappe.get_roles(employee_user):
					self.workflow_state = "Created By Manager"
				elif u'Line Manager' in frappe.get_roles(employee_user):
					self.workflow_state = "Created By Line Manager"
				elif u'Employee' in frappe.get_roles(employee_user):
					self.workflow_state = "Pending"

			if not employee_user and self.get('__islocal'):
				self.workflow_state = "Pending"
