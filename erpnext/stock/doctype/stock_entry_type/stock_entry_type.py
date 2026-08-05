# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import copy
from collections import defaultdict

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt


class StockEntryType(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		add_to_transit: DF.Check
		is_standard: DF.Check
		purpose: DF.Literal[
			"Material Issue",
			"Material Receipt",
			"Material Transfer",
			"Material Transfer for Manufacture",
			"Material Consumption for Manufacture",
			"Manufacture",
			"Repack",
			"Send to Subcontractor",
			"Disassemble",
			"Receive from Customer",
			"Return Raw Material to Customer",
			"Subcontracting Delivery",
			"Subcontracting Return",
		]
	# end: auto-generated types

	def validate(self):
		self.validate_standard_type()
		if self.add_to_transit and self.purpose != "Material Transfer":
			self.add_to_transit = 0

	def validate_standard_type(self):
		if self.is_standard and self.name not in [
			"Material Issue",
			"Material Receipt",
			"Material Transfer",
			"Material Transfer for Manufacture",
			"Material Consumption for Manufacture",
			"Manufacture",
			"Repack",
			"Send to Subcontractor",
			"Disassemble",
			"Receive from Customer",
			"Return Raw Material to Customer",
			"Subcontracting Delivery",
			"Subcontracting Return",
		]:
			frappe.throw(_("Stock Entry Type {0} cannot be set as standard").format(self.name))


class ManufactureEntry:
	def __init__(self, kwargs) -> None:
		for key, value in kwargs.items():
			setattr(self, key, value)

	def make_stock_entry(self):
		self.stock_entry = frappe.new_doc("Stock Entry")
		self.stock_entry.purpose = self.purpose
		self.stock_entry.company = self.company

		if self.bom_no:
			self.stock_entry.from_bom = 1
			self.stock_entry.bom_no = self.bom_no
			self.stock_entry.use_multi_level_bom = 1

		self.stock_entry.fg_completed_qty = self.for_quantity
		self.stock_entry.process_loss_qty = self.process_loss_qty
		self.stock_entry.project = self.project
		self.stock_entry.job_card = self.job_card
		self.stock_entry.set_stock_entry_type()
		self.stock_entry.work_order = self.work_order

		self.prepare_source_warehouse()
		self.add_raw_materials()
		self.add_finished_good()

	def prepare_source_warehouse(self):
		self.source_wh = {}
		if self.skip_material_transfer:
			if not self.backflush_from_wip_warehouse:
				self.source_wh = frappe._dict(
					frappe.get_all(
						"Job Card Item",
						filters={"parent": self.job_card},
						fields=["item_code", "source_warehouse"],
						as_list=1,
					)
				)

	def add_raw_materials(self):
		from erpnext.stock.doctype.stock_entry.services.manufacturing import (
			set_previous_operation_serial_batch,
		)

		if self.job_card:
			item_dict = {}
			if not item_dict:
				item_dict = self.get_items_from_job_card()

			backflush_based_on = frappe.db.get_single_value(
				"Manufacturing Settings", "backflush_raw_materials_based_on"
			)

			if self.bom_no:
				if based_on := frappe.get_cached_value("BOM", self.bom_no, "backflush_based_on"):
					backflush_based_on = based_on

			available_serial_batches = frappe._dict({})
			if backflush_based_on != "BOM":
				available_serial_batches = self.get_transferred_serial_batches()

			for item_code, _dict in item_dict.items():
				_dict.s_warehouse = self.source_wh.get(item_code) or self.wip_warehouse
				_dict.t_warehouse = ""
				_dict.item_code = item_code

				if backflush_based_on != "BOM" and not self.skip_material_transfer:
					calculated_qty = flt(_dict.transferred_qty) - flt(_dict.consumed_qty)
					if calculated_qty < 0:
						frappe.throw(
							_("Consumed quantity of item {0} exceeds transferred quantity.").format(item_code)
						)

					_dict.qty = calculated_qty
					for row_dict in self.split_by_available_serial_batches(_dict, available_serial_batches):
						self.stock_entry.append("items", row_dict)
					continue
				elif self.skip_material_transfer:
					set_previous_operation_serial_batch(self.stock_entry, _dict)

				self.stock_entry.append("items", _dict)

	def parse_available_serial_batches(self, item_dict, available_serial_batches):
		key = (item_dict.item_code, item_dict.from_warehouse)
		if key not in available_serial_batches:
			return [], {}

		_avl_dict = available_serial_batches[key]

		qty = item_dict.qty
		serial_nos = []
		batches = frappe._dict()

		if _avl_dict.serial_nos:
			serial_nos = _avl_dict.serial_nos[: cint(qty)]
			qty -= len(serial_nos)
			for sn in serial_nos:
				_avl_dict.serial_nos.remove(sn)

		elif _avl_dict.batches:
			batches = frappe._dict()
			for batch_no, batch_qty in _avl_dict.batches.items():
				if qty <= 0:
					break
				if batch_qty <= qty:
					batches[batch_no] = batch_qty
					qty -= batch_qty
				else:
					batches[batch_no] = qty
					qty = 0

			for _used_batch_no in batches:
				_avl_dict.batches[_used_batch_no] -= batches[_used_batch_no]
				if _avl_dict.batches[_used_batch_no] <= 0:
					del _avl_dict.batches[_used_batch_no]

		return serial_nos, batches

	def split_by_available_serial_batches(self, item_dict, available_serial_batches):
		"""Returns one row per batch (batch_no is single-valued) or a single row with every
		serial no joined into the plain field (which already holds multiple, newline-separated)."""
		serial_nos, batches = self.parse_available_serial_batches(item_dict, available_serial_batches)

		if serial_nos:
			item_dict.use_serial_batch_fields = 1
			item_dict.serial_no = "\n".join(serial_nos)
			return [item_dict]

		if not batches:
			return [item_dict]

		rows = []
		for batch_no, qty in batches.items():
			row = copy.deepcopy(item_dict)
			row.use_serial_batch_fields = 1
			row.batch_no = batch_no
			row.qty = qty
			rows.append(row)

		return rows

	def get_stock_entry_data(self):
		stock_entry = frappe.qb.DocType("Stock Entry")
		stock_entry_detail = frappe.qb.DocType("Stock Entry Detail")
		sll = frappe.qb.DocType("Stock Location Ledger")

		return (
			frappe.qb.from_(stock_entry)
			.inner_join(stock_entry_detail)
			.on(stock_entry.name == stock_entry_detail.parent)
			.inner_join(sll)
			.on(
				(sll.voucher_type == "Stock Entry")
				& (sll.voucher_no == stock_entry.name)
				& (sll.voucher_detail_no == stock_entry_detail.name)
			)
			.select(
				stock_entry_detail.item_code,
				sll.serial_no,
				sll.batch_no,
				sll.qty,
				sll.warehouse,
				stock_entry_detail.s_warehouse,
				stock_entry_detail.t_warehouse,
				stock_entry.purpose,
			)
			.where(
				(stock_entry.job_card == self.job_card)
				& (sll.docstatus == 1)
				& (stock_entry.docstatus == 1)
				& (stock_entry.purpose.isin(["Material Transfer for Manufacture", "Manufacture"]))
			)
			.orderby(stock_entry.posting_date, stock_entry.posting_time)
		).run(as_dict=True)

	def get_transferred_serial_batches(self):
		available_serial_batches = frappe._dict({})

		stock_entry_data = self.get_stock_entry_data()

		for row in stock_entry_data:
			warehouse = (
				row.t_warehouse if row.purpose == "Material Transfer for Manufacture" else row.s_warehouse
			)
			if not warehouse or row.warehouse != warehouse:
				continue

			key = (row.item_code, warehouse)
			if key not in available_serial_batches:
				available_serial_batches[key] = frappe._dict(
					{
						"batches": defaultdict(float),
						"serial_nos": [],
					}
				)

			_avl_dict = available_serial_batches[key]

			if row.serial_no:
				if row.qty > 0:
					_avl_dict.serial_nos.append(row.serial_no)
				elif row.serial_no in _avl_dict.serial_nos:
					_avl_dict.serial_nos.remove(row.serial_no)
			if row.batch_no:
				_avl_dict.batches[row.batch_no] += flt(row.qty)

		return available_serial_batches

	def get_items_from_job_card(self):
		item_dict = {}
		items = frappe.get_all(
			"Job Card Item",
			fields=[
				"name as job_card_item",
				"item_code",
				"source_warehouse",
				"required_qty as qty",
				"transferred_qty",
				"consumed_qty",
				"item_name",
				"uom",
				"stock_uom",
				"item_group",
				"description",
			],
			filters={"parent": self.job_card},
		)

		for item in items:
			key = item.item_code

			if key in item_dict:
				item_dict[key]["qty"] += flt(item.qty)
			else:
				item_dict[key] = item

		for item, item_details in item_dict.items():
			for d in [
				["Account", "expense_account", "stock_adjustment_account"],
				["Cost Center", "cost_center", "cost_center"],
				["Warehouse", "default_warehouse", ""],
			]:
				company_in_record = frappe.db.get_value(d[0], item_details.get(d[1]), "company")
				if not item_details.get(d[1]) or (company_in_record and self.company != company_in_record):
					item_dict[item][d[1]] = (
						frappe.get_cached_value("Company", self.company, d[2]) if d[2] else None
					)

		return item_dict

	def add_finished_good(self):
		from erpnext.stock.doctype.item.item import get_item_defaults

		item = get_item_defaults(self.production_item, self.company)

		args = {
			"t_warehouse": self.fg_warehouse,
			"s_warehouse": "",
			"qty": self.for_quantity - self.process_loss_qty,
			"item_name": item.item_name,
			"description": item.description,
			"stock_uom": item.stock_uom,
			"expense_account": item.get("expense_account"),
			"cost_center": item.get("buying_cost_center"),
			"is_finished_item": 1,
			"item_code": self.production_item,
		}

		self.stock_entry.append("items", args)
