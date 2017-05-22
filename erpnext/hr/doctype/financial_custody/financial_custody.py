# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils.data import getdate
from frappe.utils import cint, cstr, date_diff, flt, formatdate, getdate
from datetime import date, datetime
from erpsystem import _send_email

class FinancialCustody(Document):
	def get_employee_from_session (self):
		if self.get('__islocal'):
			employee = frappe.get_list("Employee", fields=["name","employee_name"]
			, filters = {"user_id":frappe.session.user},ignore_permissions=True)
			if employee != []:
				self.reported_by = employee[0].name
				self.reported_by_name = employee[0].employee_name

	def before_submit(self):
		self.calculate_total_amount()
		if self.custody_value<=0:
			frappe.throw(_("Set Custody Value"))
		if self.remaining <0 :
			frappe.throw(_("Paid more than Custody Value"))

	def on_submit(self):
		self.insert_expense_claim()

	def validate(self):
		self.validate_value()

	def validate_value(self):
		self.calculate_total_amount()
		if self.custody_value <=0:
			frappe.throw(_("Set Custody Value"))

	def calculate_total_amount(self):
		il = self.financial_custody_attachment
		total = 0
		for value in il:
			total = flt(value.value)
		self.paid = total ;
		self.remaining = flt(self.custody_value) - total ;


	def insert_expense_claim(self):
		fields = self.financial_custody_attachment
		expenses=[]# other_costs training_cost accommodation_cost living_costs transportation_costs
		for value in fields:
			if value >0:
				expenses.append( {
				"claim_amount": value.value,
				"sanctioned_amount":  value.value,
				"description":_(value.title),
				"parentfield": "expenses"
				})
		expense_claim = frappe.get_doc({
		"doctype": "Expense Claim",
		"naming_series": "EXP",
		"exp_approver": self.reported_by,
		"employee": self.employee,
		"remark":self.reason,
		"expenses":expenses,
		"expense_type":"Financial Custody",
		"reference_type":"Financial Custody",
		"reference_name":self.name,
		"remark":self.reason})
		expense_claim.employee
		expense_claim.save()

	def get_department_managers(self):
		department = self.get_department()
		query = """select user.* from tabEmployee employee
							Inner Join tabUserRole role on employee.user_id = role.parent
							Inner Join tabUser user on employee.user_id = user.name
							where role.role = 'Department Manager' and employee.department='{department}'"""

		department_managers = frappe.db.sql(query.format(department=frappe.db.escape(department)), as_dict=1)
		return department_managers

	def get_department(self):
		employee = frappe.get_doc('Employee', {'name': self.reported_by})
		department = employee.department
		return department

def emp_query(doctype, txt, searchfield, start, page_len, filters):
	user = frappe.session.user
	user_roles=frappe.get_roles(user)
	return frappe.db.sql("""select name,employee_name from `tabEmployee` where status = 'Active'""")

def get_permission_query_conditions(user):
	if not user:
		user = frappe.session.user
	if u'Employee' in frappe.get_roles(user) and not u'Department Manager' in frappe.get_roles(user) :
		employee = frappe.get_doc('Employee',{'user_id' : user} )
		return """employee ='{employee}'""".format( employee=frappe.db.escape(employee.name) )
