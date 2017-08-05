# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class EmployeeBadgeRequest(Document):
	def on_update(self):
		if self.accept != "Yes":
			frappe.throw( _("You must accept the Pledge before you can save the request") )



	def get_employee_illnes(self):
		if self.employee:
			employee = frappe.get_doc("Employee", {"name": self.employee})
			special_case=""
			if employee.chronic_disease:
				for value in employee.chronic_disease:
					special_case+= value.illness_name +"\n"
				self.special_case = special_case
			else :
				self.special_case ="-"
		return self.special_case

	def before_submit(self):
		if self.badge_received != "Yes":
			frappe.throw(_("Employee must recieve the Badge before submit"))
