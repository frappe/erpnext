# -*- coding: utf-8 -*-
# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class VoidedCheck(Document):
	def validate(self):		
		if self.docstatus == 0:
			self.verificate_bank_check()
			if self.created_by == None:
				self.created_by = frappe.session.user
	
	def verificate_bank_check(self):
		bank_transaction = frappe.get_all("Bank Transactions", "*", filters = {"no_bank_check": self.no_bank_check, "bank_account": self.bank_account})
		voided_check = frappe.get_all("Voided Check", "*", filters = {"no_bank_check": self.no_bank_check, "bank_account": self.bank_account})
		payment_entry = frappe.get_all("Payment Entry", "*", filters = {"reference_no": self.no_bank_check, "bank_account": self.bank_account})

		if len(bank_transaction) > 0:
			frappe.throw(_("This bank check number is assigned to bank transaction number {}".format(bank_transaction[0].name)))

		if len(voided_check) > 0 and voided_check[0].name != self.name:
			frappe.throw(_("This bank check number is assigned to voided check number {}".format(voided_check[0].name)))
		
		if len(payment_entry) > 0:
			frappe.throw(_("This bank check number is assigned to payment entry number {}".format(payment_entry[0].name)))
