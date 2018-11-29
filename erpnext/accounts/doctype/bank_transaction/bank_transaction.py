# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

class BankTransaction(Document):
	def after_insert(self):
		self.unallocated_amount = abs(flt(self.credit) - flt(self.debit))

	def on_update_after_submit(self):
		linked_payments = [x.payment_entry for x in self.payment_entries]

		if linked_payments:
			allocated_amount = frappe.get_all("Payment Entry", filters=[["name", "in", linked_payments]], fields=["sum(paid_amount) as total"])

			frappe.db.set_value(self.doctype, self.name, "allocated_amount", flt(allocated_amount[0].total))
			frappe.db.set_value(self.doctype, self.name, "unallocated_amount", abs(flt(self.credit) - flt(self.debit)) - flt(allocated_amount[0].total))
		
		else:
			frappe.db.set_value(self.doctype, self.name, "allocated_amount", 0)
			frappe.db.set_value(self.doctype, self.name, "unallocated_amount", abs(flt(self.credit) - flt(self.debit)))
	
		self.reload()