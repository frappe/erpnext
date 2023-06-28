# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
from frappe.utils import flt


class ProformaInvoiceNew(Document):
	# def __init__(self, *args, **kwargs):
	# 		super(SalesOrder, self).__init__(*args, **kwargs)

	# def validate(self):
	# 	# super(ProformaInvoice, self).validate()
	# 	for d in self.items:
	# 		print(d.qty)

	def before_save(self):
		# super(ProformaInvoice, self).validate()
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
