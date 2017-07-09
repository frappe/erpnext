# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, formatdate, getdate, nowdate
from frappe.model.document import Document

class OverTime(Document):
	def validate(self):
		self.validate_date()
		self.validate_hour_count()
		self.status="Pending"
		self.get_department_manager()


	def validate_date(self):
		if not self.date:
			frappe.throw(_("Date field required"))
		if getdate(self.date) > getdate(nowdate()):
			frappe.throw(_("The Overtime date cant be greater than the current date"))
			

	def validate_hour_count(self):
		if not self.hours_count:
			frappe.throw(_("Hours Count field required"))
		if self.hours_count > 24.0:
			frappe.throw(_("The Overtime Hours Count cant be more than 24 hour"))


	def on_submit(self):
		self.insert_expense_claim()
		self.status="Approved"

	def on_cancle(self):
		self.status="Rejected"



		
	def insert_expense_claim(self):

		employee = frappe.get_doc('Employee', {'name': self.employee})
		grade = frappe.get_doc('Grade', {'name': employee.grade})
		st_name = frappe.db.sql("""select parent,base from `tabSalary Structure Employee`
			where employee=%s order by modified desc limit 1""",self.employee,as_dict=True)
		if not st_name:
		    frappe.throw(_("No active or default Salary Structure found for employee {0} for the given dates")
            					.format(self.employee), title=_('Salary Structure Missing'))
		if st_name:
			struct = frappe.db.sql("""select name from `tabSalary Structure`where name=%s and is_active = 'Yes' limit 1""",st_name[0].parent)
			if not struct:
				self.salary_structure = None
				frappe.throw(_("No active or default Salary Structure found for employee {0} for the given dates")
					.format(self.employee), title=_('Salary Structure Missing'))

		main_payment = st_name[0].base
		overtime_value=1.0
		if grade:
			overtime_value=grade.overtime_value

		hour_sal=(float(main_payment) /160.0 )*overtime_value
		app_user=frappe.get_doc("Employee",self.approval)
		app_userr=app_user.user_id

		expenses=[{
				"claim_amount": hour_sal,
				"expense_type": "over time",
				"sanctioned_amount":  hour_sal,
				"expense_date":  self.date,
				"description":self.reson,
				"parentfield": "expenses"
				}]
		expense_claim = frappe.get_doc({
		"doctype": "Expense Claim",
		"naming_series": "EXP",
		"exp_approver": app_userr,
		"posting_date":  self.date,
		"employee": self.employee,
		"expenses":expenses,
		"reference_type":"Over Time",
		"reference_name":self.name,
		"remark":self.reson,
		"company" :"Tawari"
		}).insert(ignore_permissions=True)







	def get_department_manager(self):
		owner_employee = frappe.get_doc('Employee',{'name' : self.employee } )
		dep_manager=""
		owner_department = owner_employee.department
		if owner_department:
			dep_doc=frappe.get_doc("Department",owner_department)
			if dep_doc:
				dep_manager=dep_doc.sub_department_manager if  dep_doc.sub_department_manager else (dep_doc.department_manager or "")
				if str(dep_manager) == str(self.employee):
					dep_doc=frappe.get_doc("Department",dep_doc.department_parent)
					dep_manager=dep_doc.sub_department_manager if  dep_doc.sub_department_manager else (dep_doc.department_manager or "")


		self.approval=dep_manager 
		app_doc=frappe.get_doc("Employee",dep_manager)
		self.approval_name=app_doc.employee_name

def get_permission_query_conditions(user):
	if not user: user = frappe.session.user
	employees = frappe.get_list("Employee", fields=["name"], filters={'user_id': user}, ignore_permissions=True)
	if employees:
		employee = frappe.get_doc('Employee', {'name': employees[0].name})

		if employee:
			query = ""
			if u'System Manager' in frappe.get_roles(user) or u'HR User' in frappe.get_roles(user):
				return ""
				
			if u'Employee' in frappe.get_roles(user):
				if query != "":
					query+=" or "
				query+="employee = '{0}'".format(employee.name)

			if u'Sub Department Manager' in frappe.get_roles(user):
				if query != "":
					query+=" or "
				department = frappe.get_value("Department" , filters= {"sub_department_manager": employee.name}, fieldname="name")
				query+="""employee in (SELECT name from tabEmployee where tabEmployee.department = '{0}')) or employee = '{1}'""".format(department, employee.name)

			if u'Department Manager' in frappe.get_roles(user):
				if query != "":
					query+=" or "
				department = frappe.get_value("Department" , filters= {"department_manager": employee.name}, fieldname="name")
				query+="""employee in (SELECT name from tabEmployee where tabEmployee.department in 
				(SELECT name from tabDepartment where parent_department = '{0}')) or employee = '{1}'""".format(department, employee.name)
			return query

