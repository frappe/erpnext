# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class TrainingResult(Document):
	def on_submit(self):
		self.send_result()
	
	def send_result(self):
		for emp in self.employees:
			message = "Thank You for attending {0}.".format(self.training_event)
			if emp.grade: 
				message = message + "Your grade: {0}".format(emp.grade)
			frappe.sendmail(frappe.db.get_value("Employee", emp.employee, "company_email"), \
				subject=_("{0} Results".format(self.training_event)), \
				content=message)

@frappe.whitelist()
def get_employees(training_event):
	return frappe.get_doc("Training Event", training_event).employees
