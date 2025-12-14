# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from erpnext.manufacturing.doctype.bom.bom import get_bom_items_as_dict


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
			frappe.throw(f"Stock Entry Type {self.name} cannot be set as standard")


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
		self.stock_entry.fg_completed_qty = self.for_quantity
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
			item_dict = {}
			if not item_dict:
				item_dict = self.get_items_from_job_card()

			backflush_based_on = frappe.db.get_single_value(
				"Manufacturing Settings", "backflush_raw_materials_based_on"
			)

			for item_code, _dict in item_dict.items():
				_dict.from_warehouse = self.source_wh.get(item_code) or self.wip_warehouse
				_dict.to_warehouse = ""

				if backflush_based_on != "BOM":
					calculated_qty = flt(_dict.transferred_qty) - flt(_dict.consumed_qty)
					if calculated_qty < 0:
						frappe.throw(
							_("Consumed quantity of item {0} exceeds transferred quantity.").format(item_code)
						)

					_dict.qty = calculated_qty

			self.stock_entry.add_to_stock_entry_detail(item_dict)

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
			"to_warehouse": self.fg_warehouse,
			"from_warehouse": "",
			"qty": self.for_quantity,
			"item_name": item.item_name,
			"description": item.description,
			"stock_uom": item.stock_uom,
			"expense_account": item.get("expense_account"),
			"cost_center": item.get("buying_cost_center"),
			"is_finished_item": 1,
		}

		self.stock_entry.add_to_stock_entry_detail({self.production_item: args}, bom_no=self.bom_no)
