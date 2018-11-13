# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import getdate, cint
from frappe.desk.doctype.auto_repeat.auto_repeat import make_auto_repeat

class AdditionalSalary(Document):
	def validate(self):
		self.validate_dates()
		if self.amount <= 0:
			frappe.throw(_("Amount should be greater than zero."))

	def validate_dates(self):
		date_of_joining, relieving_date = frappe.db.get_value("Employee", self.employee,
			["date_of_joining", "relieving_date"])
		if self.payroll_date and self.to_date and getdate(self.payroll_date) > getdate(self.to_date):
			frappe.throw(_("To date can not be less than from date"))
		elif date_of_joining and getdate(self.payroll_date) < getdate(date_of_joining):
			frappe.throw(_("From date can not be less than employee's joining date"))
		elif relieving_date and getdate(self.to_date) > getdate(relieving_date):
 			frappe.throw(_("To date can not greater than employee's relieving date"))

	def on_submit(self):
		if cint(self.is_recurring):
			self.create_auto_repeat()

	def create_auto_repeat(self):
		auto_repeat = frappe.new_doc("Auto Repeat")
		auto_repeat.reference_doctype = self.doctype
		auto_repeat.reference_document = self.name
		auto_repeat.frequency = "Monthly"
		auto_repeat.start_date = self.payroll_date
		auto_repeat.end_date = self.to_date
		auto_repeat.repeat_on_day = getdate(self.payroll_date).day
		auto_repeat.submit_on_creation = 1
		auto_repeat.save()
		auto_repeat.submit()

	def on_update_after_submit(self):
		existing_values = frappe.db.get_value("Additional Salary", self.name,
			["to_date", "is_recurring"], as_dict=1)
		if self.is_recurring and self.is_recurring != existing_values.is_recurring:
			self.create_auto_repeat()

		if self.auto_repeat:
			if not self.is_recurring:
				frappe.db.set_value("Auto Repeat", self.auto_repeat, "disabled", 1)
			else:
				frappe.db.set_value("Auto Repeat", self.auto_repeat, "disabled", 0)
				if self.to_date and getdate(self.to_date) != getdate(existing_values.to_date):
					frappe.db.set_value("Auto Repeat", self.auto_repeat, "end_date", self.to_date)

	def on_cancel(self):
		if self.salary_slip:
			frappe.throw(_("Cannot cancel, Salary Slip {0} has been created against this")
				.format(self.salary_slip))

@frappe.whitelist()
def get_additional_salary_component(employee, start_date, end_date):
	additional_components = frappe.db.sql("""
		select salary_component, sum(amount) as amount, overwrite_salary_structure_amount, bank
		from `tabAdditional Salary`
		where employee=%(employee)s
			and docstatus = 1
			and payroll_date between %(from_date)s and %(to_date)s
		group by salary_component, overwrite_salary_structure_amount
		order by salary_component, overwrite_salary_structure_amount
	""", {
		'employee': employee,
		'from_date': start_date,
		'to_date': end_date
	}, as_dict=1)

	additional_components_list = []
	for d in additional_components:
		component = frappe.get_doc("Salary Component", d.salary_component)
		struct_row = {'salary_component': d.salary_component, 'bank': d.bank}
		for field in ["depends_on_lwp", "abbr", "is_tax_applicable", "variable_based_on_taxable_salary",
			"is_additional_component", "prorated_based_on_attendance"]:
				struct_row[field] = component.get(field)

		additional_components_list.append({
			'amount': d.amount,
			'type': component.type,
			'struct_row': struct_row,
			'overwrite': d.overwrite_salary_structure_amount
		})
	return additional_components_list