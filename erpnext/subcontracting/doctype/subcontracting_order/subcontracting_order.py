# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt

from erpnext.buying.doctype.purchase_order.purchase_order import is_subcontracting_order_created
from erpnext.controllers.subcontracting_controller import SubcontractingController
from erpnext.stock.stock_balance import get_ordered_qty, update_bin_qty
from erpnext.stock.utils import get_bin


class SubcontractingOrder(SubcontractingController):
	def before_validate(self):
		super(SubcontractingOrder, self).before_validate()

	def validate(self):
		super(SubcontractingOrder, self).validate()
		self.validate_purchase_order_for_subcontracting()
		self.validate_items()
		self.validate_service_items()
		self.validate_supplied_items()
		self.set_missing_values()
		self.reset_default_field_value("set_warehouse", "items", "warehouse")

	def on_submit(self):
		self.update_ordered_qty_for_subcontracting()
		self.update_reserved_qty_for_subcontracting()
		self.update_status()

	def on_cancel(self):
		self.update_ordered_qty_for_subcontracting()
		self.update_reserved_qty_for_subcontracting()
		self.update_status()

	def validate_purchase_order_for_subcontracting(self):
		if self.purchase_order:
			if is_subcontracting_order_created(self.purchase_order):
				frappe.throw(
					_(
						"Only one Subcontracting Order can be created against a Purchase Order, cancel the existing Subcontracting Order to create a new one."
					)
				)

			po = frappe.get_doc("Purchase Order", self.purchase_order)

			if not po.is_subcontracted:
				frappe.throw(_("Please select a valid Purchase Order that is configured for Subcontracting."))

			if po.is_old_subcontracting_flow:
				frappe.throw(_("Please select a valid Purchase Order that has Service Items."))

			if po.docstatus != 1:
				msg = f"Please submit Purchase Order {po.name} before proceeding."
				frappe.throw(_(msg))

			if po.per_received == 100:
				msg = f"Cannot create more Subcontracting Orders against the Purchase Order {po.name}."
				frappe.throw(_(msg))
		else:
			self.service_items = self.items = self.supplied_items = None
			frappe.throw(_("Please select a Subcontracting Purchase Order."))

	def validate_service_items(self):
		for item in self.service_items:
			if frappe.get_value("Item", item.item_code, "is_stock_item"):
				msg = f"Service Item {item.item_name} must be a non-stock item."
				frappe.throw(_(msg))

	def validate_supplied_items(self):
		if self.supplier_warehouse:
			for item in self.supplied_items:
				if self.supplier_warehouse == item.reserve_warehouse:
					msg = f"Reserve Warehouse must be different from Supplier Warehouse for Supplied Item {item.main_item_code}."
					frappe.throw(_(msg))

	def set_missing_values(self):
		self.set_missing_values_in_additional_costs()
		self.set_missing_values_in_service_items()
		self.set_missing_values_in_supplied_items()
		self.set_missing_values_in_items()

	def set_missing_values_in_additional_costs(self):
		if self.get("additional_costs"):
			self.total_additional_costs = sum(flt(item.amount) for item in self.get("additional_costs"))

			if self.total_additional_costs:
				if self.distribute_additional_costs_based_on == "Amount":
					total_amt = sum(flt(item.amount) for item in self.get("items"))
					for item in self.items:
						item.additional_cost_per_qty = (
							(item.amount * self.total_additional_costs) / total_amt
						) / item.qty
				else:
					total_qty = sum(flt(item.qty) for item in self.get("items"))
					additional_cost_per_qty = self.total_additional_costs / total_qty
					for item in self.items:
						item.additional_cost_per_qty = additional_cost_per_qty
		else:
			self.total_additional_costs = 0

	def set_missing_values_in_service_items(self):
		for idx, item in enumerate(self.get("service_items")):
			self.items[idx].service_cost_per_qty = item.amount / self.items[idx].qty

	def set_missing_values_in_supplied_items(self):
		for item in self.get("items"):
			bom = frappe.get_doc("BOM", item.bom)
			rm_cost = sum(flt(rm_item.amount) for rm_item in bom.items)
			item.rm_cost_per_qty = rm_cost / flt(bom.quantity)

	def set_missing_values_in_items(self):
		total_qty = total = 0
		for item in self.items:
			item.rate = (
				item.rm_cost_per_qty + item.service_cost_per_qty + (item.additional_cost_per_qty or 0)
			)
			item.amount = item.qty * item.rate
			total_qty += flt(item.qty)
			total += flt(item.amount)
		else:
			self.total_qty = total_qty
			self.total = total

	def update_ordered_qty_for_subcontracting(self, sco_item_rows=None):
		item_wh_list = []
		for item in self.get("items"):
			if (
				(not sco_item_rows or item.name in sco_item_rows)
				and [item.item_code, item.warehouse] not in item_wh_list
				and frappe.get_cached_value("Item", item.item_code, "is_stock_item")
				and item.warehouse
			):
				item_wh_list.append([item.item_code, item.warehouse])
		for item_code, warehouse in item_wh_list:
			update_bin_qty(item_code, warehouse, {"ordered_qty": get_ordered_qty(item_code, warehouse)})

	def update_reserved_qty_for_subcontracting(self):
		for item in self.supplied_items:
			if item.rm_item_code:
				stock_bin = get_bin(item.rm_item_code, item.reserve_warehouse)
				stock_bin.update_reserved_qty_for_sub_contracting()

	def populate_items_table(self):
		items = []

		for si in self.service_items:
			if si.fg_item:
				item = frappe.get_doc("Item", si.fg_item)
				bom = frappe.db.get_value("BOM", {"item": item.item_code, "is_active": 1, "is_default": 1})

				items.append(
					{
						"item_code": item.item_code,
						"item_name": item.item_name,
						"schedule_date": self.schedule_date,
						"description": item.description,
						"qty": si.fg_item_qty,
						"stock_uom": item.stock_uom,
						"bom": bom,
					},
				)
			else:
				frappe.throw(
					_("Please select Finished Good Item for Service Item {0}").format(
						si.item_name or si.item_code
					)
				)
		else:
			for item in items:
				self.append("items", item)
			else:
				self.set_missing_values()

	def update_status(self, status=None, update_modified=False):
		if self.docstatus >= 1 and not status:
			if self.docstatus == 1:
				if self.status == "Draft":
					status = "Open"
				elif self.per_received >= 100:
					status = "Completed"
				elif self.per_received > 0 and self.per_received < 100:
					status = "Partially Received"
				else:
					total_required_qty = total_supplied_qty = 0
					for item in self.supplied_items:
						total_required_qty += item.required_qty
						total_supplied_qty += item.supplied_qty or 0
					if total_supplied_qty:
						status = "Partial Material Transferred"
						if total_supplied_qty >= total_required_qty:
							status = "Material Transferred"
					else:
						status = "Open"
			elif self.docstatus == 2:
				status = "Cancelled"

			frappe.db.set_value("Subcontracting Order", self.name, "status", status, update_modified)


