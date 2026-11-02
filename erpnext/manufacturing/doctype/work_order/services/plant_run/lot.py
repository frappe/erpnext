from functools import cached_property

import frappe
from frappe import _
from frappe.utils import flt

from erpnext.manufacturing.doctype.work_order.services.plant_run.flow import EPSILON


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

	def get_quantities(self):
		quantities = {row.name: self.quantities.get(row.name, 0) for row in self.job_card.items}
		for row in self.job_card.items:
			if self.is_balance_row(row):
				quantities[row.name] = self.get_balance_qty(row)
		return quantities

	def get_balance_qty(self, row):
		factors = self.flow.plan.weight_factors
		shift = sum(
			(self.quantities.get(other.name, 0) - self.get_planned_qty(other)) / flt(factors[other.item_code])
			for other in self.job_card.items
			if not self.get_input(other)
			and not self.is_balance_row(other)
			and flt(factors.get(other.item_code))
		)
		return flt(self.get_planned_qty(row) - shift * (flt(factors.get(row.item_code)) or 1), 3)

	def validate(self, quantities, tolerance):
		if self.share <= 0 or self.output_qty <= 0:
			frappe.throw(_("Pass some of the semi-finished goods to this stage first"))

		for row in self.job_card.items:
			qty = quantities[row.name]
			if source := self.get_input(row):
				self.validate_input(row, qty, source)
			else:
				self.validate_material(row, qty, tolerance)

	def validate_input(self, row, qty, source):
		if qty < 0 or qty > source.waiting_qty + EPSILON:
			frappe.throw(
				_("Only {0} {1} of {2} is waiting from {3}").format(
					flt(source.waiting_qty, 3), row.uom, row.item_name or row.item_code, source.stage_name
				)
			)

	def validate_material(self, row, qty, tolerance):
		name = row.item_name or row.item_code
		if qty <= 0:
			frappe.throw(_("{0} needs a quantity above zero").format(name))

		planned_qty = self.get_planned_qty(row)
		if self.is_balance_row(row) or not planned_qty:
			return

		variance = (qty - planned_qty) / planned_qty * 100
		if abs(variance) > tolerance + 0.0001:
			frappe.throw(
				_("{0} is {1}% off the formula. The allowed range is ±{2}%.").format(
					name, flt(abs(variance), 1), flt(tolerance)
				)
			)
