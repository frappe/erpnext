# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class LetterofCredit(Document):
	def get_default_letter_of_credit_account(self):
		default_letter_of_credit_account = frappe.get_cached_value('Company',
			{"company_name": self.company},  "default_letter_of_credit_account")

		if not default_letter_of_credit_account:
			frappe.throw(_("Please set Default Letter of Credit Account in Company {0}")
				.format(self.company))

		return default_letter_of_credit_account
