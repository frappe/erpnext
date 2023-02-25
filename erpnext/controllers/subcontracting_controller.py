# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import copy
import json
from collections import defaultdict

import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.utils import cint, cstr, flt, get_link_to_form

from erpnext.controllers.stock_controller import StockController
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
from erpnext.stock.utils import get_incoming_rate


class SubcontractingController(StockController):
	def __init__(self, *args, **kwargs):
		super(SubcontractingController, self).__init__(*args, **kwargs)
		if self.get("is_old_subcontracting_flow"):
			self.subcontract_data = frappe._dict(
				{
					"order_doctype": "Purchase Order",
					"order_field": "purchase_order",
					"rm_detail_field": "po_detail",
					"receipt_supplied_items_field": "Purchase Receipt Item Supplied",
					"order_supplied_items_field": "Purchase Order Item Supplied",
				}
			)
		else:
			self.subcontract_data = frappe._dict(
				{
					"order_doctype": "Subcontracting Order",
					"order_field": "subcontracting_order",
					"rm_detail_field": "sco_rm_detail",
					"receipt_supplied_items_field": "Subcontracting Receipt Supplied Item",
					"order_supplied_items_field": "Subcontracting Order Supplied Item",
				}
			)

	def before_validate(self):
		if self.doctype in ["Subcontracting Order", "Subcontracting Receipt"]:
			self.remove_empty_rows()
			self.set_items_conversion_factor()

	def validate(self):
		if self.doctype in ["Subcontracting Order", "Subcontracting Receipt"]:
			self.validate_items()
			self.create_raw_materials_supplied()
		else:
			super(SubcontractingController, self).validate()

	def remove_empty_rows(self):
		for key in ["service_items", "items", "supplied_items"]:
			if self.get(key):
				idx = 1
				for item in self.get(key)[:]:
					if not (item.get("item_code") or item.get("main_item_code")):
						self.get(key).remove(item)
					else:
						item.idx = idx
						idx += 1

	def set_items_conversion_factor(self):
		for item in self.get("items"):
			if not item.conversion_factor:
				item.conversion_factor = 1

	def validate_items(self):
		for item in self.items:
			is_stock_item, is_sub_contracted_item = frappe.get_value(
				"Item", item.item_code, ["is_stock_item", "is_sub_contracted_item"]
			)

			if not is_stock_item:
				frappe.throw(_("Row {0}: Item {1} must be a stock item.").format(item.idx, item.item_name))

			if not is_sub_contracted_item:
				frappe.throw(
					_("Row {0}: Item {1} must be a subcontracted item.").format(item.idx, item.item_name)
				)

			if item.bom:
				bom = frappe.get_doc("BOM", item.bom)
				if not bom.is_active:
					frappe.throw(
						_("Row {0}: Please select an active BOM for Item {1}.").format(item.idx, item.item_name)
					)
				if bom.item != item.item_code:
					frappe.throw(
						_("Row {0}: Please select an valid BOM for Item {1}.").format(item.idx, item.item_name)
					)
			else:
				frappe.throw(_("Row {0}: Please select a BOM for Item {1}.").format(item.idx, item.item_name))

	def __get_data_before_save(self):
		item_dict = {}
		if (
			self.doctype in ["Purchase Receipt", "Purchase Invoice", "Subcontracting Receipt"]
			and self._doc_before_save
		):
			for row in self._doc_before_save.get("items"):
				item_dict[row.name] = (row.item_code, row.qty)

		return item_dict

	def __identify_change_in_item_table(self):
		self.__changed_name = []
		self.__reference_name = []

		if self.doctype in ["Purchase Order", "Subcontracting Order"] or self.is_new():
			self.set(self.raw_material_table, [])
			return

		item_dict = self.__get_data_before_save()
		if not item_dict:
			return True

		for row in self.items:
			self.__reference_name.append(row.name)
			if (row.name not in item_dict) or (row.item_code, row.qty) != item_dict[row.name]:
				self.__changed_name.append(row.name)

			if item_dict.get(row.name):
				del item_dict[row.name]

		self.__changed_name.extend(item_dict.keys())

	def __get_backflush_based_on(self):
		self.backflush_based_on = frappe.db.get_single_value(
			"Buying Settings", "backflush_raw_materials_of_subcontract_based_on"
		)

	def initialized_fields(self):
		self.available_materials = frappe._dict()
		self.__transferred_items = frappe._dict()
		self.alternative_item_details = frappe._dict()
		self.__get_backflush_based_on()

	def __get_subcontract_orders(self):
		self.subcontract_orders = []

		if self.doctype in ["Purchase Order", "Subcontracting Order"]:
			return

		self.subcontract_orders = [
			item.get(self.subcontract_data.order_field)
			for item in self.items
			if item.get(self.subcontract_data.order_field)
		]

	def __get_pending_qty_to_receive(self):
		"""Get qty to be received against the subcontract order."""

		self.qty_to_be_received = defaultdict(float)

		if (
			self.doctype != self.subcontract_data.order_doctype
			and self.backflush_based_on != "BOM"
			and self.subcontract_orders
		):
			for row in frappe.get_all(
				f"{self.subcontract_data.order_doctype} Item",
				fields=["item_code", "(qty - received_qty) as qty", "parent", "name"],
				filters={"docstatus": 1, "parent": ("in", self.subcontract_orders)},
			):

				self.qty_to_be_received[(row.item_code, row.parent)] += row.qty

	def __get_transferred_items(self):
		fields = [f"`tabStock Entry`.`{self.subcontract_data.order_field}`"]
		alias_dict = {
			"item_code": "rm_item_code",
			"subcontracted_item": "main_item_code",
			"basic_rate": "rate",
		}

		child_table_fields = [
			"item_code",
			"item_name",
			"description",
			"qty",
			"basic_rate",
			"amount",
			"serial_no",
			"uom",
			"subcontracted_item",
			"stock_uom",
			"batch_no",
			"conversion_factor",
			"s_warehouse",
			"t_warehouse",
			"item_group",
			self.subcontract_data.rm_detail_field,
		]

		if self.backflush_based_on == "BOM":
			child_table_fields.append("original_item")

		for field in child_table_fields:
			fields.append(f"`tabStock Entry Detail`.`{field}` As {alias_dict.get(field, field)}")

		filters = [
			["Stock Entry", "docstatus", "=", 1],
			["Stock Entry", "purpose", "=", "Send to Subcontractor"],
			["Stock Entry", self.subcontract_data.order_field, "in", self.subcontract_orders],
		]

		return frappe.get_all("Stock Entry", fields=fields, filters=filters)

	def __set_alternative_item_details(self, row):
		if row.get("original_item"):
			self.alternative_item_details[row.get("original_item")] = row

	def __get_received_items(self, doctype):
		fields = []
		for field in ["name", self.subcontract_data.order_field, "parent"]:
			fields.append(f"`tab{doctype} Item`.`{field}`")

		filters = [
			[doctype, "docstatus", "=", 1],
			[f"{doctype} Item", self.subcontract_data.order_field, "in", self.subcontract_orders],
		]
		if doctype == "Purchase Invoice":
			filters.append(["Purchase Invoice", "update_stock", "=", 1])

		return frappe.get_all(f"{doctype}", fields=fields, filters=filters)

	def __get_consumed_items(self, doctype, receipt_items):
		return frappe.get_all(
			self.subcontract_data.receipt_supplied_items_field,
			fields=[
				"serial_no",
				"rm_item_code",
				"reference_name",
				"batch_no",
				"consumed_qty",
				"main_item_code",
			],
			filters={"docstatus": 1, "reference_name": ("in", list(receipt_items)), "parenttype": doctype},
		)

	def __update_consumed_materials(self, doctype, return_consumed_items=False):
		"""Deduct the consumed materials from the available materials."""

		receipt_items = self.__get_received_items(doctype)
		if not receipt_items:
			return ([], {}) if return_consumed_items else None

		receipt_items = {
			item.name: item.get(self.subcontract_data.order_field) for item in receipt_items
		}
		consumed_materials = self.__get_consumed_items(doctype, receipt_items.keys())

		if return_consumed_items:
			return (consumed_materials, receipt_items)

		for row in consumed_materials:
			key = (row.rm_item_code, row.main_item_code, receipt_items.get(row.reference_name))
			if not self.available_materials.get(key):
				continue

			self.available_materials[key]["qty"] -= row.consumed_qty
			if row.serial_no:
				self.available_materials[key]["serial_no"] = list(
					set(self.available_materials[key]["serial_no"]) - set(get_serial_nos(row.serial_no))
				)

			if row.batch_no:
				self.available_materials[key]["batch_no"][row.batch_no] -= row.consumed_qty

	def get_available_materials(self):
		"""Get the available raw materials which has been transferred to the supplier.
		available_materials = {
		        (item_code, subcontracted_item, subcontract_order): {
		                'qty': 1, 'serial_no': [ABC], 'batch_no': {'batch1': 1}, 'data': item_details
		        }
		}
		"""
		if not self.subcontract_orders:
			return

		for row in self.__get_transferred_items():
			key = (row.rm_item_code, row.main_item_code, row.get(self.subcontract_data.order_field))

			if key not in self.available_materials:
				self.available_materials.setdefault(
					key,
					frappe._dict(
						{
							"qty": 0,
							"serial_no": [],
							"batch_no": defaultdict(float),
							"item_details": row,
							f"{self.subcontract_data.rm_detail_field}s": [],
						}
					),
				)

			details = self.available_materials[key]
			details.qty += row.qty
			details[f"{self.subcontract_data.rm_detail_field}s"].append(
				row.get(self.subcontract_data.rm_detail_field)
			)

			if row.serial_no:
				details.serial_no.extend(get_serial_nos(row.serial_no))

			if row.batch_no:
				details.batch_no[row.batch_no] += row.qty

			self.__set_alternative_item_details(row)

		self.__transferred_items = copy.deepcopy(self.available_materials)
		if self.get("is_old_subcontracting_flow"):
			for doctype in ["Purchase Receipt", "Purchase Invoice"]:
				self.__update_consumed_materials(doctype)
		else:
			self.__update_consumed_materials("Subcontracting Receipt")

	def __remove_changed_rows(self):
		if not self.__changed_name:
			return

		i = 1
		self.set(self.raw_material_table, [])
		for item in self._doc_before_save.supplied_items:
			if item.reference_name in self.__changed_name:
				continue

			if item.reference_name not in self.__reference_name:
				continue

			item.idx = i
			self.append("supplied_items", item)

			i += 1

	def __get_materials_from_bom(self, item_code, bom_no, exploded_item=0):
		doctype = "BOM Item" if not exploded_item else "BOM Explosion Item"
		fields = [f"`tab{doctype}`.`stock_qty` / `tabBOM`.`quantity` as qty_consumed_per_unit"]

		alias_dict = {
			"item_code": "rm_item_code",
			"name": "bom_detail_no",
			"source_warehouse": "reserve_warehouse",
		}
		for field in [
			"item_code",
			"name",
			"rate",
			"stock_uom",
			"source_warehouse",
			"description",
			"item_name",
			"stock_uom",
		]:
			fields.append(f"`tab{doctype}`.`{field}` As {alias_dict.get(field, field)}")

		filters = [
			[doctype, "parent", "=", bom_no],
			[doctype, "docstatus", "=", 1],
			["BOM", "item", "=", item_code],
			[doctype, "sourced_by_supplier", "=", 0],
		]

		return (
			frappe.get_all("BOM", fields=fields, filters=filters, order_by=f"`tab{doctype}`.`idx`") or []
		)

	def __update_reserve_warehouse(self, row, item):
		if self.doctype == self.subcontract_data.order_doctype:
			row.reserve_warehouse = self.set_reserve_warehouse or item.warehouse

	def __set_alternative_item(self, bom_item):
		if self.alternative_item_details.get(bom_item.rm_item_code):
			bom_item.update(self.alternative_item_details[bom_item.rm_item_code])

	def __set_serial_nos(self, item_row, rm_obj):
		key = (rm_obj.rm_item_code, item_row.item_code, item_row.get(self.subcontract_data.order_field))
		if self.available_materials.get(key) and self.available_materials[key]["serial_no"]:
			used_serial_nos = self.available_materials[key]["serial_no"][0 : cint(rm_obj.consumed_qty)]
			rm_obj.serial_no = "\n".join(used_serial_nos)

			# Removed the used serial nos from the list
			for sn in used_serial_nos:
				self.available_materials[key]["serial_no"].remove(sn)

	def __set_batch_no_as_per_qty(self, item_row, rm_obj, batch_no, qty):
		rm_obj.update(
			{
				"consumed_qty": qty,
				"batch_no": batch_no,
				"required_qty": qty,
				self.subcontract_data.order_field: item_row.get(self.subcontract_data.order_field),
			}
		)

		self.__set_serial_nos(item_row, rm_obj)

	def __set_consumed_qty(self, rm_obj, consumed_qty, required_qty=0):
		rm_obj.required_qty = required_qty
		rm_obj.consumed_qty = consumed_qty

	def __set_batch_nos(self, bom_item, item_row, rm_obj, qty):
		key = (rm_obj.rm_item_code, item_row.item_code, item_row.get(self.subcontract_data.order_field))

		if self.available_materials.get(key) and self.available_materials[key]["batch_no"]:
			new_rm_obj = None
			for batch_no, batch_qty in self.available_materials[key]["batch_no"].items():
				if batch_qty >= qty or (
					rm_obj.consumed_qty == 0
					and self.backflush_based_on == "BOM"
					and len(self.available_materials[key]["batch_no"]) == 1
				):
					if rm_obj.consumed_qty == 0:
						self.__set_consumed_qty(rm_obj, qty)

					self.__set_batch_no_as_per_qty(item_row, rm_obj, batch_no, qty)
					self.available_materials[key]["batch_no"][batch_no] -= qty
					return

				elif qty > 0 and batch_qty > 0:
					qty -= batch_qty
					new_rm_obj = self.append(self.raw_material_table, bom_item)
					new_rm_obj.reference_name = item_row.name
					self.__set_batch_no_as_per_qty(item_row, new_rm_obj, batch_no, batch_qty)
					self.available_materials[key]["batch_no"][batch_no] = 0

			if abs(qty) > 0 and not new_rm_obj:
				self.__set_consumed_qty(rm_obj, qty)
		else:
			self.__set_consumed_qty(rm_obj, qty, bom_item.required_qty or qty)
			self.__set_serial_nos(item_row, rm_obj)

	def __add_supplied_item(self, item_row, bom_item, qty):
		bom_item.conversion_factor = item_row.conversion_factor
		rm_obj = self.append(self.raw_material_table, bom_item)
		rm_obj.reference_name = item_row.name

		if self.doctype == "Subcontracting Receipt":
			args = frappe._dict(
				{
					"item_code": rm_obj.rm_item_code,
					"warehouse": self.supplier_warehouse,
					"posting_date": self.posting_date,
					"posting_time": self.posting_time,
					"qty": -1 * flt(rm_obj.consumed_qty),
					"serial_no": rm_obj.serial_no,
					"batch_no": rm_obj.batch_no,
					"voucher_type": self.doctype,
					"voucher_no": self.name,
					"company": self.company,
					"allow_zero_valuation": 1,
				}
			)
			rm_obj.rate = get_incoming_rate(args)

		if self.doctype == self.subcontract_data.order_doctype:
			rm_obj.required_qty = qty
			rm_obj.amount = rm_obj.required_qty * rm_obj.rate
		else:
			rm_obj.consumed_qty = 0
			setattr(
				rm_obj, self.subcontract_data.order_field, item_row.get(self.subcontract_data.order_field)
			)
			self.__set_batch_nos(bom_item, item_row, rm_obj, qty)

	def __get_qty_based_on_material_transfer(self, item_row, transfer_item):
		key = (item_row.item_code, item_row.get(self.subcontract_data.order_field))

		if self.qty_to_be_received == item_row.qty:
			return transfer_item.qty

		if self.qty_to_be_received:
			qty = (flt(item_row.qty) * flt(transfer_item.qty)) / flt(self.qty_to_be_received.get(key, 0))
			transfer_item.item_details.required_qty = transfer_item.qty

			if transfer_item.serial_no or frappe.get_cached_value(
				"UOM", transfer_item.item_details.stock_uom, "must_be_whole_number"
			):
				return frappe.utils.ceil(qty)

			return qty

	def __set_supplied_items(self):
		self.bom_items = {}

		has_supplied_items = True if self.get(self.raw_material_table) else False
		for row in self.items:
			if self.doctype != self.subcontract_data.order_doctype and (
				(self.__changed_name and row.name not in self.__changed_name)
				or (has_supplied_items and not self.__changed_name)
			):
				continue

			if self.doctype == self.subcontract_data.order_doctype or self.backflush_based_on == "BOM":
				for bom_item in self.__get_materials_from_bom(
					row.item_code, row.bom, row.get("include_exploded_items")
				):
					qty = flt(bom_item.qty_consumed_per_unit) * flt(row.qty) * row.conversion_factor
					bom_item.main_item_code = row.item_code
					self.__update_reserve_warehouse(bom_item, row)
					self.__set_alternative_item(bom_item)
					self.__add_supplied_item(row, bom_item, qty)

			elif self.backflush_based_on != "BOM":
				for key, transfer_item in self.available_materials.items():
					if (key[1], key[2]) == (
						row.item_code,
						row.get(self.subcontract_data.order_field),
					) and transfer_item.qty > 0:
						qty = flt(self.__get_qty_based_on_material_transfer(row, transfer_item))
						transfer_item.qty -= qty
						self.__add_supplied_item(row, transfer_item.get("item_details"), qty)

				if self.qty_to_be_received:
					self.qty_to_be_received[
						(row.item_code, row.get(self.subcontract_data.order_field))
					] -= row.qty

	def __prepare_supplied_items(self):
		self.initialized_fields()
		self.__get_subcontract_orders()
		self.__get_pending_qty_to_receive()
		self.get_available_materials()
		self.__remove_changed_rows()
		self.__set_supplied_items()

	def __validate_batch_no(self, row, key):
		if row.get("batch_no") and row.get("batch_no") not in self.__transferred_items.get(key).get(
			"batch_no"
		):
			link = get_link_to_form(
				self.subcontract_data.order_doctype, row.get(self.subcontract_data.order_field)
			)
			msg = f'The Batch No {frappe.bold(row.get("batch_no"))} has not supplied against the {self.subcontract_data.order_doctype} {link}'
			frappe.throw(_(msg), title=_("Incorrect Batch Consumed"))

	def __validate_serial_no(self, row, key):
		if row.get("serial_no"):
			serial_nos = get_serial_nos(row.get("serial_no"))
			incorrect_sn = set(serial_nos).difference(self.__transferred_items.get(key).get("serial_no"))

			if incorrect_sn:
				incorrect_sn = "\n".join(incorrect_sn)
				link = get_link_to_form(
					self.subcontract_data.order_doctype, row.get(self.subcontract_data.order_field)
				)
				msg = f"The Serial Nos {incorrect_sn} has not supplied against the {self.subcontract_data.order_doctype} {link}"
				frappe.throw(_(msg), title=_("Incorrect Serial Number Consumed"))

	def __validate_supplied_items(self):
		if self.doctype not in ["Purchase Invoice", "Purchase Receipt", "Subcontracting Receipt"]:
			return

		for row in self.get(self.raw_material_table):
			key = (row.rm_item_code, row.main_item_code, row.get(self.subcontract_data.order_field))
			if not self.__transferred_items or not self.__transferred_items.get(key):
				return

			self.__validate_batch_no(row, key)
			self.__validate_serial_no(row, key)

	def set_materials_for_subcontracted_items(self, raw_material_table):
		if self.doctype == "Purchase Invoice" and not self.update_stock:
			return

		self.raw_material_table = raw_material_table
		self.__identify_change_in_item_table()
		self.__prepare_supplied_items()
		self.__validate_supplied_items()

	def create_raw_materials_supplied(self, raw_material_table="supplied_items"):
		self.set_materials_for_subcontracted_items(raw_material_table)

		if self.doctype in ["Subcontracting Receipt", "Purchase Receipt", "Purchase Invoice"]:
			for item in self.get("items"):
				item.rm_supp_cost = 0.0

	def __update_consumed_qty_in_subcontract_order(self, itemwise_consumed_qty):
		fields = ["main_item_code", "rm_item_code", "parent", "supplied_qty", "name"]
		filters = {"docstatus": 1, "parent": ("in", self.subcontract_orders)}

		for row in frappe.get_all(
			self.subcontract_data.order_supplied_items_field, fields=fields, filters=filters, order_by="idx"
		):
			key = (row.rm_item_code, row.main_item_code, row.parent)
			consumed_qty = itemwise_consumed_qty.get(key, 0)

			if row.supplied_qty < consumed_qty:
				consumed_qty = row.supplied_qty

			itemwise_consumed_qty[key] -= consumed_qty
			frappe.db.set_value(
				self.subcontract_data.order_supplied_items_field, row.name, "consumed_qty", consumed_qty
			)

	def set_consumed_qty_in_subcontract_order(self):
		# Update consumed qty back in the subcontract order
		if self.doctype in ["Subcontracting Order", "Subcontracting Receipt"] or self.get(
			"is_old_subcontracting_flow"
		):
			self.__get_subcontract_orders()
			itemwise_consumed_qty = defaultdict(float)
			if self.get("is_old_subcontracting_flow"):
				doctypes = ["Purchase Receipt", "Purchase Invoice"]
			else:
				doctypes = ["Subcontracting Receipt"]

			for doctype in doctypes:
				consumed_items, receipt_items = self.__update_consumed_materials(
					doctype, return_consumed_items=True
				)

				for row in consumed_items:
					key = (row.rm_item_code, row.main_item_code, receipt_items.get(row.reference_name))
					itemwise_consumed_qty[key] += row.consumed_qty

			self.__update_consumed_qty_in_subcontract_order(itemwise_consumed_qty)

	def update_ordered_and_reserved_qty(self):
		sco_map = {}
		for item in self.get("items"):
			if self.doctype == "Subcontracting Receipt" and item.subcontracting_order:
				sco_map.setdefault(item.subcontracting_order, []).append(item.subcontracting_order_item)

		for sco, sco_item_rows in sco_map.items():
			if sco and sco_item_rows:
				sco_doc = frappe.get_doc("Subcontracting Order", sco)

				if sco_doc.status in ["Closed", "Cancelled"]:
					frappe.throw(
						_("{0} {1} is cancelled or closed").format(_("Subcontracting Order"), sco),
						frappe.InvalidStatusError,
					)

				sco_doc.update_ordered_qty_for_subcontracting(sco_item_rows)
				sco_doc.update_reserved_qty_for_subcontracting()

	def make_sl_entries_for_supplier_warehouse(self, sl_entries):
		if hasattr(self, "supplied_items"):
			for item in self.get("supplied_items"):
				# negative quantity is passed, as raw material qty has to be decreased
				# when SCR is submitted and it has to be increased when SCR is cancelled
				sl_entries.append(
					self.get_sl_entries(
						item,
						{
							"item_code": item.rm_item_code,
							"warehouse": self.supplier_warehouse,
							"actual_qty": -1 * flt(item.consumed_qty),
							"dependant_sle_voucher_detail_no": item.reference_name,
						},
					)
				)

	def update_stock_ledger(self, allow_negative_stock=False, via_landed_cost_voucher=False):
		self.update_ordered_and_reserved_qty()

		sl_entries = []
		stock_items = self.get_stock_items()

		for item in self.get("items"):
			if item.item_code in stock_items and item.warehouse:
				scr_qty = flt(item.qty) * flt(item.conversion_factor)

				if scr_qty:
					sle = self.get_sl_entries(
						item, {"actual_qty": flt(scr_qty), "serial_no": cstr(item.serial_no).strip()}
					)
					rate_db_precision = 6 if cint(self.precision("rate", item)) <= 6 else 9
					incoming_rate = flt(item.rate, rate_db_precision)
					sle.update(
						{
							"incoming_rate": incoming_rate,
							"recalculate_rate": 1,
						}
					)
					sl_entries.append(sle)

				if flt(item.rejected_qty) != 0:
					sl_entries.append(
						self.get_sl_entries(
							item,
							{
								"warehouse": item.rejected_warehouse,
								"actual_qty": flt(item.rejected_qty) * flt(item.conversion_factor),
								"serial_no": cstr(item.rejected_serial_no).strip(),
								"incoming_rate": 0.0,
								"recalculate_rate": 1,
							},
						)
					)

		self.make_sl_entries_for_supplier_warehouse(sl_entries)
		self.make_sl_entries(
			sl_entries,
			allow_negative_stock=allow_negative_stock,
			via_landed_cost_voucher=via_landed_cost_voucher,
		)

	def get_supplied_items_cost(self, item_row_id, reset_outgoing_rate=True):
		supplied_items_cost = 0.0
		for item in self.get("supplied_items"):
			if item.reference_name == item_row_id:
				if (
					self.get("is_old_subcontracting_flow")
					and reset_outgoing_rate
					and frappe.get_cached_value("Item", item.rm_item_code, "is_stock_item")
				):
					rate = get_incoming_rate(
						{
							"item_code": item.rm_item_code,
							"warehouse": self.supplier_warehouse,
							"posting_date": self.posting_date,
							"posting_time": self.posting_time,
							"qty": -1 * item.consumed_qty,
							"serial_no": item.serial_no,
							"batch_no": item.batch_no,
						}
					)

					if rate > 0:
						item.rate = rate

				item.amount = flt(flt(item.consumed_qty) * flt(item.rate), item.precision("amount"))
				supplied_items_cost += item.amount

		return supplied_items_cost

	def set_subcontracting_order_status(self):
		if self.doctype == "Subcontracting Order":
			self.update_status()
		elif self.doctype == "Subcontracting Receipt":
			self.__get_subcontract_orders

			if self.subcontract_orders:
				for sco in set(self.subcontract_orders):
					sco_doc = frappe.get_doc("Subcontracting Order", sco)
					sco_doc.update_status()

	def set_missing_values_in_additional_costs(self):
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
			for item in self.items:
				item.additional_cost_per_qty = 0

	@frappe.whitelist()
	def get_current_stock(self):
		if self.doctype in ["Purchase Receipt", "Subcontracting Receipt"]:
			for item in self.get("supplied_items"):
				if self.supplier_warehouse:
					actual_qty = frappe.db.get_value(
						"Bin",
						{"item_code": item.rm_item_code, "warehouse": self.supplier_warehouse},
						"actual_qty",
					)
					item.current_stock = flt(actual_qty)

	@property
	def sub_contracted_items(self):
		if not hasattr(self, "_sub_contracted_items"):
			self._sub_contracted_items = []
			item_codes = list(set(item.item_code for item in self.get("items")))
			if item_codes:
				items = frappe.get_all(
					"Item", filters={"name": ["in", item_codes], "is_sub_contracted_item": 1}
				)
				self._sub_contracted_items = [item.name for item in items]

		return self._sub_contracted_items


