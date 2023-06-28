# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
from frappe.utils import flt


class ProformaInvoice(Document):
	def before_save(self):
		total_rate = 0
		total_qty = 0
		total = 0
		for d in self.items:
			total_qty += flt(d.proforma_invoice_qty)
			total_rate += flt(d.rate)
			total += flt(d.proforma_invoice_qty) * flt(d.rate)
			d.amount = flt(d.proforma_invoice_qty) * flt(d.rate)

		self.total_qty = total_qty
		self.base_total = total
		self.base_net_total = total
