# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class SubcontractingReceipt(Document):
	def validate(self):
		self.validate_subcontracting_order()

	def validate_subcontracting_order(self):
		sco = frappe.get_doc("Subcontracting Order", self.get("subcontracting_order"))

		if sco.docstatus != 1:
			frappe.throw(_(f"Please submit Subcontracting Order {sco.name} before proceeding."))

