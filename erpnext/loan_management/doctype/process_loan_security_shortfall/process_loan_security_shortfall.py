# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import get_datetime
from frappe import _
from frappe.model.document import Document
from erpnext.loan_management.doctype.loan_security_shortfall.loan_security_shortfall import check_for_ltv_shortfall

class ProcessLoanSecurityShortfall(Document):
	def onload(self):
		self.set_onload('update_time', get_datetime())

	def on_submit(self):
		check_for_ltv_shortfall(process_loan_security_shortfall = self.name)
