# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import flt

from frappe import msgprint, _

from frappe.model.document import Document

class PaymentReconciliation(Document):
	def get_unreconciled_entries(self):
		self.set('payment_reconciliation_payment', [])
		jve = self.get_jv_entries()
		self.create_payment_reconciliation_payment(jve)

