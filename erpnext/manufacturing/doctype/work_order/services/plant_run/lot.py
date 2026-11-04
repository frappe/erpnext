from functools import cached_property

import frappe
from frappe import _
from frappe.utils import flt

from erpnext.manufacturing.doctype.work_order.services.plant_run.flow import EPSILON
from erpnext.stock.stock_ledger import is_negative_stock_allowed


class Lot:
	def __init__(self, flow, job_card, quantities):
		self.flow = flow
		self.job_card = job_card
		self.idx = job_card.operation_row_id
		self.inputs = {(row.item_code, row.warehouse): row for row in flow.get_inputs(self.idx)}
		self.planned = flow.get_planned_quantities(self.idx)
		self.quantities = {name: flt(qty) for name, qty in (quantities or {}).items()}

	def get_input(self, row):
		return self.inputs.get((row.item_code, row.source_warehouse))

	@cached_property
	def tolerance(self):
		return self.flow.plan.tolerance

	@cached_property
	def share(self):
		passed = {key: self.get_passed(source) for key, source in self.inputs.items()}
		return self.flow.get_lot_share(self.idx, passed)

	@cached_property
	def operation_qty(self):
		return self.flow.get_operation_qty(self.flow.get_stage(self.idx))

	@cached_property
	def output_qty(self):
		return self.flow.get_planned_output(self.idx, self.share)

	@cached_property
	def is_last(self):
		return all(
			self.flow.is_done(row.stage_idx) and self.get_passed(row) >= row.waiting_qty - EPSILON
			for row in self.inputs.values()
		)

	def get_passed(self, source):
		return sum(
			self.quantities.get(row.name, 0)
			for row in self.job_card.items
			if (row.item_code, row.source_warehouse) == (source.item_code, source.warehouse)
		)

	@cached_property
	def for_quantity(self):
		if self.is_last and self.flow.get_stage(self.idx).is_packing:
			return max(self.output_qty, self.flow.get_closing_qty(self.idx))
		return self.output_qty

	@cached_property
	def scale(self):
		return self.output_qty / self.operation_qty if self.operation_qty else 0

	def get_planned_qty(self, row):
		return flt(self.planned.get((row.item_code, row.source_warehouse), 0) * self.scale, 3)

	def is_balance_row(self, row):
		return not self.get_input(row) and row.item_code in self.flow.balance_items

	@cached_property
	def resolved_quantities(self):
		return {row.name: self.get_qty(row) for row in self.job_card.items}

	def get_qty(self, row):
		if self.is_balance_row(row):
			return self.get_balance_qty(row)
		if row.name in self.quantities:
			return self.quantities[row.name]
		return 0 if self.get_input(row) else self.get_planned_qty(row)

	def get_balance_qty(self, row):
		factors = self.flow.plan.weight_factors
		shift = sum(
			(self.get_qty(other) - self.get_planned_qty(other)) / flt(factors[other.item_code])
			for other in self.job_card.items
			if not self.get_input(other)
			and not self.is_balance_row(other)
			and flt(factors.get(other.item_code))
		)
		return flt(self.get_planned_qty(row) - shift * (flt(factors.get(row.item_code)) or 1), 3)

	@cached_property
	def stock(self):
		bins = frappe.get_all(
			"Bin",
			filters={
				"item_code": ("in", [row.item_code for row in self.job_card.items]),
				"warehouse": ("in", [row.source_warehouse for row in self.job_card.items]),
			},
			fields=["item_code", "warehouse", "actual_qty"],
		)
		return {(row.item_code, row.warehouse): flt(row.actual_qty) for row in bins}

	@property
	def error(self):
		if self.share <= 0 or self.output_qty <= 0:
			return _("Pass some of the semi-finished goods to this stage first")

	@cached_property
	def row_errors(self):
		errors = {
			row.name: self.get_row_error(row, self.resolved_quantities[row.name])
			for row in self.job_card.items
		}
		return {name: error for name, error in errors.items() if error}

	def validate(self):
		if error := self.error or next(iter(self.row_errors.values()), None):
			frappe.throw(error)

	def get_preview(self):
		return frappe._dict(
			output_qty=self.output_qty,
			errors=list(filter(None, [self.error, *self.row_errors.values()])),
			items={
				row.name: frappe._dict(
					qty=self.resolved_quantities[row.name],
					planned_qty=self.get_lot_planned_qty(row),
					is_off=row.name in self.row_errors,
				)
				for row in self.job_card.items
			},
		)

	def get_lot_planned_qty(self, row):
		source = self.get_input(row)
		return source.waiting_qty if source else self.get_planned_qty(row)

	def get_row_error(self, row, qty):
		if source := self.get_input(row):
			return self.get_input_error(row, qty, source)
		return self.get_material_error(row, qty)

	def get_input_error(self, row, qty, source):
		if qty < 0 or qty > source.waiting_qty + EPSILON:
			return _("Only {0} {1} of {2} is waiting from {3}").format(
				flt(source.waiting_qty, 3), row.uom, row.item_name or row.item_code, source.stage_name
			)

	def get_material_error(self, row, qty):
		name = row.item_name or row.item_code
		if qty <= 0:
			return _("{0} needs a quantity above zero").format(name)

		in_stock = self.stock.get((row.item_code, row.source_warehouse), 0)
		if qty > in_stock + EPSILON and not is_negative_stock_allowed(item_code=row.item_code):
			return _("Only {0} {1} of {2} is in stock").format(flt(in_stock, 3), row.uom, name)

		planned_qty = self.get_planned_qty(row)
		if self.is_balance_row(row) or not planned_qty:
			return None

		variance = (qty - planned_qty) / planned_qty * 100
		if abs(variance) > self.tolerance + 0.0001:
			return _("{0} is {1}% off the formula. The allowed range is ±{2}%.").format(
				name, flt(abs(variance), 1), self.tolerance
			)
