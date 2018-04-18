# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import getdate, get_datetime

class EmployeeTransfer(Document):
	def validate(self):
		if getdate(self.transfer_date) < getdate():
			frappe.throw("Cannot create promotion for past date")

	def on_submit(self):
		employee = frappe.get_doc("Employee", self.employee)
		for item in self.transfer_details:
			fieldtype = frappe.get_meta("Employee").get_field(item.fieldname).fieldtype
			new_data = item.new
			if fieldtype == "Date" and new_data:
				new_data = getdate(item.new)
			elif fieldtype =="Datetime" and new_data:
				new_data = get_datetime(item.new)
			setattr(employee, item.fieldname, new_data)
		employee.company = self.new_company
		if self.create_new_employee_id:
			#remove data from object to create new employee
			employee.name = employee.creation = employee.modified = employee.modified_by = employee.owner = ""
			new_employee = employee.insert()
			self.db_set("new_employee_id", new_employee.name)
			#relieve the old employee
			old_employee = frappe.get_doc("Employee", self.employee)
			old_employee.status = "Left"
			old_employee.relieving_date = getdate()
			old_employee.save()
		else:
			employee.save()

	def on_cancel(self):
		if self.create_new_employee_id:
			#mark the new employee status as left, not sure deletion is possible
			new_employee = frappe.get_doc("Employee", self.new_employee_id)
			new_employee.status = "Left"
			new_employee.relieving_date = getdate()
			new_employee.save()
			#mark the employee as active
			employee = frappe.get_doc("Employee", self.employee)
			employee.status = "Active"
			employee.relieving_date = ''
			employee.save()
		else:
			employee = frappe.get_doc("Employee", self.employee)
			for item in self.transfer_details:
				fieldtype = frappe.get_meta("Employee").get_field(item.fieldname).fieldtype
				old_data = item.current
				if fieldtype == "Date" and old_data:
					old_data = getdate(item.current)
				elif fieldtype =="Datetime" and old_data:
					old_data = get_datetime(item.current)
				setattr(employee, item.fieldname, old_data)
		employee.save()
