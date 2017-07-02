# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import msgprint, _

class EmployeeResignation(Document):
	
	def before_submit(self):
		if self.status == "Open":
			frappe.throw(_("Please Change The Status of the document to Approved or Rejected"))
	
	def on_submit(self):
		if self.status == "Approved":
			emp = frappe.get_doc("Employee",self.employee)
			emp.status ="Left"
			emp.relieving_date =self.permission_date
			emp.save(ignore_permissions=True)
			eos_award=frappe.new_doc("End of Service Award")
			eos_award.employee=self.employee
			eos_award.end_date=self.permission_date
			eos_award.reason="استقالة العامل"
			eos_award.insert()
