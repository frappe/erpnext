# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class LetterofCredit(Document):
	def validate(self):
		self.set_title()

	def set_title(self):
		if self.reference_text:
			self.title = "{0}{1} - {2}".format(self.naming_prefix, self.letter_of_credit_number, self.reference_text)
		else:
			self.title = "{0}{1}".format(self.naming_prefix, self.letter_of_credit_number)

	def get_default_letter_of_credit_account(self):
		default_letter_of_credit_account = frappe.get_cached_value('Company',
			{"company_name": self.company},  "default_letter_of_credit_account")

		if not default_letter_of_credit_account:
			frappe.throw(_("Please set Default Letter of Credit Account in Company {0}")
				.format(self.company))

		return default_letter_of_credit_account