def get_item_details(items):
	item = frappe.qb.DocType("Item")
	item_list = (
		frappe.qb.from_(item)
		.select(item.item_code, item.item_name, item.description, item.allow_alternative_item)
		.where(item.name.isin(items))
		.run(as_dict=True)
	)

	item_details = {}
	for item in item_list:
		item_details[item.item_code] = item

	return item_details


@frappe.whitelist()
def make_rm_stock_entry(
	subcontract_order, rm_items=None, order_doctype="Subcontracting Order", target_doc=None
):
	if subcontract_order:
		subcontract_order = frappe.get_doc(order_doctype, subcontract_order)

		if not rm_items:
			if not subcontract_order.supplied_items:
				frappe.throw(_("No item available for transfer."))

			rm_items = subcontract_order.supplied_items

		fg_item_code_list = list(
			set(item.get("main_item_code") or item.get("item_code") for item in rm_items)
		)

		if fg_item_code_list:
			rm_item_code_list = tuple(set(item.get("rm_item_code") for item in rm_items))
			item_wh = get_item_details(rm_item_code_list)

			field_no_map, rm_detail_field = "purchase_order", "sco_rm_detail"
			if order_doctype == "Purchase Order":
				field_no_map, rm_detail_field = "subcontracting_order", "po_detail"

			if target_doc and target_doc.get("items"):
				target_doc.items = []

			stock_entry = get_mapped_doc(
				order_doctype,
				subcontract_order.name,
				{
					order_doctype: {
						"doctype": "Stock Entry",
						"field_map": {
							"supplier": "supplier",
							"supplier_name": "supplier_name",
							"supplier_address": "supplier_address",
							"to_warehouse": "supplier_warehouse",
						},
						"field_no_map": [field_no_map],
						"validation": {
							"docstatus": ["=", 1],
						},
					},
				},
				target_doc,
				ignore_child_tables=True,
			)

			stock_entry.purpose = "Send to Subcontractor"

			if order_doctype == "Purchase Order":
				stock_entry.purchase_order = subcontract_order.name
			else:
				stock_entry.subcontracting_order = subcontract_order.name

			stock_entry.set_stock_entry_type()

			for fg_item_code in fg_item_code_list:
				for rm_item in rm_items:

					if rm_item.get("main_item_code") == fg_item_code or rm_item.get("item_code") == fg_item_code:
						rm_item_code = rm_item.get("rm_item_code")

						items_dict = {
							rm_item_code: {
								rm_detail_field: rm_item.get("name"),
								"item_name": rm_item.get("item_name")
								or item_wh.get(rm_item_code, {}).get("item_name", ""),
								"description": item_wh.get(rm_item_code, {}).get("description", ""),
								"qty": rm_item.get("qty")
								or max(rm_item.get("required_qty") - rm_item.get("total_supplied_qty"), 0),
								"from_warehouse": rm_item.get("warehouse") or rm_item.get("reserve_warehouse"),
								"to_warehouse": subcontract_order.supplier_warehouse,
								"stock_uom": rm_item.get("stock_uom"),
								"serial_no": rm_item.get("serial_no"),
								"batch_no": rm_item.get("batch_no"),
								"main_item_code": fg_item_code,
								"allow_alternative_item": item_wh.get(rm_item_code, {}).get("allow_alternative_item"),
							}
						}

						stock_entry.add_to_stock_entry_detail(items_dict)

			if target_doc:
				return stock_entry
			else:
				return stock_entry.as_dict()
		else:
			frappe.throw(_("No Items selected for transfer."))


