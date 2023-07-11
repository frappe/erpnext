# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe

from erpnext.controllers.selling_controller import SellingController


class ProformaInvoice(SellingController):
	def __init__(self, *args, **kwargs):
		super(ProformaInvoice, self).__init__(*args, **kwargs)
		self.status_updater = [
			{
				"source_dt": "Proforma Invoice Item",
				"target_dt": "Sales Order Item",
				"target_field": "proforma_qty",  # field of Sales Order Item
				"source_field": "qty",  # field of Proforma Invoice Item
				"target_ref_field": "qty",  # field of Proforma Invoice Item
				"join_field": "so_item",  # field of Proforma Invoice Item
				"target_parent_dt": "Sales Order",
				"percent_join_field": "sales_order",
			}
		]

	def on_submit(self):
		self.update_prevdoc_status()
