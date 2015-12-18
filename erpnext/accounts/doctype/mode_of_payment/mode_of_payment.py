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
		"""Error when Same organization is entered multiple times in accounts"""
		accounts_list = []
		for entry in self.accounts:
			accounts_list.append(entry.organization)

		if len(accounts_list)!= len(set(accounts_list)):
			frappe.throw(_("Same organization is entered more than once"))

	def validate_accounts(self):
		for entry in self.accounts:
			"""Error when organization of Ledger account doesn't match with organization Selected"""
			if frappe.db.get_value("Account", entry.default_account, "organization") != entry.organization:
				frappe.throw(_("Account does not match with organization"))
