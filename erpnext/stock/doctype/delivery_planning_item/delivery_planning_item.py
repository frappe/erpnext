# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class DeliveryPlanningItem(Document):

	@frappe.whitelist()
	def split_dp_item(self,n_transporter, n_qty, n_src_warehouse, n_supplier, n_date):
		new_qty = 0
		if(n_transporter, n_supplier, n_src_warehouse, n_qty):
			if n_qty != self.ordered_qty:
				new_qty = int(self.ordered_qty) - n_qty
				print("------- per unit ---------- ",self.weight_per_unit,"-------- new Qty ------- ", n_qty)
				n_weight = self.weight_per_unit * n_qty
				print("===== new n weight ===== ", n_weight)
				dp_item = frappe.new_doc("Delivery Planning Item")
				dp_item.transporter = n_transporter
				dp_item.customer = self.customer
				dp_item.item_code = self.item_code
				dp_item.item_name = self.item_name
				dp_item.ordered_qty = n_qty
				dp_item.pending_qty = n_qty
				dp_item.qty_to_deliver = n_qty
				dp_item.weight_to_deliver = self.weight_per_unit * n_qty
				dp_item.sales_order = self.sales_order
				dp_item.sorce_warehouse = n_src_warehouse
				dp_item.postal_code = 0
				dp_item.delivery_date = n_date
				dp_item.current_stock = self.current_stock
				dp_item.available_stock = self.available_stock
				dp_item.related_delivey_planning = self.related_delivey_planning
				dp_item.weight_per_unit = self.weight_per_unit
				dp_item.supplier_dc = self.supplier_dc
				dp_item.supplier = n_supplier
				dp_item.save(ignore_permissions=True)
				print("------- per unit ---------- ",self.weight_per_unit,"-------- new Qty ------- ", new_qty)

				n_weight = int(self.weight_per_unit) * new_qty
				frappe.db.set_value('Delivery Planning Item', self.name, {
					'ordered_qty': new_qty,
					'pending_qty': new_qty,
					'qty_to_deliver': new_qty
					# 'weight_to_deliver': new_qty * self.weight_per_unit
				})

			return 1
		else: return 0

frappe.db.set_value('Task', 'TASK00002', {
    'subject': 'New Subject',
    'description': 'New Description'
})
