# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class VechicleRequestExtension(Document):
	def on_submit(self):
		doc = frappe.get_doc("Vehicle Request", self.vehicle_request)
		doc.to_date = self.new_to_date
		doc.reason_for_extension = self.reason_for_extension
		doc.save(ignore_permissions=True)