# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from erpnext.loan_management.doctype.loan_security_price.loan_security_price import update_loan_security_price

class ProcessLoanSecurityPrice(Document):
	def validate(self):
		if self.from_time > self.to_time:
			frappe.throw(_("From time must be lesser than Upto time."))


@frappe.whitelist()
def update_loan_security(from_timestamp, to_timestamp, loan_security_type=None):
	update_loan_security_price(from_timestamp=from_timestamp, to_timestamp=to_timestamp,
			loan_security_type=loan_security_type, from_background_job=0)