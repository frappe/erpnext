# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint, flt

BOM_FIELDS = ("company", "rm_cost_as_per", "project", "currency", "conversion_rate", "buying_price_list")


class BOMPlan:
	def __init__(self, design):
		self.design = design
		self.parts = {row.node_id: row for row in design.items}

	def get_node_item(self, node_id) -> str | None:
		if not cint(node_id):
			return self.design.item_code

		return self.parts[cint(node_id)].item_code

	def get_bom_quantity(self, node_id: int) -> float:
		return 1 if node_id else flt(self.design.qty) or 1

	def get_bom_node_ids(self) -> list[int]:
		raise NotImplementedError

	def get_problems(self) -> list[str]:
		raise NotImplementedError

	def get_bom_order(self) -> list[int]:
		raise NotImplementedError

	def make_bom(self, node_id: int, boms: dict[str, str]) -> str:
		raise NotImplementedError

	def validate_can_make_boms(self):
		problems = self.get_problems()
		if problems:
			frappe.throw(problems, title=_("Fix These Before Creating BOMs"), as_list=True)

	def make_boms(self) -> dict[str, str]:
		self.validate_can_make_boms()
		boms = self.get_existing_boms()
		for node_id in self.get_bom_order():
			item_code = self.get_node_item(node_id)
			if item_code not in boms:
				boms[item_code] = self.make_bom(node_id, boms)

		return boms

	def get_existing_boms(self) -> dict[str, str]:
		if self.design.is_new():
			return {}

		return dict(
			frappe.get_all(
				"BOM",
				filters={"bom_creator": self.design.name, "docstatus": 1},
				fields=["item", "name"],
				order_by="creation",
				as_list=True,
			)
		)

	def has_all_boms(self) -> bool:
		items = {self.get_node_item(node_id) for node_id in self.get_bom_node_ids()}
		return all(items) and items <= set(self.get_existing_boms())

	def new_bom(self, node_id: int):
		part = self.parts.get(node_id)
		bom = frappe.new_doc("BOM")
		bom.update(
			{
				"item": self.get_node_item(node_id),
				"quantity": self.get_bom_quantity(node_id),
				"bom_type": "Production",
				"allow_alternative_item": 1,
				"bom_creator": self.design.name,
				"bom_creator_item": part.name if part else "",
				"is_phantom_bom": part.is_phantom_item if part else self.design.is_phantom,
			}
		)

		for field in BOM_FIELDS:
			if self.design.get(field):
				bom.set(field, self.design.get(field))

		if self.design.set_rate_based_on_warehouse and self.design.default_warehouse:
			bom.default_source_warehouse = self.design.default_warehouse

		return bom

	def get_bom_item(self, item_code: str, qty: float, uom: str | None, boms: dict, part=None) -> dict:
		bom_item = {
			"item_code": item_code,
			"qty": qty,
			"uom": uom,
			"allow_alternative_item": 1,
			"include_item_in_manufacturing": 1,
		}

		if item_code in boms:
			bom_item.update({"bom_no": boms[item_code], "do_not_explode": 0})
		elif part:
			bom_item.update(
				{
					"do_not_explode": part.do_not_explode,
					"bom_no": "" if part.do_not_explode else part.bom_no,
				}
			)

		if part:
			bom_item.update(
				{
					"is_phantom_item": part.is_phantom_item if item_code in boms else 0,
					"sourced_by_supplier": part.sourced_by_supplier,
					"conversion_factor": part.conversion_factor if uom == part.uom else 0,
				}
			)

		return bom_item

	def submit_bom(self, bom) -> str:
		bom.flags.ignore_permissions = True
		bom.insert()
		bom.submit()
		return bom.name
