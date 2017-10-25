# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, getdate
from frappe.model.document import Document
from erpnext.hr.doctype.leave_application.leave_application import get_number_of_leave_days
from frappe.model.naming import make_autoname
# from erpnext import get_user_employee
class CancelLeaveApplication(Document):
	# @frappe.whitelist() 
	# def cancel_leave_app(self,leave_app):
	# 	leave_doc=frappe.get_doc("Leave Application", str(leave_app))
	# 	name=leave_doc.employee_name
	# 	# 
	# 	leave_doc.is_canceled=1
	# 	leave_doc.workflow_state='Rejected By Employee'
	# 	leave_doc.save()
	# 	# leave_doc.submit()
	# 	# leave_doc.cancel()

	# 	return """ canceled """+name


	def autoname(self):
		self.name = make_autoname(self.employee +"-"+ self.leave_application)


	def validate(self):
		self.add_leave_details()
		self.validate_dates()
		self.validate_is_canceled()
		self.validate_emp()
		if self.workflow_state:
			if "Rejected" in self.workflow_state:
				self.docstatus = 1
				self.docstatus = 2

	def on_submit(self):
		self.validate_leave_cancelation()
	pass

	def validate_emp(self):
		 if self.get('__islocal'):
			if u'CEO' in frappe.get_roles(frappe.session.user):
				self.workflow_state = "Created By CEO"
			elif u'Director' in frappe.get_roles(frappe.session.user):
				self.workflow_state = "Created By Director"
			elif u'Manager' in frappe.get_roles(frappe.session.user):
				self.workflow_state = "Created By Manager"
			elif u'Line Manager' in frappe.get_roles(frappe.session.user):
				self.workflow_state = "Created By Line Manager"
			elif u'Employee' in frappe.get_roles(frappe.session.user):
				self.workflow_state = "Pending"

	def validate_dates(self):
		if getdate(self.cancel_date) >= getdate(self.to_date):
			frappe.throw(_("Cancel date can not be greater or equal than end date"))
   
	def validate_leave_cancelation(self):
		leave_application = frappe.get_doc("Leave Application",{'name':self.leave_application})
		if leave_application:
			if getdate(self.cancel_date) < getdate(self.from_date):
				if leave_application.docstatus == 1:
					leave_application.flags.ignore_validate_update_after_submit = True
				elif leave_application.docstatus == 2:
					frappe.throw(_("Leave Application {0} is already canceled".format(self.leave_application)))
				else:
					leave_application = frappe.get_doc("Leave Application", self.leave_application)
					leave_application.is_canceled = "Yes"
					leave_application.workflow_state ='Canceled By Employee'
					leave_application.save()
					frappe.msgprint(_("Leave Application record {0} has been canceled").format("<a href='#Form/Leave Application/{0}'>{0}</a>".format(self.leave_application)))
		# leave_doc=frappe.get_value("Leave Application",filters={"name":self.leave_application},fieldname="docstatus")
		# if leave_doc==0:
			elif getdate(self.cancel_date) >= getdate(self.from_date) and getdate(self.cancel_date) <= getdate(self.to_date):
				leave_application.old_to_date = leave_application.to_date
				leave_application.to_date= self.cancel_date
				leave_application.is_canceled = 1
				leave_application.total_leave_days = get_number_of_leave_days(self.employee, leave_application.leave_type, leave_application.from_date, 
					self.cancel_date, leave_application.half_day)
				leave_application.flags.ignore_validate_update_after_submit = True
				leave_application.save()
				frappe.msgprint(_("Leave Application to date {0} has been amended").format("<a href='#Form/Leave Application/{0}'>{0}</a>".format(self.leave_application)))			

	def add_leave_details(self):
		la =frappe.get_doc('Leave Application',{'name' : self.leave_application})
		self.employee = la.employee
		self.employee_name = la.employee_name
		self.from_date = la.from_date
		self.to_date = la.to_date
	
	def validate_is_canceled(self):
		leave_application = frappe.get_doc("Leave Application",{'name':self.leave_application})
		if leave_application.is_canceled == 'Yes':
			frappe.throw(_("Leave Application {0} already is canceled".format(self.leave_application)))


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

	# 		# if u'Leave Approver' in frappe.get_roles(user):	
	# 		# 	if query != "":
	# 		# 		query+=" or "
 #   #      		query+= """(`tabreturn_from_leave_statement`.leave_approver = '{user}' or `tabreturn_from_leave_statement`.employee = '{employee}')""" \
 #   #          	.format(user=frappe.db.escape(user), employee=frappe.db.escape(employee.name))

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
