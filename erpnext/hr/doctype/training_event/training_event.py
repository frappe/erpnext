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
	
	def on_update_after_submit(self):
		if self.event_status == "Scheduled" and self.send_email:
			self.invite_employee()
	
	def invite_employee(self):
		subject = _("""You are invited for to attend {0} - {1} scheduled from {2} to {3} at {4}."""\
			.format(self.type, self.event_name, self.start_time, self.end_time, self.location))
	
		for emp in self.employees:
			if emp.status== "Open":
				frappe.sendmail(frappe.db.get_value("Employee", emp.employee, "company_email"), \
					subject=subject, content= self.introduction)
				emp.status= "Invited"