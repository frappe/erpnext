# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.contacts.address_and_contact import (
	delete_contact_and_address,
	load_address_and_contact,
)
from frappe.model.document import Document


class Bank(Document):
	def onload(self):
		"""Load address and contacts in `__onload`"""
		load_address_and_contact(self)
		self.load_branches()

	def validate(self):
		self.validate_mandatory()
		self.sync_branches()
		self.items = []

	def on_trash(self):
		delete_contact_and_address("Bank", self.name)

	def validate_mandatory(self):
		if not self.bank_name:
			frappe.throw(_("Bank Name is mandatory"))

	def get_branches(self):
		return frappe.get_all("Bank Branch", "*", {"bank": self.name}, order_by="name")

	def load_branches(self):
		self.items = []
		for branch in self.get_branches():
			self.append("items",{
				"branch_name": branch.branch_name,
				"financial_system_code": branch.financial_system_code,
				"bank_branch": branch.name
			})

	def sync_branches(self):
		for item in self.items:
			if item.bank_branch:
				branch = frappe.get_doc("Bank Branch", item.bank_branch)
			else:
				branch = frappe.new_doc("Bank Branch")

			branch.update({
				"bank": self.name,
				"branch_name": str(item.branch_name).strip(),
				"financial_system_code": str(item.financial_system_code).strip()
			})
			branch.save(ignore_permissions=True)
