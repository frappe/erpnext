# -*- coding: utf-8 -*-
# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class CancelBankChecks(Document):
	def validate(self):
		if self.docstatus == 1:
			self.delete_journal_entry()
	
	def delete_journal_entry(self):
		journals = frappe.get_all("Journal Entry", ["*"], filters = {"bank_transaction": self.check})

		test = ""

		# for journal in journals:
		# 	frappe.delete_doc("Journal Entry", journal.name)