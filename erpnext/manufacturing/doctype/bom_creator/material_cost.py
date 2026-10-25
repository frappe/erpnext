# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from collections import defaultdict

import frappe
from frappe.utils import cint, flt

import erpnext
from erpnext.manufacturing.doctype.bom.bom import get_bom_item_rate
from erpnext.setup.utils import get_exchange_rate


class MaterialCost:
	def __init__(self, design):
		self.design = design

	def set_costs(self):
		self.set_exchange_rates()
		self.set_conversion_factors()
		self.set_part_rates()
		if self.design.track_semi_finished_goods:
			self.design.raw_material_cost = self.get_operation_plan_cost()

	def set_exchange_rates(self):
		design = self.design
		company_currency = erpnext.get_company_currency(design.company)
		design.currency = design.currency or company_currency
		if design.currency == company_currency:
			design.conversion_rate = 1
		elif flt(design.conversion_rate) in (0, 1) or (
			not design.is_new() and design.has_value_changed("currency")
		):
			design.conversion_rate = get_exchange_rate(design.currency, company_currency, args="for_buying")

		if design.rm_cost_as_per != "Price List" or not design.buying_price_list:
			design.plc_conversion_rate = 1
			return

		design.price_list_currency = frappe.get_cached_value(
			"Price List", design.buying_price_list, "currency"
		)
		if design.price_list_currency == company_currency:
			design.plc_conversion_rate = 1
		elif flt(design.plc_conversion_rate) in (0, 1) or (
			not design.is_new() and design.has_value_changed("price_list_currency")
		):
			design.plc_conversion_rate = get_exchange_rate(
				design.price_list_currency, company_currency, args="for_buying"
			)

	def set_conversion_factors(self):
		rows = [row for row in self.design.items if row.item_code]
		uom_factors = self.get_uom_factors([row.item_code for row in rows])
		stock_uoms = self.get_stock_uoms([row.item_code for row in rows])
		for row in rows:
			row.stock_uom = stock_uoms.get(row.item_code)
			row.uom = row.uom or row.stock_uom
			row.conversion_factor = (
				flt(uom_factors.get((row.item_code, row.uom))) or flt(row.conversion_factor) or 1.0
			)

			row.stock_qty = flt(row.qty) * flt(row.conversion_factor)

	def set_part_rates(self):
		children = defaultdict(list)
		for row in self.design.items:
			row.rate = row.amount = 0
			if row.item_code and not row.exclude_from_bom:
				children[row.parent_node_id or 0].append(row)

		cost = self.get_part_cost(0, children, set())
		self.design.raw_material_cost = cost * (flt(self.design.qty) or 1)

	def get_part_cost(self, node_id: int, children: dict, visited: set) -> float:
		visited.add(node_id)
		cost = 0
		for row in children.get(node_id, []):
			if children.get(row.node_id) and row.node_id not in visited:
				row.rate = self.get_part_cost(row.node_id, children, visited) * flt(
					row.conversion_factor or 1
				)
			else:
				row.rate = self.get_rate(
					row.item_code, row.qty, row.uom, row.stock_uom, row.conversion_factor, row
				)

			row.amount = flt(row.rate) * flt(row.qty)
			row.base_rate = flt(row.rate) * flt(self.design.conversion_rate or 1)
			row.base_amount = flt(row.amount) * flt(self.design.conversion_rate or 1)
			cost += row.amount

		return cost

	def get_operation_plan_cost(self) -> float:
		materials = defaultdict(list)
		for row in self.design.materials:
			materials[cint(row.bom_node_id)].append(row)

		parts = {row.node_id: row for row in self.design.items}
		item_codes = [row.item_code for row in self.design.materials if row.item_code]
		self.stock_uoms = self.get_stock_uoms(item_codes)
		self.uom_factors = self.get_uom_factors(item_codes)
		return self.get_material_cost(0, materials, parts, {0}) * (flt(self.design.qty) or 1)

	def get_material_cost(self, node_id: int, materials: dict, parts: dict, visited: set) -> float:
		cost = 0
		for row in materials[node_id]:
			node = cint(row.part_node_id)
			if row.from_operation_id or (node and not parts[node].item_code):
				continue

			if node and node in materials and node not in visited:
				rate = self.get_material_cost(node, materials, parts, visited | {node})
			elif node:
				rate = flt(parts[node].rate)
			else:
				stock_uom = self.stock_uoms.get(row.item_code)
				factor = flt(self.uom_factors.get((row.item_code, row.uom))) or 1
				rate = self.get_rate(row.item_code, row.qty, row.uom or stock_uom, stock_uom, factor)

			cost += rate * flt(row.qty)

		return cost

	def get_rate(self, item_code, qty, uom, stock_uom, conversion_factor, row=None) -> float:
		design = self.design
		rate = get_bom_item_rate(
			{
				"company": design.company,
				"item_code": item_code,
				"bom_no": "",
				"qty": qty,
				"uom": uom,
				"stock_uom": stock_uom,
				"conversion_factor": conversion_factor,
				"sourced_by_supplier": row.sourced_by_supplier if row else 0,
				"set_rate_based_on_warehouse": design.set_rate_based_on_warehouse,
				"warehouse": design.default_warehouse,
			},
			design,
		)
		if design.rm_cost_as_per == "Price List":
			rate = flt(rate) * flt(design.plc_conversion_rate or 1)

		return flt(rate) / flt(design.conversion_rate or 1)

	def get_uom_factors(self, item_codes: list[str]) -> dict:
		if not item_codes:
			return {}

		return {
			(row.parent, row.uom): row.conversion_factor
			for row in frappe.get_all(
				"UOM Conversion Detail",
				filters={"parent": ("in", list(set(item_codes))), "parenttype": "Item"},
				fields=["parent", "uom", "conversion_factor"],
			)
		}

	def get_stock_uoms(self, item_codes: list[str]) -> dict:
		if not item_codes:
			return {}

		return dict(
			frappe.get_all(
				"Item",
				filters={"name": ("in", list(set(item_codes)))},
				fields=["name", "stock_uom"],
				as_list=True,
			)
		)
