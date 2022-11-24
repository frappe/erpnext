# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class EInvoiceSettings(Document):
	def validate(self):
		if self.enable and not self.credentials:
			frappe.throw(_("You must add atleast one credentials to be able to use E Invoicing."))

		prev_doc = self.get_doc_before_save()
		if prev_doc.client_secret != self.client_secret or prev_doc.client_id != self.client_id:
			self.auth_token = None
			self.token_expiry = None