@frappe.whitelist()
def make_subcontracting_receipt(source_name, target_doc=None):
	return get_mapped_subcontracting_receipt(source_name, target_doc)


def get_mapped_subcontracting_receipt(source_name, target_doc=None):
	def update_item(obj, target, source_parent):
		target.qty = flt(obj.qty) - flt(obj.received_qty)
		target.amount = (flt(obj.qty) - flt(obj.received_qty)) * flt(obj.rate)

	target_doc = get_mapped_doc(
		"Subcontracting Order",
		source_name,
		{
			"Subcontracting Order": {
				"doctype": "Subcontracting Receipt",
				"field_map": {"supplier_warehouse": "supplier_warehouse"},
				"validation": {
					"docstatus": ["=", 1],
				},
			},
			"Subcontracting Order Item": {
				"doctype": "Subcontracting Receipt Item",
				"field_map": {
					"name": "subcontracting_order_item",
					"parent": "subcontracting_order",
					"bom": "bom",
				},
				"postprocess": update_item,
				"condition": lambda doc: abs(doc.received_qty) < abs(doc.qty),
			},
		},
		target_doc,
	)

	return target_doc


@frappe.whitelist()
def update_subcontracting_order_status(sco):
	if isinstance(sco, str):
		sco = frappe.get_doc("Subcontracting Order", sco)

	sco.update_status()
