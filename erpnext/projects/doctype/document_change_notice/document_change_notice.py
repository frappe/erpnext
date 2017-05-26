# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

@frappe.whitelist()
def get_amended_from(doctype, name):
	if frappe.get_meta(doctype).has_field("amended_from"):
		return {'amended_from': frappe.get_value(doctype, name, "amended_from")}
	else:
		return None


class DocumentChangeNotice(Document):
	def validate(self):

		self.validate_employee()
		self.validate_approval()
		self.validate_status()
		self.flags.ignore_links = True
		
	def validate_employee(self):
		# Check to see if the employee matches the department
		emp_dept = frappe.get_value("Employee", self.employee, "department")
		if emp_dept != self.emp_department:
			frappe.throw(_("Initiating employee must be part of the initiating department"))
			
	def validate_approval(self):
		# Check to see if any departments do not have the correct manager
		for dept in self.approvals:
			manager = frappe.get_value("Department", dept.department, "manager")
			if manager != dept.manager:
				frappe.throw(_("Incorrect department manager selected"))
		
	def check_department_status(self):
		# Check to make sure approvals have signature and date
		for dept in self.approvals:
			if dept.status != 'Pending':
				if not (dept.review_date and dept.signature):
					frappe.throw(_("Approval must be signed and dated"))
					

	
	def validate_status(self):
		# Check to see if any departments do not have the correct manager
		status = 1
		for dept in self.approvals:
			if dept.status == 'Pending':
				status = min(status, 0)
			elif dept.status == 'Approved':
				status = min(status, 1)
			elif dept.status == 'Revisions Needed':
				status = 2
				break
			elif dept.status == 'Rejected':
				status = 3
				break
				
		if self.docstatus == 0:
			self.status = 'Pending'
			for dept in self.approvals:
				dept.status = 'Pending'
		elif status == 0 and self.docstatus == 1:
			self.status = 'Under Review'
		elif status == 1 and self.docstatus == 1:
			self.status = 'Approved'
		elif status == 2 and self.docstatus == 1:
			self.status = 'Needs Revisions'
			self.remove_todos()
		elif status == 3 or self.docstatus == 2:
			self.status = 'Rejected'
			self.remove_todos()
		else:
			self.status = 'Pending'
			
	def on_submit(self):
		self.create_todos()
		frappe.clear_cache()
	
	def before_update_after_submit(self):
		self.flags.ignore_links = True
		
	def validate_update_after_submit(self):
		
		self.check_department_status()
		self.validate_status()
		frappe.clear_cache()
		
	def create_todos(self):
		name = self.name
		user =  frappe.get_value("Employee", self.employee, "user_id")
		for dept in self.approvals: 
			manager =  frappe.get_value("Employee", dept.manager, "user_id")
			mydict = dict(doctype='ToDo', description=name + ' Review', assigned_by=user, 
				owner=manager, reference_type='Document Change Notice', reference_name=name)
			todo = frappe.get_doc(mydict).insert()
	
	def remove_todos(self):
		name = self.name
		todo = frappe.get_all('ToDo',filters={'reference_name':name, 'description':name + ' Review'},
			fields=["name"])
		for rem_td in todo:
			frappe.delete_doc("ToDo", rem_td.name, ignore_permissions=True)
	

