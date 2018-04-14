# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, formatdate, getdate, nowdate, get_datetime_str, get_first_day, get_last_day
from frappe.model.document import Document

class OverTime(Document):
	def validate(self):

		self.validate_date()
		self.validate_hour_count()
		self.overtime_hours = frappe.utils.data.time_diff_in_hours(self.to_date, self.from_date)
		# frappe.throw(str(frappe.utils.data.time_diff_in_hours(self.to_date, self.from_date)))
		self.insert_expense_claim()
		# self.get_department_manager()
		self.validate_emp()
		if self.workflow_state:
			if "Rejected" in self.workflow_state:
				self.docstatus = 1
				self.docstatus = 2

	def validate_emp(self):
		if self.employee:
			employee_user = frappe.get_value("Employee", filters={"name": self.employee}, fieldname="user_id")
			if self.get('__islocal') and employee_user:
				if u'CEO' in frappe.get_roles(employee_user):
					self.workflow_state = "Created By CEO"
				elif u'Director' in frappe.get_roles(employee_user):
					self.workflow_state = "Created By Director"
				elif u'Manager' in frappe.get_roles(employee_user):
					self.workflow_state = "Created By Manager"
				elif u'Line Manager' in frappe.get_roles(employee_user):
					self.workflow_state = "Created By Line Manager"
				elif u'Employee' in frappe.get_roles(employee_user):
					self.workflow_state = "Pending"
					
			if not employee_user and self.get('__islocal'):
				self.workflow_state = "Pending"
	def validate_date(self):
		pass
		# if not self.date:
		# 	frappe.throw(_("Date field required"))
		# if getdate(self.date) > getdate(nowdate()):
		# 	frappe.throw(_("The Overtime date cant be greater than the current date"))
			

	def validate_hour_count(self):
		pass
		# if not self.hours_count:
		# 	frappe.throw(_("Hours Count field required"))
		# if self.hours_count > 24:
		# 	frappe.throw(_("The Overtime Hours Count cant be more than 24 hour"))


	def on_submit(self):
		# self.insert_expense_claim()
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

		hour_sal=(float(main_payment) /160.0 )*overtime_value*self.overtime_hours
		# app_user=frappe.get_doc("Employee",self.approval)
		# app_userr=app_user.user_id
		date_d = getdate(self.from_date)
		exp_date = get_datetime_str(date_d)
		first_day= get_first_day(exp_date)
		last_day= get_last_day(exp_date)

		parent_exp = frappe.db.sql("""Select parent from `tabExpense Claim Detail` where
		 expense_date between '{0}' and '{1}' and expense_type = 'Over Time'
		 order by modified desc limit 1""".format(first_day,last_day), as_dict=True)

		expenses=[{
				"claim_amount": hour_sal,
				"expense_type": "over time",
				"sanctioned_amount":  hour_sal,
				"expense_date": exp_date,
				"description":self.reason,
				"parentfield": "expenses",
				"default_account":"42010008-Wages - اجور - T"
				}]
		if parent_exp:
			exp_claim = frappe.get_doc("Expense Claim",parent_exp[0].parent)
			exp_claim.set("expenses",expenses)

		else:
			expense_claim = frappe.get_doc({
			"doctype": "Expense Claim",
			"naming_series": "EXP",
			"posting_date":  exp_date,
			"employee": self.employee,
			"expenses":expenses,
			"reference_type":"Over Time",
			"reference_name":self.name,
			"remark":self.reason,
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
		query = ""
		employee = frappe.get_doc('Employee', {'name': employees[0].name})
		
		if u'Employee' in frappe.get_roles(user):
			if query != "":
				query+=" or "
			query+=""" employee = '{0}'""".format(employee.name)
		return query


# def get_permission_query_conditions(user):
# 	pass
	# if not user: user = frappe.session.user
	# employees = frappe.get_list("Employee", fields=["name"], filters={'user_id': user}, ignore_permissions=True)
	# if employees:
	# 	employee = frappe.get_doc('Employee', {'name': employees[0].name})

	# 	if employee:
	# 		query = ""
	# 		if u'System Manager' in frappe.get_roles(user) or u'HR User' in frappe.get_roles(user):
	# 			return ""
				
	# 		if u'Employee' in frappe.get_roles(user):
	# 			if query != "":
	# 				query+=" or "
	# 			query+="employee = '{0}'".format(employee.name)

	# 		if u'Sub Department Manager' in frappe.get_roles(user):
	# 			if query != "":
	# 				query+=" or "
	# 			department = frappe.get_value("Department" , filters= {"sub_department_manager": employee.name}, fieldname="name")
	# 			query+="""employee in (SELECT name from tabEmployee where tabEmployee.department = '{0}')) or employee = '{1}'""".format(department, employee.name)

	# 		if u'Department Manager' in frappe.get_roles(user):
	# 			if query != "":
	# 				query+=" or "
	# 			department = frappe.get_value("Department" , filters= {"department_manager": employee.name}, fieldname="name")
	# 			query+="""employee in (SELECT name from tabEmployee where tabEmployee.department in 
	# 			(SELECT name from tabDepartment where parent_department = '{0}')) or employee = '{1}'""".format(department, employee.name)
	# 		return query

