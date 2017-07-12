# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import flt
from erpnext.hr.utils import set_employee_name

class ExpenseReceipt(Document):
	def validate(self):
		self.validate_tax_amount()
		set_employee_name(self)


	def validate_tax_amount(self):
		if flt(self.tax_amount) > flt(self.claim_amount):
			frappe.throw(_("Tax Amount cannot be greater than Claim Amount."))