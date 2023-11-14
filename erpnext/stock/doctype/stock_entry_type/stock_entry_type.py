# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document

from erpnext.manufacturing.doctype.bom.bom import get_bom_items_as_dict


class StockEntryType(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		add_to_transit: DF.Check
		purpose: DF.Literal[
			"",
			"Material Issue",
			"Material Receipt",
			"Material Transfer",
			"Material Transfer for Manufacture",
			"Material Consumption for Manufacture",
			"Manufacture",
			"Repack",
			"Send to Subcontractor",
		]
	# end: auto-generated types

	def validate(self):
		if self.add_to_transit and self.purpose != "Material Transfer":
			self.add_to_transit = 0


class ManufactureEntry:
	def __init__(self, kwargs) -> None:
		for key, value in kwargs.items():
			setattr(self, key, value)

	def make_stock_entry(self):
		self.stock_entry = frappe.new_doc("Stock Entry")
		self.stock_entry.purpose = self.purpose
		self.stock_entry.company = self.company
		self.stock_entry.from_bom = 1
		self.stock_entry.bom_no = self.bom_no
		self.stock_entry.use_multi_level_bom = 1
		self.stock_entry.fg_completed_qty = self.qty_to_manufacture
		self.stock_entry.project = self.project
		self.stock_entry.job_card = self.job_card
		self.stock_entry.work_order = self.work_order
		self.stock_entry.set_stock_entry_type()

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
		if self.job_card:
			item_dict = get_bom_items_as_dict(
				self.bom_no,
				self.company,
				qty=self.qty_to_manufacture,
				fetch_exploded=False,
				fetch_qty_in_stock_uom=False,
			)

			for item_code, _dict in item_dict.items():
				_dict.from_warehouse = self.source_wh.get(item_code) or self.wip_warehouse
				_dict.to_warehouse = ""

			self.stock_entry.add_to_stock_entry_detail(item_dict)

	def add_finished_good(self):
		from erpnext.stock.doctype.item.item import get_item_defaults

		item = get_item_defaults(self.production_item, self.company)

		args = {
			"to_warehouse": self.fg_warehouse,
			"from_warehouse": "",
			"qty": self.qty_to_manufacture,
			"item_name": item.item_name,
			"description": item.description,
			"stock_uom": item.stock_uom,
			"expense_account": item.get("expense_account"),
			"cost_center": item.get("buying_cost_center"),
			"is_finished_item": 1,
		}

		self.stock_entry.add_to_stock_entry_detail({self.production_item: args}, bom_no=self.bom_no)
