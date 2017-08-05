# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
import re

class EmployeeChangeIBAN(Document):
	def validate(self):
		self.validate_IBAN()

	def validate_IBAN(self):		
		#pattern = r"^[a-zA-Z]{2}[0-9]{2}[a-zA-Z0-9]{4}[0-9]{7}([a-zA-Z0-9]?){0,16}$"
		pattern = r'(^(SA.{22})$)'
		if not re.match(pattern, self.new_iban):
			frappe.throw(_("Invalid IBAN number, IBAN should be like SAxxxxxxxxxxxxxxxxxxxxxx."))


	def before_submit(self):
		employee = frappe.get_doc("Employee", self.employee)
		employee.db_set("iban", self.new_iban)
		employee.db_set("bank_name", self.new_bank)



def get_permission_query_conditions(user):
	pass
def get_permission_query_conditions22(user):
	return ""
	if not user: user = frappe.session.user
	
	employees = frappe.get_list("Employee", fields=["name"], filters={'user_id': user}, ignore_permissions=True)
	if employees:
		employee = frappe.get_doc('Employee', {'name': employees[0].name})
		
		if u'Change IBAN Approver' in frappe.get_roles(user) :			
			return ""
		elif u'Employee' in frappe.get_roles(user):
			return """(`Employee Change IBAN`.owner = '{user}' or `Employee Change IBAN`.employee = '{employee}')""" \
				.format(user=frappe.db.escape(user), employee=frappe.db.escape(employee.name))
		else:
			return None


