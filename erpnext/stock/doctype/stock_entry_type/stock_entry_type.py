# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


# import frappe
from frappe.model.document import Document


class StockEntryType(Document):
	def validate(self):
		if self.add_to_transit and self.purpose != "Material Transfer":
			self.add_to_transit = 0
