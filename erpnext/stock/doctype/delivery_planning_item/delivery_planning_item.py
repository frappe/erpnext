# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class DeliveryPlanningItem(Document):

	@frappe.whitelist()
	def split_dp_item(self,n_transporter, n_qty, n_src_warehouse, n_supplier):
		if(n_transporter, n_supplier, n_src_warehouse, n_qty):
			if n_qty != self.ordered_qty:
				new_qty = int(self.ordered_qty) - n_qty

				dp_item = frappe.new_doc("Delivery Planning Item")
				dp_item.transporter = n_transporter
				dp_item.customer = self.customer
				dp_item.item_code = self.item_code
				dp_item.item_name = self.item_name
				dp_item.ordered_qty = n_qty
				dp_item.pending_qty = n_qty
				dp_item.qty_to_deliver = n_qty
				dp_item.weight_to_deliver = n_qty * self.weight_per_unit
				dp_item.sales_order = self.sales_order
				dp_item.sorce_warehouse = n_src_warehouse
				dp_item.postal_code = 0
				dp_item.delivery_date = self.delivery_date
				dp_item.current_stock = self.current_stock
				dp_item.available_stock = self.available_stock
				dp_item.related_delivey_planning = self.related_delivey_planning
				dp_item.weight_per_unit = self.weight_per_unit
				dp_item.supplier_dc = self.supplier_dc
				dp_item.supplier = n_supplier
				dp_item.save(ignore_permissions=True)

				dp_item1 = frappe.new_doc("Delivery Planning Item")
				dp_item1.transporter = n_transporter
				dp_item1.customer = self.customer
				dp_item1.item_code = self.item_code
				dp_item1.item_name = self.item_name
				dp_item1.ordered_qty = new_qty
				dp_item1.pending_qty = new_qty
				dp_item1.qty_to_deliver = new_qty
				dp_item1.weight_to_deliver = new_qty * self.weight_per_unit
				dp_item1.sales_order = self.sales_order
				dp_item1.sorce_warehouse = n_src_warehouse
				dp_item1.postal_code = 0
				dp_item1.delivery_date = self.delivery_date
				dp_item1.current_stock = self.current_stock
				dp_item1.available_stock = self.available_stock
				dp_item1.related_delivey_planning = self.related_delivey_planning
				dp_item1.weight_per_unit = self.weight_per_unit
				dp_item1.supplier_dc = self.supplier_dc
				dp_item1.supplier = n_supplier
				dp_item1.save(ignore_permissions=True)

				frappe.db.delete('Delivery Planning Item', {
					'name': self.name
				})

			return 1
		else: return 0
