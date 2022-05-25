# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document


class PaymentLedgerEntry(Document):
	def validate_account(self):
		valid_account = frappe.db.get_list(
			"Account",
			"name",
			filters={"name": self.account, "account_type": self.account_type, "company": self.company},
			ignore_permissions=True,
		)
		if not valid_account:
			frappe.throw(_("{0} account is not of type {1}").format(self.account, self.account_type))

	def validate(self):
		self.validate_account()
