# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, getdate
from frappe.model.document import Document
from erpnext.hr.doctype.leave_application.leave_application import get_number_of_leave_days
from frappe.model.naming import make_autoname
# from erpnext import get_user_employee
class CancelLeaveApplication(Document):
	def autoname(self):
		self.name = make_autoname(self.employee +"-"+ self.leave_application)

	def validate(self):
		self.add_leave_details()
		self.validate_dates()
		self.validate_is_canceled()

	def on_submit(self):
		self.validate_dates()
		self.validate_is_canceled()
		leave_application = frappe.get_doc("Leave Application",{'name':self.leave_application})
		leave_application.old_to_date = leave_application.to_date
		leave_application.to_date= self.cancel_date
		# leave_application.cancel_date_hijri= self.cancel_date
		leave_application.is_canceled = "Yes"
		# employee = get_user_employee().name
		leave_application.total_leave_days = get_number_of_leave_days(self.employee, leave_application.leave_type, leave_application.from_date, 
			self.cancel_date, leave_application.half_day)
		leave_application.flags.ignore_validate_update_after_submit = True
		leave_application.save()

	def validate_dates(self):
		if getdate(self.cancel_date) >= getdate(self.to_date):
			frappe.throw(_("Cancel date can not be greater or equal than end date"))
		if getdate(self.cancel_date) < getdate(self.from_date):
			frappe.throw(_("Cancel date can not be smaller than from date"))

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
