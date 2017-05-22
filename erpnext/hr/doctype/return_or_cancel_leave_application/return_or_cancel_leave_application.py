# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, getdate
from frappe.model.document import Document
from erpnext.hr.doctype.leave_application.leave_application import get_number_of_leave_days

class ReturnorCancelLeaveApplication(Document):
	def validate(self):
		self.add_leave_details()
		self.validate_dates()
		self.validate_is_canceled()

	def on_submit(self):
		self.validate_dates()
		self.validate_is_canceled()
		leave_application = frappe.get_doc("Leave Application",{'name':self.leave_application})
		leave_application.return_date= self.cancel_date
		leave_application.is_canceled = 1
		leave_application.total_leave_days = get_number_of_leave_days(leave_application.employee, leave_application.leave_type,
					leave_application.from_date, self.cancel_date, leave_application.half_day)

		leave_application.save()

	def validate_dates(self):
		if getdate(self.cancel_date) > getdate(self.to_date):
			frappe.throw(_("Cancel date can not be greater or equal than end date"))
		if getdate(self.cancel_date) < getdate(self.from_date):
			frappe.throw(_("Cancel date can not be smaler than from date"))

	def add_leave_details(self):
		la =frappe.get_doc('Leave Application',{'name' : self.leave_application})
		self.employee = la.employee
		self.employee_name = la.employee_name
		self.from_date = la.from_date
		self.to_date = la.to_date
	def validate_is_canceled(self):
		leave_application = frappe.get_doc("Leave Application",{'name':self.leave_application})
		if leave_application.is_canceled == 'Yes':
			frappe.throw(_("Leave Application %s already canceled at %s")% (self.leave_application,leave_application.cancel_date) )
