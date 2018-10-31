# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import today, get_first_day, get_last_day, add_months, getdate
from frappe.model.document import Document

class AdditionalSalaryTool(Document):
	def validate(self):
		self.sync_additional_salary()

	def sync_additional_salary(self):
		for table_fieldname in ("earnings", "deductions"):
			self.create_additional_salary(table_fieldname)

		self.update_additional_salary()

		frappe.msgprint(_("Additional Salary records updated"))


	def create_additional_salary(self, table_fieldname):
		from_date = today()
		for d in self.get(table_fieldname):
			if not d.additional_salary_id:
				addl_salary = frappe.new_doc("Additional Salary")
				addl_salary.company = self.company
				addl_salary.employee = self.employee
				addl_salary.salary_component = d.salary_component
				addl_salary.from_date = from_date
				addl_salary.amount = d.amount
				addl_salary.bank = d.bank
				addl_salary.insert()
				addl_salary.submit()
				d.additional_salary_id = addl_salary.name

	def update_additional_salary(self):
		end_date = get_last_day(add_months(today(), -1))
		addl_salary_records = get_additional_salary_records(self.employee)

		current_list = [d.additional_salary_id for d in self.earnings if d.additional_salary_id] \
			+ [d.additional_salary_id for d in self.deductions if d.additional_salary_id]
		
		delete_list, expired_list = [], []
		for d in addl_salary_records:
			if d.name not in current_list:
				if getdate(d.from_date) > getdate(end_date):
					delete_list.append(d.name)
				else:
					expired_list.append(d.name)

		for addl_salary in expired_list:
			frappe.db.set_value("Additional Salary", addl_salary, "to_date", end_date)
		
		for d in delete_list:
			addl_salary = frappe.get_doc("Additional Salary", d)
			addl_salary.cancel()


@frappe.whitelist()
def get_additional_salary_records(employee):
	start_date = get_first_day(today())
	end_date = get_last_day(today())

	additional_components = frappe.db.sql("""
		select name, salary_component, amount, type, bank, from_date
		from `tabAdditional Salary`
		where employee=%(employee)s
			and docstatus = 1
			and (
				(%(from_date)s between from_date and to_date)
				or (ifnull(to_date, '') = '' and from_date <= %(to_date)s)
				or (%(to_date)s between from_date and to_date)
				or (from_date between %(from_date)s and %(to_date)s)
			)
	""", {
		'employee': employee,
		'from_date': start_date,
		'to_date': end_date
	}, as_dict=1)

	return additional_components
			

			
