# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate
from frappe.model.document import Document
from erpnext.hr.doctype.leave_application.leave_application import get_number_of_leave_days
# from erpnext import get_user_employee

class ReturnFromLeaveStatement(Document):
	def validate(self):
		self.add_leave_details()
		self.validate_dates()
		# self.validate_emp()

	def on_submit(self):
		self.validate_dates()
		leave_application = frappe.get_doc("Leave Application",{'name':self.leave_application})
		if leave_application.status == "Returned":
			frappe.throw(_("This Leave Application is already returned"))
		else:
			leave_application.return_date = self.return_date
			leave_application.status = "Returned"
			# leave_application.cancel_date_hijri= self.cancel_date
			# leave_application.is_canceled = "Yes"
			# leave_application.return_from_leave_statement = self.name
			# employee = get_user_employee().name
			# leave_application.total_leave_days = get_number_of_leave_days(leave_application.leave_type,
			# 	leave_application.from_date, self.cancel_date,employee, leave_application.half_day)
			leave_application.flags.ignore_validate_update_after_submit = True
			leave_application.save()

	def validate_dates(self):
		if getdate(self.return_date) <= getdate(self.to_date):
			frappe.throw(_("Return date can not be smaller or equal than to date"))
		if getdate(nowdate()) != getdate(self.return_date):
			frappe.throw(_("The return date must be today date"))
			

	def validate_emp(self):
		if self.get('__islocal'):
			if u'Regional Director' in frappe.get_roles(frappe.session.user):
				self.workflow_state = "Created By Regional Director"
			elif u'Department Manager' in frappe.get_roles(frappe.session.user):
				self.workflow_state = "Created By Department Manager"
			elif u'Line Manager' in frappe.get_roles(frappe.session.user):
				self.workflow_state = "Created By Line Manager"
			elif u'Employee' in frappe.get_roles(frappe.session.user):
				self.workflow_state = "Created By Employee"
			employee = frappe.get_list("Employee", fields=["name", "employee_name"], filters={"user_id": frappe.session.user}, ignore_permissions=True)
			if employee:
				self.employee = employee[0].name
				self.employee_name = employee[0].employee_name
		else :
			if not self.employee :
				frappe.throw(_("Employee field is mandatory"))

				
				
	def add_leave_details(self):
		emp =frappe.get_doc('Employee',{'name' : self.employee})
		la =frappe.get_doc('Leave Application',{'name' : self.leave_application})
		self.employee = la.employee
		self.employee_name = la.employee_name
		# self.employee_name_english = emp.employee_name_english
		# self.grade = emp.grade
		# self.region = emp.region
		# self.branch = emp.branch
		# self.department = emp.department
		# self.designation = emp.designation
		self.from_date = la.from_date
		self.to_date = la.to_date
		self.total_leave_days = la.total_leave_days
		self.leave_approver = la.leave_approver
		self.leave_approver_name = la.leave_approver_name
		#self.actual_departure_date = la.actual_departure_date
		self.from_date = la.from_date
		self.to_date = la.to_date
		#self.actual_departure_date_hijri = la.actual_departure_date_hijri
		# self.from_date_hijri = la.from_date_hijri
		# self.to_date_hijri = la.to_date_hijri
		# self.cancel_date_hijri = la.cancel_date_hijri


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

			# if u'Leave Approver' in frappe.get_roles(user):	
			# 	if query != "":
			# 		query+=" or "
   #      		query+= """(`tabreturn_from_leave_statement`.leave_approver = '{user}' or `tabreturn_from_leave_statement`.employee = '{employee}')""" \
   #          	.format(user=frappe.db.escape(user), employee=frappe.db.escape(employee.name))

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



# def get_permission_query_conditions(user):	
# 	pass
# 	if not user: user = frappe.session.user
# 	employees = frappe.get_list("Employee", fields=["name"], filters={'user_id': user}, ignore_permissions=True)
# 	if employees:
# 		employee = frappe.get_doc('Employee', {'name': employees[0].name})
# 		department = frappe.get_doc('Department', {'name': employee.department})

# 		region = employee.region
# 		region_city = employee.region_city
# 		region_department = employee.region_department

