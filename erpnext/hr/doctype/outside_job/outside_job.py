# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _, throw
from frappe.model.document import Document
from frappe.utils.data import getdate
from erpsystem import _send_email
from frappe.utils import cint, cstr, date_diff, flt, formatdate, getdate, get_link_to_form

class OutsideJob(Document):

	def validate(self):
		self.validate_type()
		self.validate_hour_count()
		user_roles = frappe.get_roles()		
		if not "HR Manager" in user_roles:
			if self.reports_to != frappe.session.user and self.docstatus ==1:
				frappe.throw(_("You are not The Direct Manger"))
			if self.reports_to != frappe.session.user and self.docstatus ==0 and self.workflow_state != "Pending":
				self.workflow_state = "Pending"
				frappe.throw(_("You are not The Direct Manger"))
		if self.get("__islocal"):
			self.notify_leave_approver()
			
	def before_submit(self):
		user_roles = frappe.get_roles()		
		if not "HR Manager" in user_roles:
			if self.reports_to != frappe.session.user and self.docstatus ==0 and self.workflow_state != "Pending":
				frappe.throw(_("You are not The Direct Manger"))
			if self.reports_to != frappe.session.user:
				frappe.throw(_("You are not The Direct Manger"))
		if self.status == "Open":
			frappe.throw(_("Please Change The Status of the document to Approved or Rejected"))			
		self.notify_employee(self.status)
			
	def validate_hour_count(self):
		if self.hourly_hour_count > 40:
			frappe.throw("Hour Count cannot be greater than 40 hours")

	def validate_type(self):
		if self.type == 'Hourly':
			self.validate_hourly()
		elif self.type == 'Daily':
			self.validate_daily()

	def validate_hourly(self):
		if not self.hourly_date or not self.hourly_date:
			throw(_('Date field required'))
		if not self.hourly_hour_count:
			throw(_('Hour Count field requierd'))

	def validate_daily(self):
		if not self.daily_from_date or not self.daily_from_date:
			throw(_('From Date field required'))

		if not self.daily_to_date or not self.daily_to_date:
			throw(_('To Date field required'))

		if 	getdate(self.daily_from_date) > getdate(self.daily_to_date):
			throw(_('To Date field must be greater than From Date field'))

	def on_submit(self):	
		self.insert_expense_claim()
		self.notify_hr_manager()

	
	def on_update_after_submit(self):
		self.notify_hr_manager()
		self.notify_employee(self.status)



	def get_department_managers(self):
		department = self.get_department()
		query = """select user.* from tabEmployee employee
							Inner Join tabUserRole role on employee.user_id = role.parent
							Inner Join tabUser user on employee.user_id = user.name
							where role.role = 'Department Manager' and employee.department='{department}'"""

		department_managers = frappe.db.sql(query.format(department=frappe.db.escape(department)), as_dict=1)
		return department_managers

	def get_department(self):
		employee = frappe.get_doc('Employee', {'user_id': self.owner})
		department = employee.department
		return department

	def get_users_in_role(self, role_name):
		query = """select user.* from tabUser user
	    							Inner Join tabUserRole role on user.name = role.parent
	    							where role.role = '{role}'"""
		users = frappe.db.sql(query.format(role=frappe.db.escape(role_name)), as_dict=1)
		return users

	def get_user(self, user):
		return frappe.get_doc('User', {'name': user})

	def get_employee(self, user):
		return frappe.get_doc('Employee', {'user_id': user})

	def get_employee_from_session (self):
		if self.get('__islocal'):
			employee = frappe.get_list("Employee", fields=["name","employee_name"]
			, filters = {"user_id":frappe.session.user},ignore_permissions=True)
			if employee:
				self.employee = employee[0].name
				self.employee_name = employee[0].employee_name

	def get_holidays_for_employee(self, start_date, end_date):
		holidays = frappe.db.sql("""select t1.holiday_date
			from `tabHoliday` t1, tabEmployee t2
			where t1.parent = t2.holiday_list and t2.name = %s
			and t1.holiday_date between %s and %s""",
			(self.employee, start_date, end_date))

		if not holidays:
			holidays = frappe.db.sql("""select t1.holiday_date
				from `tabHoliday` t1, `tabHoliday List` t2
				where t1.parent = t2.name and t2.is_default = 1
				and t2.fiscal_year = %s
				and t1.holiday_date between %s and %s""",
				(self.fiscal_year, start_date, end_date))

		holidays = [cstr(i[0]) for i in holidays]
		return holidays
	def diff_month(self,d1, d2):
	    return (d1.year - d2.year)*12 + d1.month - d2.month
	def insert_expense_claim(self):
		#fix it man !!!
		#outside_cost = (main_payment*1.55*total_hours)
		#transportaion=(transportation_costs/30)*days_of_outside
		#outside_total = outside_cost+transportaion
		cost = 0
		user = frappe.session.user
		employee = frappe.get_doc('Employee', {'name': self.employee})
		grade = frappe.get_doc('Grade', {'name': employee.grade})
		

		
		
		if employee.attendance_hours :
			attendance_horus = frappe.get_doc('Attendance Hours', {'name': employee.attendance_hours})#attendance_hours
		else:
			def_att_h = frappe.db.get_single_value("HR Settings", "attendance_hours")
			attendance_horus = frappe.get_doc('Attendance Hours', {'name': def_att_h})#attendance_hours
			
		st_name = frappe.db.sql("""select parent,base from `tabSalary Structure Employee`
			where employee=%s order by modified desc limit 1""",self.employee,as_dict=True)
		if st_name:
			struct = frappe.db.sql("""select name from `tabSalary Structure`where name=%s and is_active = 'Yes' limit 1""",st_name[0].parent)
			if not struct:
				self.salary_structure = None
				frappe.throw(_("No active or default Salary Structure found for employee {0} for the given dates")
					.format(self.employee), title=_('Salary Structure Missing'))

		main_payment = st_name[0].base
		main_salary_structur = frappe.get_doc("Salary Structure",st_name[0].parent)
		from erpnext.hr.doctype.salary_structure.salary_structure import make_salary_slip
		salar_slip = frappe.new_doc("Salary Slip")
		make_salary_slip(main_salary_structur.name,salar_slip, employee = employee.name)
		transportation_costs = grade.transportation_costs
		total_hours = 0
		total_days = 0
		#overtime_hours
		if self.type == "Hourly":
			total_hours = flt(self.hourly_hour_count)
			total_days =1
		elif self.type == "Daily":
			total_days = date_diff(self.daily_to_date, self.daily_from_date) + 1
			total_hours = flt(self.hourly_hour_count)*attendance_horus.attendance_hours

		outside_cost = (salar_slip.net_pay/30/flt(attendance_horus.attendance_hours))*total_hours
		outside_total = outside_cost

		fields = {
		_('Total'):outside_total,
		}
		expenses=[]# other_costs training_cost accommodation_cost living_costs transportation_costs
		for key,value in fields.iteritems():
			if value >0:
				expenses.append( {
				"claim_amount": value,
				"expense_type": "خارج الدوام",
				"sanctioned_amount":  value,
				"description":key,
				"parentfield": "expenses"
				})
		expense_claim = frappe.get_doc({
		"doctype": "Expense Claim",
		"naming_series": "EXP",
		"exp_approver": self.reports_to,
		"employee": self.employee,
		"expenses":expenses,
		"reference_type":"Outside Job",
		"reference_name":self.name,
		"remark":self.notes
		})
		print expense_claim
		expense_claim.save(ignore_permissions=True)

	def notify_employee(self, status):
		employee = frappe.get_doc("Employee", self.employee)
		if not employee.user_id:
			return

		def _get_message(url=False):
			name = self.name
			employee_name = cstr(employee.employee_name)
			if url:
				name = get_link_to_form(self.doctype, self.name)
				employee_name = get_link_to_form("Employee", self.employee, label=employee_name)
			message = (_("Outside Job") + ": %s") % (name)+"<br>"
			if hasattr(self, 'workflow_state'):
				message += "Workflow State: {workflow_state}".format(workflow_state=self.workflow_state)+"<br>"
			message += (_("Employee") + ": %s") % (employee_name)+"<br>"
			message += (_("Status") + ": %s") % (self.status)+"<br>"
			message += (_("Date") + ": %s") % (self.hourly_date)+"<br>"
			message += (_("Subject") + ": %s") % (self.notes)+"<br>"
			return message	
		try:	
			self.notify({
				# for post in messages
				"message": _get_message(url=True),
				"message_to": employee.prefered_email,
				"subject": (_("Outside Job") + ": %s - %s") % (self.name, _(status))
			})
		except:
			frappe.throw("could not send")
		
	def notify_leave_approver(self):
		employee = frappe.get_doc("Employee", self.employee)

		def _get_message(url=False):
			name = self.name
			employee_name = cstr(employee.employee_name)
			if url:
				name = get_link_to_form(self.doctype, self.name)
				employee_name = get_link_to_form("Employee", self.employee, label=employee_name)
			message = (_("Outside Job") + ": %s") % (name)+"<br>"
			if hasattr(self, 'workflow_state'):
				message += "Workflow State: {workflow_state}".format(workflow_state=self.workflow_state)+"<br>"
			message += (_("Employee") + ": %s") % (employee_name)+"<br>"
			message += (_("Status") + ": %s") % (self.status)+"<br>"
			message += (_("Date") + ": %s") % (self.hourly_date)+"<br>"
			message += (_("Subject") + ": %s") % (self.notes)+"<br>"
			return message	
		
		self.notify({
			# for post in messages
			"message": _get_message(url=True),
			"message_to": self.reports_to,

			# for email
			"subject": (_("Outside Job") + ": %s - " + _("Employee") + ": %s") % (self.name, cstr(employee.employee_name))
		})
		
	def notify_hr_manager(self):
		employee = frappe.get_doc("Employee", self.employee)
		super_emp_list = []
		supers =frappe.get_all('UserRole', fields = ["parent"], filters={'role' : 'HR Manager'})
		
		for s in supers:
			super_emp_list.append(s.parent)
		try:super_emp_list.remove('Administrator')
		except : pass
		
		def _get_message(url=False):
			name = self.name
			employee_name = cstr(employee.employee_name)
			if url:
				name = get_link_to_form(self.doctype, self.name)
				employee_name = get_link_to_form("Employee", self.employee, label=employee_name)
			message = (_("Outside Job") + ": %s") % (name)+"<br>"
			if hasattr(self, 'workflow_state'):
				message += "Workflow State: {workflow_state}".format(workflow_state=self.workflow_state)+"<br>"
			message += (_("Employee") + ": %s") % (employee_name)+"<br>"
			message += (_("Status") + ": %s") % (self.status)+"<br>"
			message += (_("Date") + ": %s") % (self.hourly_date)+"<br>"
			message += (_("Subject") + ": %s") % (self.notes)+"<br>"
			return message	
		
		cells = []
		emp_result =frappe.get_all('Employee', fields = ["cell_number"], filters = [["user_id", "in", super_emp_list]])
		self.description = str(super_emp_list)
		for emp in emp_result:
			cells.append(emp.cell_number)
			  
		self.description = str(employee.employee_name)
		for s in super_emp_list:
			self.notify({
				# for post in messages
				"message": _get_message(url=True),
				"message_to": s,
				# for email
				"subject": (_("Outside Job") + ": %s - " + _("Employee") + ": %s") % (self.name, cstr(employee.employee_name))
			})

	def notify(self, args):
		args = frappe._dict(args)
		from frappe.desk.page.chat.chat import post
		post(**{"txt": args.message, "contact": args.message_to, "subject": args.subject,
			"notify": cint(1)})

