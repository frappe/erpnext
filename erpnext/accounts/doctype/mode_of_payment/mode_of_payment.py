# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.model.document import Document
from frappe import _

class ModeofPayment(Document):
	def validate(self):
		self.validate_accounts()
		self.validate_repeating_companies()
	
	def validate_repeating_companies(self):
		"""Error when Same Company is entered multiple times in accounts"""
		accounts_list = []
		for entry in self.accounts:
			accounts_list.append(entry.company)

		if len(accounts_list)!= len(set(accounts_list)):
			frappe.throw(_("Same Company is entered more than once"))

	def validate_accounts(self):
		for entry in self.accounts:
			"""Error when Company of Ledger account doesn't match with Company Selected"""
			account = frappe.get_list("Account",
				fields=["name"],
				filters = {
					"company": entry.company,
					"name": entry.default_account
				})
			try:
				account[0].name
			except IndexError:
				frappe.throw(_("Account does not match with Company"))
