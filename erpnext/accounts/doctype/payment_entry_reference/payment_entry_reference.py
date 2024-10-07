# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class PaymentEntryReference(Document):
	@property
	def payment_request_outstanding(self):
		if not self.payment_request:
			return

		return frappe.db.get_value("Payment Request", self.payment_request, "outstanding_amount")
