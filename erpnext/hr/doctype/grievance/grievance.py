# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import throw, _
from erpnext.setup.doctype.sms_settings.sms_settings import send_sms
from frappe.utils import cint, cstr, date_diff, flt, formatdate, getdate, get_link_to_form, \
	comma_or, get_fullname
	
class Grievance(Document):
	def validate(self):	
		if self.send_to =="المدير المباشر" and not self.reports_to : 
			frappe.throw(_("Please Select Direct manager"))	
		if self.get("__islocal"):
			if self.send_to =="المدير المباشر":
				self.notify_leave_approver()
			if self.send_to =="المدير التنفيذي":
				self.notify_exec_manager()
			if self.send_to =="المدير المباشر و التنفيذي":
				self.notify_exec_manager()
				self.notify_leave_approver()
			
	def before_submit(self):
		if self.status == "New":
			frappe.throw(_("Please Change The Status of the document to Approved or Rejected"))

		if self.reports_to != frappe.session.user:
			frappe.throw(_("You are not The Direct Manger "),self.reports_to)
		
	def on_submit(self):
		if self.status == "Open":
			frappe.throw(_("Only Doc with status 'Approved' can be submitted"))
		self.notify_employee(self.status)


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
			message = (_("Grievance") + ": %s") % (name)+"<br>"
			if hasattr(self, 'workflow_state'):
				message += "Workflow State: {workflow_state}".format(workflow_state=self.workflow_state)+"<br>"
			message += (_("Employee") + ": %s") % (employee_name)+"<br>"
			message += (_("Status") + ": %s") % (self.status)+"<br>"
			message += (_("Date") + ": %s") % (self.date)+"<br>"
			message += (_("Subject") + ": %s") % (self.subject)+"<br>"
			message += (_("Reason") + ": %s") % (self.reason)+"<br>"
			return message	
		try:	
			self.notify({
				# for post in messages
				"message": _get_message(url=True),
				"message_to": employee.prefered_email,
				"subject": (_("Grievance") + ": %s - %s") % (self.name, _(status))
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
			message = (_("Grievance") + ": %s") % (name)+"<br>"
			if hasattr(self, 'workflow_state'):
				message += "Workflow State: {workflow_state}".format(workflow_state=self.workflow_state)+"<br>"
			message += (_("Employee") + ": %s") % (employee_name)+"<br>"
			message += (_("Status") + ": %s") % (self.status)+"<br>"
			message += (_("Date") + ": %s") % (self.date)+"<br>"
			message += (_("Subject") + ": %s") % (self.subject)+"<br>"
			message += (_("Reason") + ": %s") % (self.reason)+"<br>"
			return message
		
		self.notify({
			# for post in messages
			"message": _get_message(url=True),
			"message_to": self.reports_to,

			# for email
			"subject": (_("Grievance") + ": %s - " + _("Employee") + ": %s") % (self.name, cstr(employee.employee_name))
		})
		
	def notify_exec_manager(self):
		employee = frappe.get_doc("Employee", self.employee)
		super_emp_list = []
		supers =frappe.get_all('UserRole', fields = ["parent"], filters={'role' : 'Executive Manager'})
		
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
			message = (_("Grievance") + ": %s") % (name)+"<br>"
			if hasattr(self, 'workflow_state'):
				message += "Workflow State: {workflow_state}".format(workflow_state=self.workflow_state)+"<br>"
			message += (_("Employee") + ": %s") % (employee_name)+"<br>"
			message += (_("Status") + ": %s") % (self.status)+"<br>"
			message += (_("Date") + ": %s") % (self.date)+"<br>"
			message += (_("Subject") + ": %s") % (self.subject)+"<br>"
			message += (_("Reason") + ": %s") % (self.reason)+"<br>"
			return message
			
		def _get_sms(url=False):
			name = self.name
			employee_name = cstr(employee.employee_name)
			message = (_("%s") % (name))
			if hasattr(self, 'workflow_state'):
				message += "{workflow_state}".format(workflow_state=self.workflow_state)+"\n"
			message += (_("%s") % (employee_name))+"\n"
			message += (_("%s") % (self.leave_type))+"\n"
			message += (_("%s") % (self.from_date))+"\n"
			return message
		
		cells = []
		emp_result =frappe.get_all('Employee', fields = ["cell_number"], filters = [["user_id", "in", super_emp_list]])
		self.description = str(super_emp_list)
		for emp in emp_result:
			cells.append(emp.cell_number)
			 
		if emp_result:
			send_sms(cells, cstr(_get_sms(url=False)))
		 
		self.description = str(employee.employee_name)
		for s in super_emp_list:
			self.notify({
				# for post in messages
				"message": _get_message(url=True),
				"message_to": s,
				# for email
				"subject": (_("Grievance") + ": %s - " + _("Employee") + ": %s") % (self.name, cstr(employee.employee_name))
			})

	def notify(self, args):
		args = frappe._dict(args)
		from frappe.desk.page.chat.chat import post
		post(**{"txt": args.message, "contact": args.message_to, "subject": args.subject,
			"notify": cint(1)})
