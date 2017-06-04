# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class JobAssignmentReport(Document):
	pass

def get_permission_query_conditions(user):
	if not user: user = frappe.session.user
	user_roles = frappe.get_roles(user)
	# print 'all|',all(k in user_roles for k in (u'System Manager', u'Accounts User'))

	if u'System Manager' in user_roles:
		return None

	if u'Department Manager' in user_roles:
		employee = frappe.get_doc('Employee', {'user_id': user})
		department = employee.department
		return """(owner='{user}' OR employee IN (SELECT name FROM tabEmployee WHERE department='{department}'))""" \
			.format(user=frappe.db.escape(user), department=frappe.db.escape(department))

	if u'Employee' in user_roles:
		employee_doc = frappe.get_doc('Employee', {'user_id': user})
		return """(owner='{user}' OR employee='{employee}')"""\
			.format(user=frappe.db.escape(user), employee=frappe.db.escape(employee_doc.employee))
