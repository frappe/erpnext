# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""BOM cost computation (extracted from bom.py).

``BOMCostingService`` wraps a BOM document (composition); bom.py keeps thin
delegating stubs so external callers (bom_update_log, etc.) keep working.
"""

import frappe
from frappe import _
from frappe.utils import flt


class BOMCostingService:
	def __init__(self, doc):
		self.doc = doc

	def validate_bom_currency(self, item):
		if (
			item.get("bom_no")
			and frappe.db.get_value("BOM", item.get("bom_no"), "currency") != self.doc.currency
		):
			frappe.throw(
				_("Row {0}: Currency of the BOM #{1} should be equal to the selected currency {2}").format(
					item.idx, item.bom_no, self.doc.currency
				)
			)

	def get_rm_rate(self, arg, notify=True):
		"""Get raw material rate as per selected method, if bom exists takes bom cost"""
		if not self.doc.rm_cost_as_per:
			self.doc.rm_cost_as_per = "Valuation Rate"

		rate = self._raw_material_rate(arg, notify) if arg else 0
		return flt(rate) * flt(self.doc.plc_conversion_rate or 1) / (self.doc.conversion_rate or 1)

	def _raw_material_rate(self, arg, notify):
		from erpnext.manufacturing.doctype.bom.bom import get_bom_item_rate

		# Customer Provided parts and Supplier sourced parts will have zero rate
		if frappe.db.get_value("Item", arg["item_code"], "is_customer_provided_item") or arg.get(
			"sourced_by_supplier"
		):
			return 0

		if arg.get("bom_no") and (
			self.doc.set_rate_of_sub_assembly_item_based_on_bom or arg.get("is_phantom_item")
		):
			return flt(self.get_bom_unitcost(arg["bom_no"])) * (arg.get("conversion_factor") or 1)

		rate = get_bom_item_rate(arg, self.doc)
		if not rate:
			self._warn_rate_not_found(arg, notify)
		return rate

	def _warn_rate_not_found(self, arg, notify):
		if self.doc.rm_cost_as_per == "Price List":
			msg = _("Price not found for item {0} in price list {1}").format(
				arg["item_code"], self.doc.buying_price_list
			)
		elif notify:
			msg = _("{0} not found for item {1}").format(self.doc.rm_cost_as_per, arg["item_code"])
		else:
			return
		frappe.msgprint(msg, alert=True)

	def update_cost(
		self,
		update_parent: bool = True,
		from_child_bom: bool = False,
		update_hour_rate: bool = True,
		save: bool = True,
	):
		if self.doc.docstatus == 2:
			return

		self.doc.flags.cost_updated = False
		existing_bom_cost = self.doc.total_cost

		if self.doc.docstatus == 1:
			self.doc.flags.ignore_validate_update_after_submit = True

		self.calculate_cost(save_updates=save, update_hour_rate=update_hour_rate)

		if save:
			self.doc.db_update()

		if self.doc.total_cost != existing_bom_cost and update_parent:
			self._update_parent_boms()

		if not from_child_bom:
			msg = "Cost Updated" if self.doc.flags.cost_updated else "No changes in cost found"
			frappe.msgprint(_(msg), alert=True)

	def _update_parent_boms(self):
		bom_item = frappe.qb.DocType("BOM Item")
		parent_boms = (
			frappe.qb.from_(bom_item)
			.select(bom_item.parent)
			.distinct()
			.where(
				(bom_item.bom_no == self.doc.name)
				& (bom_item.docstatus == 1)
				& (bom_item.parenttype == "BOM")
			)
		).run(pluck=True)

		for bom in parent_boms:
			frappe.get_doc("BOM", bom).update_cost(from_child_bom=True)

	def update_parent_cost(self):
		if self.doc.total_cost:
			cost = self.doc.total_cost / self.doc.quantity

			bom_item = frappe.qb.DocType("BOM Item")
			(
				frappe.qb.update(bom_item)
				.set(bom_item.rate, cost)
				.set(bom_item.amount, bom_item.stock_qty * cost)
				.where(
					(bom_item.bom_no == self.doc.name)
					& (bom_item.docstatus < 2)
					& (bom_item.parenttype == "BOM")
				)
			).run()

	def get_bom_unitcost(self, bom_no):
		bom_table = frappe.qb.DocType("BOM")
		bom = (
			frappe.qb.from_(bom_table)
			.select(
				bom_table.name,
				(bom_table.base_total_cost / bom_table.quantity).as_("unit_cost"),
			)
			.where((bom_table.is_active == 1) & (bom_table.name == bom_no))
		).run(as_dict=1)
		return bom and bom[0]["unit_cost"] or 0

	def calculate_cost(self, save_updates=False, update_hour_rate=False):
		"""Calculate bom totals"""
		self.calculate_op_cost(update_hour_rate)
		self.calculate_rm_cost(save=save_updates)
		self.calculate_secondary_items_costs(save=save_updates)
		if save_updates:
			# not via doc event, table is not regenerated and needs updation
			self.calculate_exploded_cost()

		old_cost = self.doc.total_cost

		self.doc.total_cost = (
			self.doc.operating_cost + self.doc.raw_material_cost - self.doc.secondary_items_cost
		)
		self.doc.base_total_cost = (
			self.doc.base_operating_cost
			+ self.doc.base_raw_material_cost
			- self.doc.base_secondary_items_cost
		)

		if self.doc.total_cost != old_cost:
			self.doc.flags.cost_updated = True

	def calculate_op_cost(self, update_hour_rate=False):
		"""Update workstation rate and calculates totals"""
		self.doc.operating_cost = 0
		self.doc.base_operating_cost = 0
		if self.doc.get("with_operations"):
			for d in self.doc.get("operations"):
				self._accumulate_operation_cost(d, update_hour_rate)
		elif self.doc.get("fg_based_operating_cost"):
			self._set_fg_based_operating_cost()

	def _accumulate_operation_cost(self, d, update_hour_rate):
		if d.workstation or d.workstation_type:
			self.update_rate_and_time(d, update_hour_rate)

		operating_cost = d.operating_cost
		base_operating_cost = d.base_operating_cost
		if d.set_cost_based_on_bom_qty:
			operating_cost = flt(d.cost_per_unit) * flt(self.doc.quantity)
			base_operating_cost = flt(d.base_cost_per_unit) * flt(self.doc.quantity)

		self.doc.operating_cost += flt(operating_cost)
		self.doc.base_operating_cost += flt(base_operating_cost)

	def _set_fg_based_operating_cost(self):
		total = flt(self.doc.get("quantity")) * flt(self.doc.get("operating_cost_per_bom_quantity"))
		self.doc.operating_cost = total
		self.doc.base_operating_cost = flt(total * self.doc.conversion_rate, 2)

	def update_rate_and_time(self, row, update_hour_rate=False):
		if not row.hour_rate or update_hour_rate:
			self._set_row_hour_rate(row)

		if row.hour_rate:
			row.base_hour_rate = flt(row.hour_rate) * flt(self.doc.conversion_rate)
			if row.time_in_mins:
				self._set_row_operating_costs(row)

		if update_hour_rate:
			row.db_update()

	def _set_row_hour_rate(self, row):
		hour_rate = 0
		if row.workstation:
			hour_rate = flt(frappe.get_cached_value("Workstation", row.workstation, "hour_rate"))
		elif row.workstation_type:
			hour_rate = flt(frappe.get_cached_value("Workstation Type", row.workstation_type, "hour_rate"))

		if hour_rate:
			row.hour_rate = (
				hour_rate / flt(self.doc.conversion_rate) if self.doc.conversion_rate else hour_rate
			)

	def _set_row_operating_costs(self, row):
		row.operating_cost = flt(row.hour_rate) * flt(row.time_in_mins) / 60.0
		row.base_operating_cost = flt(row.operating_cost) * flt(self.doc.conversion_rate)
		row.cost_per_unit = row.operating_cost / (row.batch_size or 1.0)
		row.base_cost_per_unit = row.base_operating_cost / (row.batch_size or 1.0)

	def calculate_rm_cost(self, save=False):
		"""Fetch RM rate as per today's valuation rate and calculate totals"""
		total_rm_cost = 0
		base_total_rm_cost = 0

		for d in self.doc.get("items"):
			old_rate = d.rate
			if not self.doc.bom_creator and (d.is_stock_item or d.is_phantom_item):
				d.rate = self.get_rm_rate(self._rm_rate_args(d), notify=False)

			self._set_item_amounts(d)
			total_rm_cost += d.amount
			base_total_rm_cost += d.base_amount
			if save and (old_rate != d.rate):
				d.db_update()

		self.doc.raw_material_cost = total_rm_cost
		self.doc.base_raw_material_cost = base_total_rm_cost

	def _rm_rate_args(self, d):
		return {
			"company": self.doc.company,
			"item_code": d.item_code,
			"bom_no": d.bom_no,
			"qty": d.qty,
			"uom": d.uom,
			"stock_uom": d.stock_uom,
			"conversion_factor": d.conversion_factor,
			"sourced_by_supplier": d.sourced_by_supplier,
			"is_phantom_item": d.is_phantom_item,
		}

	def _set_item_amounts(self, d):
		d.base_rate = flt(d.rate) * flt(self.doc.conversion_rate)
		d.amount = flt(
			flt(d.rate, d.precision("rate")) * flt(d.qty, d.precision("qty")), d.precision("amount")
		)
		d.base_amount = d.amount * flt(self.doc.conversion_rate)
		d.qty_consumed_per_unit = flt(d.stock_qty, d.precision("stock_qty")) / flt(
			self.doc.quantity, self.doc.precision("quantity")
		)

	def calculate_secondary_items_costs(self, save=False):
		"""Fetch RM rate as per today's valuation rate and calculate totals"""
		total_sm_cost = 0
		base_total_sm_cost = 0
		precision = self.doc.precision("raw_material_cost")

		for d in self.doc.get("secondary_items"):
			if not d.is_legacy:
				d.cost = flt(self.doc.raw_material_cost * (d.cost_allocation_per / 100), precision)
				d.base_cost = flt(d.cost * self.doc.conversion_rate, precision)

				total_sm_cost += d.cost
				base_total_sm_cost += d.base_cost
				if save:
					d.db_update()

		self.doc.secondary_items_cost = total_sm_cost
		self.doc.base_secondary_items_cost = base_total_sm_cost

	def calculate_exploded_cost(self):
		"Set exploded row cost from it's parent BOM."
		rm_rate_map = self.get_rm_rate_map()

		for row in self.doc.get("exploded_items"):
			old_rate = flt(row.rate)
			row.rate = rm_rate_map.get(row.item_code)
			row.amount = flt(row.stock_qty) * flt(row.rate)

			if old_rate != row.rate:
				# Only db_update if changed
				row.db_update()

	def get_rm_rate_map(self) -> dict[str, float]:
		"Create Raw Material-Rate map for Exploded Items. Fetch rate from Items table or Subassembly BOM."
		rm_rate_map = {}

		for item in self.doc.get("items"):
			if item.bom_no:
				# Get Item-Rate from Subassembly BOM
				explosion_items = frappe.get_all(
					"BOM Explosion Item",
					filters={"parent": item.bom_no},
					fields=["item_code", "rate"],
					order_by=None,  # to avoid sort index creation at db level (granular change)
				)
				explosion_item_rate = {item.item_code: flt(item.rate) for item in explosion_items}
				rm_rate_map.update(explosion_item_rate)
			else:
				rm_rate_map[item.item_code] = flt(item.base_rate) / flt(item.conversion_factor or 1.0)

		return rm_rate_map