def get_permission_query_conditions(user):
	if not user: user = frappe.session.user
	user_roles = frappe.get_roles(user)
	# print 'all|',all(k in user_roles for k in (u'System Manager', u'Accounts User'))

	if u'System Manager' in user_roles:
		return None

	if u'Department Manager' in user_roles:
		employee = frappe.get_doc('Employee', {'user_id': user})
		department = employee.department
		return """(owner='{user}' OR employee_name IN (SELECT name FROM tabEmployee WHERE department='{department}'))""" \
			.format(user=frappe.db.escape(user), department=frappe.db.escape(department))

	if u'Employee' in user_roles:
		employee_doc = frappe.get_doc('Employee', {'user_id': user})
		return """(owner='{user}' OR employee_name='{employee}')"""\
			.format(user=frappe.db.escape(user), employee=frappe.db.escape(employee_doc.employee_name))

def emp_query(doctype, txt, searchfield, start, page_len, filters):
	user = frappe.session.user
	user_roles = frappe.get_roles(user)
	employee = frappe.get_doc('Employee',{'user_id' : user} )
	department = "" if employee.department is None else employee.department
	if u'Department Manager' in user_roles:
		return frappe.db.sql("""select name,employee_name from `tabEmployee` where department = '{department}' and name != '{employee}'""".
		format(department=frappe.db.escape(department),employee=frappe.db.escape(employee.name)))
	else:
		if u'Employee' in user_roles:
			return frappe.db.sql("""select name,employee_name from `tabEmployee` where  name = '{employee}'""".
			format(employee=frappe.db.escape(employee.name)))


