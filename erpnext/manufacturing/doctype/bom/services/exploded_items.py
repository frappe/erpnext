# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""BOM exploded-items (flat BOM) computation (extracted from bom.py)."""

from operator import itemgetter

import frappe
from frappe.query_builder.functions import IfNull
from frappe.utils import flt


class BOMExplodedItemsService:
	def __init__(self, doc):
		self.doc = doc

	def update_exploded_items(self, save=True):
		"""Update Flat BOM, following will be correct data"""
		self.get_exploded_items()
		self.add_exploded_items(save=save)

	def get_exploded_items(self):
		"""Get all raw materials including items from child bom"""
		self.doc.cur_exploded_items = {}
		for d in self.doc.get("items"):
			if d.bom_no:
				self.get_child_exploded_items(d.bom_no, d.stock_qty, d.operation)
			elif d.item_code:
				self.add_to_cur_exploded_items(self._exploded_item_row(d))

	@staticmethod
	def _exploded_item_row(d):
		return frappe._dict(
			{
				"item_code": d.item_code,
				"item_name": d.item_name,
				"operation": d.operation,
				"is_sub_assembly_item": d.is_sub_assembly_item,
				"source_warehouse": d.source_warehouse,
				"description": d.description,
				"image": d.image,
				"stock_uom": d.stock_uom,
				"stock_qty": flt(d.stock_qty),
				"rate": flt(d.base_rate) / (flt(d.conversion_factor) or 1.0),
				"include_item_in_manufacturing": d.include_item_in_manufacturing,
				"sourced_by_supplier": d.sourced_by_supplier,
			}
		)

	def add_to_cur_exploded_items(self, args):
		key = args.item_code
		if args.operation:
			key = (args.item_code, args.operation)

		if self.doc.cur_exploded_items.get(key):
			self.doc.cur_exploded_items[key]["stock_qty"] += args.stock_qty
		else:
			self.doc.cur_exploded_items[key] = args

	def get_child_exploded_items(self, bom_no, stock_qty, operation=None):
		"""Add all items from Flat BOM of child BOM"""
		for d in self._fetch_child_flat_bom_items(bom_no):
			self.add_to_cur_exploded_items(self._child_exploded_row(d, stock_qty, operation))

	@staticmethod
	def _fetch_child_flat_bom_items(bom_no):
		# Did not use qty_consumed_per_unit in the query, as it leads to rounding loss
		bom_item = frappe.qb.DocType("BOM Explosion Item")
		bom = frappe.qb.DocType("BOM")
		qty_consumed_per_unit = (bom_item.stock_qty / IfNull(bom.quantity, 1)).as_("qty_consumed_per_unit")
		return (
			frappe.qb.from_(bom_item)
			.join(bom)
			.on(bom_item.parent == bom.name)
			.select(
				bom_item.item_code,
				bom_item.item_name,
				bom_item.description,
				bom_item.source_warehouse,
				bom_item.operation,
				bom_item.is_sub_assembly_item,
				bom_item.stock_uom,
				bom_item.stock_qty,
				bom_item.rate,
				bom_item.include_item_in_manufacturing,
				bom_item.sourced_by_supplier,
				qty_consumed_per_unit,
			)
			.where((bom.name == bom_no) & (bom.docstatus == 1))
		).run(as_dict=1)

	@staticmethod
	def _child_exploded_row(d, stock_qty, operation):
		return frappe._dict(
			{
				"item_code": d["item_code"],
				"item_name": d["item_name"],
				"source_warehouse": d["source_warehouse"],
				"operation": d["operation"] or operation,
				"description": d["description"],
				"stock_uom": d["stock_uom"],
				"stock_qty": d["qty_consumed_per_unit"] * stock_qty,
				"rate": flt(d["rate"]),
				"include_item_in_manufacturing": d.get("include_item_in_manufacturing", 0),
				"sourced_by_supplier": d.get("sourced_by_supplier", 0),
				"is_sub_assembly_item": d.get("is_sub_assembly_item", 0),
			}
		)

	def add_exploded_items(self, save=True):
		"Add items to Flat BOM table"
		self.doc.set("exploded_items", [])

		if save:
			explosion_item = frappe.qb.DocType("BOM Explosion Item")
			frappe.qb.from_(explosion_item).delete().where(explosion_item.parent == self.doc.name).run()

		for d in sorted(self.doc.cur_exploded_items, key=itemgetter(0)):
			ch = self.doc.append("exploded_items", {})
			for i in self.doc.cur_exploded_items[d].keys():
				ch.set(i, self.doc.cur_exploded_items[d][i])
			ch.amount = flt(ch.stock_qty) * flt(ch.rate)
			ch.qty_consumed_per_unit = flt(ch.stock_qty) / flt(self.doc.quantity)
			ch.docstatus = self.doc.docstatus

			if save:
				ch.db_insert()
