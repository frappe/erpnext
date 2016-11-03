# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class TrainingEvent(Document):
	def validate(self):
		if self.event_status == "Scheduled":
			self.invite_employee()
		elif self.event_status == "Completed":
			self.send_result()
	
	def invite_employee(self):
		message = _("A {0} - {1} has been scheduled from {2} to {3} at {4}. You are requested to attend the same."\
			.format(self.type, self.event_name, self.start_time, self.end_time, self.location))
		
		for emp in self.employees:
			if emp.status== "Scheduled":
				frappe.sendmail(frappe.db.get_value("Employee", emp.employee, "company_email"), \
					subject=_("{0} - {1} invitation".format(self.type, self.event_name)), \
					content=message)
				emp.status= "Invited"
				
	def send_result(self):
		for emp in self.employees:
			if not emp.result_sent:
				message = "Thank You for attending {0} - {1}. You grade is {2}".format(self.type, self.event_name, self.grade)
				frappe.sendmail(frappe.db.get_value("Employee", emp.employee, "company_email"), \
					subject=_("{0} - {1} Grade".format(self.type, self.event_name)), \
					content=message)
				emp.result_sent= 1
					
				
				
			