import copy
from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import cint, flt, get_link_to_form

from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos


class Subcontracting:
	def set_materials_for_subcontracted_items(self, raw_material_table):
		if self.doctype == "Purchase Invoice" and not self.update_stock:
			return

		self.raw_material_table = raw_material_table
		self.__identify_change_in_item_table()
		self.__prepare_supplied_items()
		self.__validate_supplied_items()

	def __prepare_supplied_items(self):
		self.initialized_fields()
		self.__get_purchase_orders()
		self.__get_pending_qty_to_receive()
		self.get_available_materials()
		self.__remove_changed_rows()
		self.__set_supplied_items()

	def initialized_fields(self):
		self.available_materials = frappe._dict()
		self.__transferred_items = frappe._dict()
		self.alternative_item_details = frappe._dict()
		self.__get_backflush_based_on()

	def __get_backflush_based_on(self):
		self.backflush_based_on = frappe.db.get_single_value(
			"Buying Settings", "backflush_raw_materials_of_subcontract_based_on"
		)

	def __get_purchase_orders(self):
		self.purchase_orders = []

		if self.doctype == "Purchase Order":
			return

		self.purchase_orders = [d.purchase_order for d in self.items if d.purchase_order]

	def __identify_change_in_item_table(self):
		self.__changed_name = []
		self.__reference_name = []

		if self.doctype == "Purchase Order" or self.is_new():
			self.set(self.raw_material_table, [])
			return

		item_dict = self.__get_data_before_save()
		if not item_dict:
			return True

		for n_row in self.items:
			self.__reference_name.append(n_row.name)
			if (n_row.name not in item_dict) or (n_row.item_code, n_row.qty) != item_dict[n_row.name]:
				self.__changed_name.append(n_row.name)

			if item_dict.get(n_row.name):
				del item_dict[n_row.name]

		self.__changed_name.extend(item_dict.keys())

	def __get_data_before_save(self):
		item_dict = {}
		if self.doctype in ["Purchase Receipt", "Purchase Invoice"] and self._doc_before_save:
			for row in self._doc_before_save.get("items"):
				item_dict[row.name] = (row.item_code, row.qty)

		return item_dict

	def get_available_materials(self):
		"""Get the available raw materials which has been transferred to the supplier.
		available_materials = {
		        (item_code, subcontracted_item, purchase_order): {
		                'qty': 1, 'serial_no': [ABC], 'batch_no': {'batch1': 1}, 'data': item_details
		        }
		}
		"""
		if not self.purchase_orders:
			return

		for row in self.__get_transferred_items():
			key = (row.rm_item_code, row.main_item_code, row.purchase_order)

			if key not in self.available_materials:
				self.available_materials.setdefault(
					key,
					frappe._dict(
						{
							"qty": 0,
							"serial_no": [],
							"batch_no": defaultdict(float),
							"item_details": row,
							"po_details": [],
						}
					),
				)

			details = self.available_materials[key]
			details.qty += row.qty
			details.po_details.append(row.po_detail)

			if row.serial_no:
				details.serial_no.extend(get_serial_nos(row.serial_no))

			if row.batch_no:
				details.batch_no[row.batch_no] += row.qty

			self.__set_alternative_item_details(row)

		self.__transferred_items = copy.deepcopy(self.available_materials)
		for doctype in ["Purchase Receipt", "Purchase Invoice"]:
			self.__update_consumed_materials(doctype)

	def __update_consumed_materials(self, doctype, return_consumed_items=False):
		"""Deduct the consumed materials from the available materials."""

		pr_items = self.__get_received_items(doctype)
		if not pr_items:
			return ([], {}) if return_consumed_items else None

		pr_items = {d.name: d.get(self.get("po_field") or "purchase_order") for d in pr_items}
		consumed_materials = self.__get_consumed_items(doctype, pr_items.keys())

		if return_consumed_items:
			return (consumed_materials, pr_items)

		for row in consumed_materials:
			key = (row.rm_item_code, row.main_item_code, pr_items.get(row.reference_name))
			if not self.available_materials.get(key):
				continue

			self.available_materials[key]["qty"] -= row.consumed_qty
			if row.serial_no:
				self.available_materials[key]["serial_no"] = list(
					set(self.available_materials[key]["serial_no"]) - set(get_serial_nos(row.serial_no))
				)

			if row.batch_no:
				self.available_materials[key]["batch_no"][row.batch_no] -= row.consumed_qty

	def __get_transferred_items(self):
		fields = ["`tabStock Entry`.`purchase_order`"]
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
			"po_detail",
		]

		if self.backflush_based_on == "BOM":
			child_table_fields.append("original_item")

		for field in child_table_fields:
			fields.append(f"`tabStock Entry Detail`.`{field}` As {alias_dict.get(field, field)}")

		filters = [
			["Stock Entry", "docstatus", "=", 1],
			["Stock Entry", "purpose", "=", "Send to Subcontractor"],
			["Stock Entry", "purchase_order", "in", self.purchase_orders],
		]

		return frappe.get_all("Stock Entry", fields=fields, filters=filters)

	def __get_received_items(self, doctype):
		fields = []
		self.po_field = "purchase_order"

		for field in ["name", self.po_field, "parent"]:
			fields.append(f"`tab{doctype} Item`.`{field}`")

		filters = [
			[doctype, "docstatus", "=", 1],
			[f"{doctype} Item", self.po_field, "in", self.purchase_orders],
		]
		if doctype == "Purchase Invoice":
			filters.append(["Purchase Invoice", "update_stock", "=", 1])

		return frappe.get_all(f"{doctype}", fields=fields, filters=filters)

	def __get_consumed_items(self, doctype, pr_items):
		return frappe.get_all(
			"Purchase Receipt Item Supplied",
			fields=[
				"serial_no",
				"rm_item_code",
				"reference_name",
				"batch_no",
				"consumed_qty",
				"main_item_code",
			],
			filters={"docstatus": 1, "reference_name": ("in", list(pr_items)), "parenttype": doctype},
		)

	def __set_alternative_item_details(self, row):
		if row.get("original_item"):
			self.alternative_item_details[row.get("original_item")] = row

	def __get_pending_qty_to_receive(self):
		"""Get qty to be received against the purchase order."""

		self.qty_to_be_received = defaultdict(float)

		if (
			self.doctype != "Purchase Order" and self.backflush_based_on != "BOM" and self.purchase_orders
		):
			for row in frappe.get_all(
				"Purchase Order Item",
				fields=["item_code", "(qty - received_qty) as qty", "parent", "name"],
				filters={"docstatus": 1, "parent": ("in", self.purchase_orders)},
			):

				self.qty_to_be_received[(row.item_code, row.parent)] += row.qty

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

	def __remove_changed_rows(self):
		if not self.__changed_name:
			return

		i = 1
		self.set(self.raw_material_table, [])
		for d in self._doc_before_save.supplied_items:
			if d.reference_name in self.__changed_name:
				continue

			if d.reference_name not in self.__reference_name:
				continue

			d.idx = i
			self.append("supplied_items", d)

			i += 1

	def __set_supplied_items(self):
		self.bom_items = {}

		has_supplied_items = True if self.get(self.raw_material_table) else False
		for row in self.items:
			if self.doctype != "Purchase Order" and (
				(self.__changed_name and row.name not in self.__changed_name)
				or (has_supplied_items and not self.__changed_name)
			):
				continue

			if self.doctype == "Purchase Order" or self.backflush_based_on == "BOM":
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
					if (key[1], key[2]) == (row.item_code, row.purchase_order) and transfer_item.qty > 0:
						qty = self.__get_qty_based_on_material_transfer(row, transfer_item) or 0
						transfer_item.qty -= qty
						self.__add_supplied_item(row, transfer_item.get("item_details"), qty)

				if self.qty_to_be_received:
					self.qty_to_be_received[(row.item_code, row.purchase_order)] -= row.qty

	def __update_reserve_warehouse(self, row, item):
		if self.doctype == "Purchase Order":
			row.reserve_warehouse = self.set_reserve_warehouse or item.warehouse

	def __get_qty_based_on_material_transfer(self, item_row, transfer_item):
		key = (item_row.item_code, item_row.purchase_order)

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

	def __set_alternative_item(self, bom_item):
		if self.alternative_item_details.get(bom_item.rm_item_code):
			bom_item.update(self.alternative_item_details[bom_item.rm_item_code])

	def __add_supplied_item(self, item_row, bom_item, qty):
		bom_item.conversion_factor = item_row.conversion_factor
		rm_obj = self.append(self.raw_material_table, bom_item)
		rm_obj.reference_name = item_row.name

		if self.doctype == "Purchase Order":
			rm_obj.required_qty = qty
		else:
			rm_obj.consumed_qty = 0
			rm_obj.purchase_order = item_row.purchase_order
			self.__set_batch_nos(bom_item, item_row, rm_obj, qty)

		rm_obj.amount = flt(rm_obj.required_qty) * flt(rm_obj.rate)

	def __set_batch_nos(self, bom_item, item_row, rm_obj, qty):
		key = (rm_obj.rm_item_code, item_row.item_code, item_row.purchase_order)

		if self.available_materials.get(key) and self.available_materials[key]["batch_no"]:
			new_rm_obj = None
			for batch_no, batch_qty in self.available_materials[key]["batch_no"].items():
				if batch_qty >= qty:
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

	def __set_consumed_qty(self, rm_obj, consumed_qty, required_qty=0):
		rm_obj.required_qty = required_qty
		rm_obj.consumed_qty = consumed_qty

	def __set_batch_no_as_per_qty(self, item_row, rm_obj, batch_no, qty):
		rm_obj.update(
			{
				"consumed_qty": qty,
				"batch_no": batch_no,
				"required_qty": qty,
				"purchase_order": item_row.purchase_order,
			}
		)

		self.__set_serial_nos(item_row, rm_obj)

	def __set_serial_nos(self, item_row, rm_obj):
		key = (rm_obj.rm_item_code, item_row.item_code, item_row.purchase_order)
		if self.available_materials.get(key) and self.available_materials[key]["serial_no"]:
			used_serial_nos = self.available_materials[key]["serial_no"][0 : cint(rm_obj.consumed_qty)]
			rm_obj.serial_no = "\n".join(used_serial_nos)

			# Removed the used serial nos from the list
			for sn in used_serial_nos:
				self.available_materials[key]["serial_no"].remove(sn)

	def set_consumed_qty_in_po(self):
		# Update consumed qty back in the purchase order
		if self.is_subcontracted != "Yes":
			return

		self.__get_purchase_orders()
		itemwise_consumed_qty = defaultdict(float)
		for doctype in ["Purchase Receipt", "Purchase Invoice"]:
			consumed_items, pr_items = self.__update_consumed_materials(doctype, return_consumed_items=True)

			for row in consumed_items:
				key = (row.rm_item_code, row.main_item_code, pr_items.get(row.reference_name))
				itemwise_consumed_qty[key] += row.consumed_qty

		self.__update_consumed_qty_in_po(itemwise_consumed_qty)

	def __update_consumed_qty_in_po(self, itemwise_consumed_qty):
		fields = ["main_item_code", "rm_item_code", "parent", "supplied_qty", "name"]
		filters = {"docstatus": 1, "parent": ("in", self.purchase_orders)}

		for row in frappe.get_all(
			"Purchase Order Item Supplied", fields=fields, filters=filters, order_by="idx"
		):
			key = (row.rm_item_code, row.main_item_code, row.parent)
			consumed_qty = itemwise_consumed_qty.get(key, 0)

			if row.supplied_qty < consumed_qty:
				consumed_qty = row.supplied_qty

			itemwise_consumed_qty[key] -= consumed_qty
			frappe.db.set_value("Purchase Order Item Supplied", row.name, "consumed_qty", consumed_qty)

	def __validate_supplied_items(self):
		if self.doctype not in ["Purchase Invoice", "Purchase Receipt"]:
			return

		for row in self.get(self.raw_material_table):
			key = (row.rm_item_code, row.main_item_code, row.purchase_order)
			if not self.__transferred_items or not self.__transferred_items.get(key):
				return

			self.__validate_batch_no(row, key)
			self.__validate_serial_no(row, key)

	def __validate_batch_no(self, row, key):
		if row.get("batch_no") and row.get("batch_no") not in self.__transferred_items.get(key).get(
			"batch_no"
		):
			link = get_link_to_form("Purchase Order", row.purchase_order)
			msg = f'The Batch No {frappe.bold(row.get("batch_no"))} has not supplied against the Purchase Order {link}'
			frappe.throw(_(msg), title=_("Incorrect Batch Consumed"))

	def __validate_serial_no(self, row, key):
		if row.get("serial_no"):
			serial_nos = get_serial_nos(row.get("serial_no"))
			incorrect_sn = set(serial_nos).difference(self.__transferred_items.get(key).get("serial_no"))

			if incorrect_sn:
				incorrect_sn = "\n".join(incorrect_sn)
				link = get_link_to_form("Purchase Order", row.purchase_order)
				msg = f"The Serial Nos {incorrect_sn} has not supplied against the Purchase Order {link}"
				frappe.throw(_(msg), title=_("Incorrect Serial Number Consumed"))
