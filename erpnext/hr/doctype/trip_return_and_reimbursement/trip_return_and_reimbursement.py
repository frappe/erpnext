# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class TripReturnandReimbursement(Document):
	def validate(self):
		self.validate_emp()
		if self.workflow_state:
			if "Rejected" in self.workflow_state:
				self.docstatus = 1
				self.docstatus = 2

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