@frappe.whitelist()
def insert_expense_claim_report(date,designation,amount,reson=None):
		cost = 0
		user = frappe.session.user
		employee_list =frappe.get_all('Employee', fields = ["*"], filters = {"designation":designation})

		if employee_list:
			for employee in employee_list:
				if employee.attendance_hours :
					attendance_horus = frappe.get_doc('Attendance Hours', {'name': employee.attendance_hours})#attendance_hours
				else:
					def_att_h = frappe.db.get_single_value("HR Settings", "attendance_hours")
					attendance_horus = frappe.get_doc('Attendance Hours', {'name': def_att_h})#attendance_hours
					
				st_name = frappe.db.sql("""select parent,base from `tabSalary Structure Employee`
					where employee=%s order by modified desc limit 1""",employee.name,as_dict=True)
				if st_name:
					struct = frappe.db.sql("""select name from `tabSalary Structure`where name=%s and is_active = 'Yes' limit 1""",st_name[0].parent)
					if not struct:
						frappe.throw(_("No active or default Salary Structure found for employee {0} for the given dates")
							.format(employee.name), title=_('Salary Structure Missing'))

				main_payment = st_name[0].base
				main_salary_structur = frappe.get_doc("Salary Structure",st_name[0].parent)
				from erpnext.hr.doctype.salary_structure.salary_structure import make_salary_slip
				salar_slip = frappe.new_doc("Salary Slip")
				make_salary_slip(main_salary_structur.name,salar_slip, employee = employee.name)
				transportation_costs = 0
				total_hours = 0
				total_days = 0
				#overtime_hours
				if amount :
					outside_cost = amount
				#~ elif value:
					#~ outside_cost = (salar_slip.net_pay/30/flt(attendance_horus.attendance_hours))*total_hours*flt(value)
				
				outside_total = outside_cost

				fields = {
				_('Total'):outside_total,
				}
				expenses=[]# other_costs training_cost accommodation_cost living_costs transportation_costs
				for key,value in fields.iteritems():
					if value >0:
						expenses.append( {
						"claim_amount": value,
						"expense_type": "خارج الدوام",
						"sanctioned_amount":  value,
						"description":key,
						"parentfield": "expenses"
						})
				expense_claim = frappe.get_doc({
				"doctype": "Expense Claim",
				"naming_series": "EXP",
				"exp_approver": frappe.session.user,
				"employee": employee.name,
				"expenses":expenses,
				#~ "reference_type":"Outside Job",
				#~ "reference_name":self.name,
				"remark":reson
				})
				print expense_claim
				expense_claim.save(ignore_permissions=True)
				frappe.msgprint("Creted")
		else:
			frappe.msgprint("No Data")

