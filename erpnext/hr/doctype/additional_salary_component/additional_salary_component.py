# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import formatdate, format_datetime, getdate, get_datetime, nowdate
from erpnext.hr.utils import validate_dates

class AdditionalSalaryComponent(Document):
	def validate(self):
		# self.validate_dates()
		validate_dates(self, self.from_date, self.to_date)

	# def validate_dates(self):
 # 		date_of_joining, relieving_date = frappe.db.get_value("Employee", self.employee,
	# 		["date_of_joining", "relieving_date"])
 # 		if getdate(self.from_date) > getdate(to_date):
 # 			frappe.throw(_("To date can not be less than from date"))
 # 		elif getdate(self.from_date) > getdate(nowdate()):
 # 			frappe.throw(_("Future dates not allowed"))
 # 		elif date_of_joining and getdate(self.from_date) < getdate(date_of_joining):
 # 			frappe.throw(_("From date can not be less than employee's joining date"))
 # 		elif relieving_date and getdate(to_date) > getdate(relieving_date):
 # 			frappe.throw(_("To date can not greater than employee's relieving date"))
