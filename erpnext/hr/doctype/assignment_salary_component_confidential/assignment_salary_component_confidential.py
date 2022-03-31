# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class AssignmentSalaryComponentConfidential(Document):
	def validate(self):
		self.status = self.get_status()
	
	def get_status(self):
		if self.docstatus == 0:
			status = "Saved"
		elif self.docstatus == 1:
			self.validate_assignment_Salary_Component()
			status = "Finished"
		return status
	
	def on_cancel(self):
		self.eliminate_salary_component()
		if self.docstatus == 2:
			self.status = "Cancelled"
	
	def validate_assignment_Salary_Component(self):
		type_component = ""
		if self.type == "Earning":
			type_component = "earnings"
		elif self.type == "Deduction":
			type_component = "deductions"

		employees = frappe.get_all("Employee Detail Salary Component Confidential", ["employee","moneda", "parent"], filters = {"parent": self.name})
		
		for item in employees:
			salary_slip = frappe.get_all("Salary Slip", ["name"], filters={"payroll_entry":self.payroll_entry, "employee":item.employee})
			
			for salary in salary_slip:
				doc = frappe.get_doc("Salary Slip", salary.name)
				row = doc.append(type_component, {})
				row.salary_component = self.salary_component
				row.amount = item.moneda
				doc.save()
	
	def eliminate_salary_component(self):	

		employees = frappe.get_all("Employee Detail Salary Component Confidential", ["employee","moneda", "parent"], filters = {"parent": self.name})
		
		for item in employees:
			salary_slip = frappe.get_all("Salary Slip", ["name"], filters={"payroll_entry":self.payroll_entry, "employee":item.employee})
			
			for salary in salary_slip:
				doc = frappe.get_doc("Salary Slip", salary.name)

				type_component = ""

				if self.type == "Earning":
					type_component = doc.earnings
				elif self.type == "Deduction":
					type_component = doc.deductions

				for component in type_component:
					if component.salary_component == self.salary_component:
						salary_detail = frappe.get_all("Salary Detail", ["name"], filters = {"salary_component":self.salary_component, "parent":salary.name})
						frappe.delete_doc("Salary Detail", salary_detail[0].name)

				self.update_data(salary.name)
					
	def update_data(self, salary_name):
		doc = frappe.get_doc("Salary Slip", salary_name)

		total_earnings = 0
		total_deductions = 0

		for item in doc.earnings:
			total_earnings += item.amount
		
		for item in doc.deductions:
			total_deductions += item.amount
		
		net_pay = total_earnings - total_deductions
		rounded_total = round(net_pay)
		
		doc.gross_pay = total_earnings
		doc.total_deduction = total_deductions
		doc.net_pay = net_pay
		doc.rounded_total = rounded_total

		doc.save()

	def confidentials(self):
		confidentials_list = frappe.get_all("Confidential Payroll Users", ["*"])

		if len(confidentials_list):
			customers = frappe.get_all("Confidential Payroll Users Detail", ["*"], filters = {"parent":confidentials_list[0].name})
			
			if len(customers) > 0:
				user = frappe.session.user
				confidential = False

				for customer in customers:
					if user == customer.user or user == customer.name_user:
						confidential = True

				if confidential:
					self.db_set('confidential', 1, update_modified=False)
				else:
					self.db_set('confidential', 0, update_modified=False)
		else:
			self.db_set('confidential', 0, update_modified=False)