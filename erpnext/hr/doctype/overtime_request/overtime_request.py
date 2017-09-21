# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, formatdate, getdate, nowdate, get_datetime_str, get_first_day, get_last_day, date_diff
from erpnext.hr.doctype.employee.employee import get_holiday_list_for_employee
from erpnext.hr.doctype.leave_application.leave_application import get_holidays

class OvertimeRequest(Document):
	def validate(self):
		self.validate_dates()
		self.validate_max_hours()
		if self.workflow_state:
			if "Rejected" in self.workflow_state:
				self.docstatus = 1
				self.docstatus = 2
		# self.get_overtime_records()

	def validate_dates(self):
		if getdate(self.from_date) > getdate(self.to_date):
			frappe.throw(_("to date must be equal or greater than from date"))
		if getdate(self.from_date).month != getdate(self.to_date).month:
			frappe.throw(_("Must be the same month"))
		if getdate(self.from_date).year != getdate(self.to_date).year:
			frappe.throw(_("Must be the same year"))
		for overtime_detail in self.get("overtime_details", self.overtime_details):
			if getdate(overtime_detail.date) < getdate(self.from_date) or getdate(overtime_detail.date) > getdate(self.to_date):
				frappe.throw(_("The overtime date must be between from date and to date in row # {0}".format(overtime_detail.idx)))

	def validate_max_hours(self):
		for overtime_detail in self.get("overtime_details",self.overtime_details):
			hol_count = get_holidays(self.employee, overtime_detail.date, overtime_detail.date)
			if(hol_count >= 1):
				if(overtime_detail.hours > 6):
					frappe.throw(_("You can't insert more than 6 hours as overtime in a holiday day at row # {0}".format(overtime_detail.idx)));
			else:
				if(overtime_detail.hours > 3):
					frappe.throw(_("You can't insert more than 3 hours as overtime in a working day at row # {0}".format(overtime_detail.idx)));
		

	def get_overtime_records(self):
		start_day = getdate(self.from_date).day
		end_day = getdate(self.to_date).day
		month = getdate(self.from_date).month
		year = getdate(self.to_date).year

		overtime_details=[]
		for i in range(start_day, end_day+1):
			overtime_details.append({
			"date":"{0}-{1}-{2}".format(year, month, i),
			"hours":0
			})
		self.set("overtime_details",overtime_details)