# 		roles = ["Line Manager","Department Manager","Regional Director","Vice Presedint","CEO"]

		
# 		query_conditions = ""
			
# 		if u'HR Region Supervisor' in frappe.get_roles(user) or u'HR User' in frappe.get_roles(user):			
# 			query_conditions =  """(`tabReturn From Leave Statement`.owner in (SELECT user_id FROM tabEmployee WHERE region='{region}') or
# 				`tabReturn From Leave Statement`.employee in (SELECT name FROM tabEmployee WHERE region='{region}')
# 				)""" \
# 					.format(region=frappe.db.escape(region))
			

# 		elif u'CEO' in frappe.get_roles(user) :			
# 			query_conditions = """(`tabReturn From Leave Statement`.owner in (SELECT user_id FROM tabEmployee WHERE region='{region}') or
# 			`tabReturn From Leave Statement`.employee in (SELECT name FROM tabEmployee WHERE  user_id in (select parent from tabUserRole where role ="Vice Presedint" ))
# 			)""" \
# 			.format(region=frappe.db.escape(region))

# 		elif u'Vice Presedint' in frappe.get_roles(user) :
# 			query_conditions = """(`tabReturn From Leave Statement`.owner in (SELECT user_id FROM tabEmployee WHERE region='{region}') or
# 			`tabReturn From Leave Statement`.employee in (SELECT name FROM tabEmployee WHERE  user_id in (select parent from tabUserRole where role ="Regional Director" ))
# 			)""" \
# 			.format(region=frappe.db.escape(region))

# 		elif u'Regional Director' in frappe.get_roles(user) :
# 			query_conditions = """(`tabReturn From Leave Statement`.owner in (SELECT user_id FROM tabEmployee WHERE region='{region}') or
# 				`tabReturn From Leave Statement`.employee in (SELECT name FROM tabEmployee WHERE region='{region}')
# 				)""" \
# 					.format(region=frappe.db.escape(region))
# 		elif u'Department Manager' in frappe.get_roles(user) :
			
# 			#return """`tabReturn From Leave Statement`.employee in  (SELECT name FROM tabEmployee WHERE  region_department='{region_department}' )""".format(region_department=frappe.db.escape(region_department))
# 			#query_conditions = """`tabReturn From Leave Statement`.employee in (SELECT name FROM tabEmployee WHERE  region_department in (SELECT name from tabRegion WHERE department_manager='{department_manager}')) and (`tabReturn From Leave Statement`.workflow_state in ('Created By Line Manager', 'Approved By Department Manager'))""".format(department_manager=employee.name)
# 			query_conditions = """`tabReturn From Leave Statement`.employee in (SELECT name FROM tabEmployee WHERE  region_department in (SELECT name from tabRegion WHERE department_manager='{department_manager}'))""".format(department_manager=employee.name)
# 		elif u'Line Manager' in frappe.get_roles(user):				
# 			#managed_regions = (i[0] for i in frappe.get_list("Region", {"line_manager": employee.name}, "name", as_list=1))
# 			query_conditions = """(`tabReturn From Leave Statement`.owner in (SELECT user_id FROM tabEmployee WHERE (region='{region}' and region_city='{region_city}' and region_department='{region_department}') or (region_department in (SELECT name from tabRegion WHERE line_manager='{line_manager}'))) or			
# 				`tabReturn From Leave Statement`.employee in (SELECT name FROM tabEmployee WHERE (region='{region}' and region_city='{region_city}' and region_department='{region_department}') or (region_department in (SELECT name from tabRegion WHERE line_manager='{line_manager}')))
# 				  )""" \
# 					.format(region=frappe.db.escape(region),region_city=frappe.db.escape(region_city),region_department=frappe.db.escape(region_department), line_manager=employee.name)

# 		if u'Employee' in frappe.get_roles(user):
# 			return  (query_conditions + " or " if  query_conditions else "") + """(`tabReturn From Leave Statement`.owner = '{user}' or `tabReturn From Leave Statement`.employee = '{employee}')""" \
# 				.format(user=frappe.db.escape(user), employee=frappe.db.escape(employee.name))
		
