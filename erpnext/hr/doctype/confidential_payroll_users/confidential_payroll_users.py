# -*- coding: utf-8 -*-
# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class ConfidentialPayrollUsers(Document):
	def validate(self):
		confidential = frappe.get_all("Confidential Payroll Users", ["*"])

		if len(confidential) > 0:
			if confidential[0].name != self.name:
				frappe.throw(_("Only one registration is allowed."))
