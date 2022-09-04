# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document


class CashFlowMapping(Document):
	def validate(self):
		self.validate_checked_options()

	def validate_checked_options(self):
		checked_fields = [
			d for d in self.meta.fields if d.fieldtype == "Check" and self.get(d.fieldname) == 1
		]
		if len(checked_fields) > 1:
			frappe.throw(
				frappe._("You can only select a maximum of one option from the list of check boxes."),
				title="Error",
			)
