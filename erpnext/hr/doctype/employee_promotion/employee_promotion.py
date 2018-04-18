# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import getdate, get_datetime

class EmployeePromotion(Document):
	def validate(self):
		if getdate(self.promotion_date) < getdate():
			frappe.throw("Cannot create promotion for past date")

	def on_submit(self):
		employee = frappe.get_doc("Employee", self.employee)
		for item in self.promotion_details:
			fieldtype = frappe.get_meta("Employee").get_field(item.fieldname).fieldtype
			new_data = item.new
			if fieldtype == "Date":
				new_data = getdate(item.new)
			elif fieldtype =="Datetime":
				new_data = get_datetime(item.new)
			setattr(employee, item.fieldname, new_data)
		employee.save()

	def on_cancel(self):
		employee = frappe.get_doc("Employee", self.employee)
		for item in self.promotion_details:
			fieldtype = frappe.get_meta("Employee").get_field(item.fieldname).fieldtype
			old_data = item.current
			if fieldtype == "Date":
				old_data = getdate(item.current)
			elif fieldtype =="Datetime":
				old_data = get_datetime(item.current)
			setattr(employee, item.fieldname, old_data)
		employee.save()
