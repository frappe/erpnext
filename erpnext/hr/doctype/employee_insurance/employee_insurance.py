# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from erpnext.hr.utils import set_employee_name
from frappe.utils import getdate, date_diff

class EmployeeInsurance(Document):
	def validate(self):
		self.validate_dates()
		self.validate_amount()
		if self.deduct_from_salary:
			self.check_mandatory()

	def on_submit(self):
		if self.deduct_from_salary:
			self.create_additional_salary()

	def on_cancel(self):
		if self.deduct_from_salary:
			addl_salary_list = frappe.get_all("Additional Salary", 
				filters={"reference_doctype": self.doctype, "reference_name": self.name})
			for d in addl_salary_list:
				frappe.get_doc("Additional Salary", d.name).cancel()

	def on_update_after_submit(self):
		if self.deduct_from_salary:
			frappe.db.set_value("Additional Salary", 
				{"reference_doctype": self.doctype, "reference_name": self.name},
				"to_date", self.premium_end_date
				)

	def validate_dates(self):
		date_of_joining, relieving_date= frappe.db.get_value("Employee", self.employee, 
			["date_of_joining", "relieving_date"])
		
		if date_diff(self.premium_end_date, self.premium_start_date) < 0:
			frappe.throw(_("Premium end date cannot be before premium start date "))

		if date_of_joining and getdate(self.premium_start_date) < getdate(date_of_joining):
			frappe.throw(_("Premium start date can not be before employee's joining date"))
		
		if relieving_date and getdate(self.premium_end_date) > getdate(relieving_date):
			frappe.throw(_("To date can not be after employee's relieving date"))	

	def validate_amount(self):
		if self.maturity_amount and self.maturity_amount <= 0:
			frappe.throw(_("Maturity amount should be greater than zero."))
		if self.monthly_premium and self.monthly_premium <= 0:
			frappe.throw(_("Premium amount should be greater than zero."))
		if self.maturity_amount and self.monthly_premium and self.monthly_premium > self.maturity_amount :
			frappe.throw(_("Maturity amount should be greater than premium amount."))

	def check_mandatory(self):
		if not self.salary_component:
			frappe.throw(_("Salary component must be set"))
		if not self.premium_start_date and not self.premium_end_date:
			frappe.throw(_("Premium start date and end date must be set"))
		if not self.monthly_premium:
			frappe.throw(_("Monthly premium must be set"))

	def create_additional_salary(self):
		additional_salary = frappe.new_doc("Additional Salary")
		additional_salary.employee = self.employee 
		additional_salary.company = frappe.get_value("Employee", self.employee, "company")
		additional_salary.amount = self.monthly_premium 
		additional_salary.from_date = self.premium_start_date
		additional_salary.to_date = self.premium_end_date
		additional_salary.salary_component = self.salary_component
		additional_salary.overwrite_salary_structure_amount = self.deduct_from_salary
		additional_salary.reference_doctype = self.doctype
		additional_salary.reference_name = self.name
		additional_salary.insert()
		additional_salary.submit()
	
		