def add_items_in_ste(
	ste_doc, row, qty, rm_details, rm_detail_field="sco_rm_detail", batch_no=None
):
	item = ste_doc.append("items", row.item_details)

	rm_detail = list(set(row.get(f"{rm_detail_field}s")).intersection(rm_details))
	item.update(
		{
			"qty": qty,
			"batch_no": batch_no,
			"basic_rate": row.item_details["rate"],
			rm_detail_field: rm_detail[0] if rm_detail else "",
			"s_warehouse": row.item_details["t_warehouse"],
			"t_warehouse": row.item_details["s_warehouse"],
			"item_code": row.item_details["rm_item_code"],
			"subcontracted_item": row.item_details["main_item_code"],
			"serial_no": "\n".join(row.serial_no) if row.serial_no else "",
		}
	)


def make_return_stock_entry_for_subcontract(
	available_materials, order_doc, rm_details, order_doctype="Subcontracting Order"
):
	ste_doc = get_mapped_doc(
		order_doctype,
		order_doc.name,
		{
			order_doctype: {
				"doctype": "Stock Entry",
				"field_no_map": ["purchase_order", "subcontracting_order"],
			},
		},
		ignore_child_tables=True,
	)

	ste_doc.purpose = "Material Transfer"

	if order_doctype == "Purchase Order":
		ste_doc.purchase_order = order_doc.name
		rm_detail_field = "po_detail"
	else:
		ste_doc.subcontracting_order = order_doc.name
		rm_detail_field = "sco_rm_detail"
	ste_doc.company = order_doc.company
	ste_doc.is_return = 1

	for key, value in available_materials.items():
		if not value.qty:
			continue

		if value.batch_no:
			for batch_no, qty in value.batch_no.items():
				if qty > 0:
					add_items_in_ste(ste_doc, value, value.qty, rm_details, rm_detail_field, batch_no)
		else:
			add_items_in_ste(ste_doc, value, value.qty, rm_details, rm_detail_field)

	ste_doc.set_stock_entry_type()
	ste_doc.calculate_rate_and_amount()

	return ste_doc


@frappe.whitelist()
def get_materials_from_supplier(
	subcontract_order, rm_details, order_doctype="Subcontracting Order"
):
	if isinstance(rm_details, str):
		rm_details = json.loads(rm_details)

	doc = frappe.get_cached_doc(order_doctype, subcontract_order)
	doc.initialized_fields()
	doc.subcontract_orders = [doc.name]
	doc.get_available_materials()

	if not doc.available_materials:
		frappe.throw(
			_("Materials are already received against the {0} {1}").format(order_doctype, subcontract_order)
		)

	return make_return_stock_entry_for_subcontract(
		doc.available_materials, doc, rm_details, order_doctype
	)
