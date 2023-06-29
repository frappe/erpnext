# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt

# from erpnext.selling.doctype.sales_order.sales_order import SalesOrder


class ProformaInvoice(Document):

	# def __init__(self, *args, **kwargs):
	# 	super(ProformaInvoice, self).__init__(*args, **kwargs)

	def before_save(self):
		total_rate = 0
		total_qty = 0
		total = 0

		for d in self.items:
			total_qty += flt(d.qty)
			total_rate += flt(d.rate)
			total += flt(d.qty) * flt(d.rate)
			d.amount = flt(d.qty) * flt(d.rate)

		self.total_qty = total_qty
		self.base_total = total
		# self.base_net_total = total
		so_list = frappe.db.get_all(
			"Sales Order Item",
			filters={"parent": self.sales_order_name},
			fields=["qty", "rate", "item_code"],
			as_list=True,
		)

	def on_submit(self):
		for d in self.items:
			so_list = frappe.db.get_all(
				"Sales Order Item",
				filters={"parent": self.sales_order_name, "name": d.name},
				fields=["qty", "rate", "item_code"],
			)
			print(so_list)
		# so_qty = frappe.db.get_value("Sales Order Item",self.sales_order_name,[""],as_dict = 1)
		# print(so_qty)
