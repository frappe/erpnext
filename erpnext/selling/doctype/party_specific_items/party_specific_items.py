# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

class PartySpecificItems(Document):
	def validate(self):
		exists = frappe.db.exists({
			'doctype': 'Party Specific Items',
			'party_type': self.party_type,
			'party': self.party,
			'restrict_based_on': self.restrict_based_on,
			'based_on': self.based_on,
		})
		if exists:
			frappe.throw(_(f"This item filter has already been applied for the {self.party_type}"))
