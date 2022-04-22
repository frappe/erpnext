# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt

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
			po = frappe.get_doc("Purchase Order", self.purchase_order)
			if not po.is_subcontracted:
				frappe.throw(_("Please select a valid Purchase Order that is configured for Subcontracting."))

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
			elif self.docstatus == 2:
				status = "Cancelled"

		if status:
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


def get_item_details(items):
	item = frappe.qb.DocType("Item")
	item_list = (
		frappe.qb.from_(item)
		.select(item.item_code, item.description, item.allow_alternative_item)
		.where(item.name.isin(items))
		.run(as_dict=True)
	)

	item_details = {}
	for item in item_list:
		item_details[item.item_code] = item

	return item_details


@frappe.whitelist()
def make_rm_stock_entry(subcontracting_order, rm_items):
	rm_items_list = rm_items

	if isinstance(rm_items, str):
		rm_items_list = json.loads(rm_items)
	elif not rm_items:
		frappe.throw(_("No Items available for transfer"))

	if rm_items_list:
		fg_items = list(set(item["item_code"] for item in rm_items_list))
	else:
		frappe.throw(_("No Items selected for transfer"))

	if subcontracting_order:
		subcontracting_order = frappe.get_doc("Subcontracting Order", subcontracting_order)

	if fg_items:
		items = tuple(set(item["rm_item_code"] for item in rm_items_list))
		item_wh = get_item_details(items)

		stock_entry = frappe.new_doc("Stock Entry")
		stock_entry.purpose = "Send to Subcontractor"
		stock_entry.subcontracting_order = subcontracting_order.name
		stock_entry.supplier = subcontracting_order.supplier
		stock_entry.supplier_name = subcontracting_order.supplier_name
		stock_entry.supplier_address = subcontracting_order.supplier_address
		stock_entry.address_display = subcontracting_order.address_display
		stock_entry.company = subcontracting_order.company
		stock_entry.to_warehouse = subcontracting_order.supplier_warehouse
		stock_entry.set_stock_entry_type()

		for item_code in fg_items:
			for rm_item_data in rm_items_list:
				if rm_item_data["item_code"] == item_code:
					rm_item_code = rm_item_data["rm_item_code"]
					items_dict = {
						rm_item_code: {
							"sco_rm_detail": rm_item_data.get("name"),
							"item_name": rm_item_data["item_name"],
							"description": item_wh.get(rm_item_code, {}).get("description", ""),
							"qty": rm_item_data["qty"],
							"from_warehouse": rm_item_data["warehouse"],
							"stock_uom": rm_item_data["stock_uom"],
							"serial_no": rm_item_data.get("serial_no"),
							"batch_no": rm_item_data.get("batch_no"),
							"main_item_code": rm_item_data["item_code"],
							"allow_alternative_item": item_wh.get(rm_item_code, {}).get("allow_alternative_item"),
						}
					}
					stock_entry.add_to_stock_entry_detail(items_dict)
		return stock_entry.as_dict()
	else:
		frappe.throw(_("No Items selected for transfer"))
	return subcontracting_order.name


def add_items_in_ste(ste_doc, row, qty, sco_rm_details, batch_no=None):
	item = ste_doc.append("items", row.item_details)

	sco_rm_detail = list(set(row.sco_rm_details).intersection(sco_rm_details))
	item.update(
		{
			"qty": qty,
			"batch_no": batch_no,
			"basic_rate": row.item_details["rate"],
			"sco_rm_detail": sco_rm_detail[0] if sco_rm_detail else "",
			"s_warehouse": row.item_details["t_warehouse"],
			"t_warehouse": row.item_details["s_warehouse"],
			"item_code": row.item_details["rm_item_code"],
			"subcontracted_item": row.item_details["main_item_code"],
			"serial_no": "\n".join(row.serial_no) if row.serial_no else "",
		}
	)


def make_return_stock_entry_for_subcontract(available_materials, sco_doc, sco_rm_details):
	ste_doc = frappe.new_doc("Stock Entry")
	ste_doc.purpose = "Material Transfer"

	ste_doc.subcontracting_order = sco_doc.name
	ste_doc.company = sco_doc.company
	ste_doc.is_return = 1

	for key, value in available_materials.items():
		if not value.qty:
			continue

		if value.batch_no:
			for batch_no, qty in value.batch_no.items():
				if qty > 0:
					add_items_in_ste(ste_doc, value, value.qty, sco_rm_details, batch_no)
		else:
			add_items_in_ste(ste_doc, value, value.qty, sco_rm_details)

	ste_doc.set_stock_entry_type()
	ste_doc.calculate_rate_and_amount()

	return ste_doc


@frappe.whitelist()
def get_materials_from_supplier(subcontracting_order, sco_rm_details):
	if isinstance(sco_rm_details, str):
		sco_rm_details = json.loads(sco_rm_details)

	doc = frappe.get_cached_doc("Subcontracting Order", subcontracting_order)
	doc.initialized_fields()
	doc.subcontracting_orders = [doc.name]
	doc.get_available_materials()

	if not doc.available_materials:
		frappe.throw(
			_("Materials are already received against the Subcontracting Order {0}").format(
				subcontracting_order
			)
		)

	return make_return_stock_entry_for_subcontract(doc.available_materials, doc, sco_rm_details)


@frappe.whitelist()
def update_subcontracting_order_status(sco):
	if isinstance(sco, str):
		sco = frappe.get_doc("Subcontracting Order", sco)

	sco.update_status()
