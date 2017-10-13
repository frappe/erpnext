# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class BankTransactionType(Document):
	def autoname(self):
		self.name = self.bank_statement_format.strip() + '-' + self.transaction_type.strip() + '-' + self.debit_or_credit
