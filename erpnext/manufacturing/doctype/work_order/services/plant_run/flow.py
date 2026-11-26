import math
from collections import defaultdict

import frappe
from frappe.utils import cint, flt, get_datetime, time_diff_in_seconds

from erpnext.manufacturing.doctype.work_order.services.plant_run.plan import RunPlan

JOB_CARD_FIELDS = [
	"name",
	"docstatus",
	"status",
	"is_paused",
	"operation_row_id",
	"workstation",
	"for_quantity",
	"total_completed_qty",
	"manufactured_qty",
	"process_loss_qty",
	"quality_inspection",
	"quality_inspection_template",
]
EPSILON = 0.001


class PlantFlow:
	def __init__(self, work_order):
		self.work_order = work_order
		self.plan = RunPlan(work_order)
		self.stages = self.plan.stages
		self.cards = get_job_cards(work_order.name)

	def get_stage(self, idx):
		return self.stages[idx - 1]

	def get_cards(self, idx):
		return self.cards.get(idx, [])

	def get_open_card(self, idx):
		return next((card for card in self.get_cards(idx) if card.docstatus == 0), None)

	def get_made_qty(self, idx):
		return sum(flt(card.manufactured_qty) for card in self.get_cards(idx) if card.docstatus == 1)

	def get_completed_qty(self, idx):
		return sum(
			max(flt(card.manufactured_qty), flt(card.total_completed_qty))
			for card in self.get_cards(idx)
			if card.docstatus == 1
		)

	@property
	def balance_items(self):
		return self.plan.balance_items

	def get_planned_quantities(self, idx):
		return {
			(row.item_code, row.source_warehouse): flt(row.required_qty)
			for row in self.work_order.required_items
			if row.operation_row_id == idx
		}

	def get_inputs(self, idx):
		return [self.get_input(idx, source) for source in self.get_stage(idx).inputs]

	def get_input(self, idx, source):
		warehouse = source.warehouse
		made = self.get_made_qty(source.stage_idx) * source.share
		return frappe._dict(
			source,
			warehouse=warehouse,
			stage_name=self.get_stage(source.stage_idx).stage_name,
			made_qty=flt(made, 3),
			waiting_qty=max(flt(made - self.get_passed_qty(idx, source.item_code, warehouse), 3), 0),
			done_qty=self.get_passed_qty(idx, source.item_code, warehouse, docstatus=1),
		)

	def get_passed_qty(self, idx, item_code, warehouse, docstatus=None):
		return sum(
			flt(row.transferred_qty)
			for card in self.get_cards(idx)
			if docstatus is None or card.docstatus == docstatus
			for row in card.materials
			if (row.item_code, row.source_warehouse) == (item_code, warehouse)
		)

	def has_input(self, idx):
		inputs = self.get_inputs(idx)
		return not inputs or (
			all(row.made_qty > 0 for row in inputs) and any(row.waiting_qty > EPSILON for row in inputs)
		)

	def is_done(self, idx):
		cards = self.get_cards(idx)
		if not cards or any(card.docstatus == 0 for card in cards):
			return False
		return all(self.is_done(row.stage_idx) and row.waiting_qty <= EPSILON for row in self.get_inputs(idx))

	def get_lot_share(self, idx, passed):
		inputs = self.get_inputs(idx)
		if not inputs:
			return 1.0

		planned = sum(self.get_weight(row.item_code, row.qty) for row in inputs)
		lot = sum(
			self.get_weight(row.item_code, passed.get((row.item_code, row.warehouse))) for row in inputs
		)
		return lot / planned if planned else 0

	def get_weight(self, item_code, qty):
		return flt(qty) / (flt(self.plan.weight_factors.get(item_code)) or 1)

	def get_output_limit(self, idx):
		stage = self.get_stage(idx)
		earlier = [row for row in self.stages if row.sequence_id < stage.sequence_id]
		if not earlier:
			return None

		limit = min(
			self.get_made_qty(row.idx) * self.get_operation_qty(stage) / self.get_operation_qty(row)
			for row in earlier
		)
		return floor_qty(limit - self.get_completed_qty(idx))

	def get_operation_qty(self, stage):
		return flt(self.work_order.qty) if stage.is_packing else flt(stage.output_qty)

	def get_done_share(self, idx):
		done = {(row.item_code, row.warehouse): row.done_qty for row in self.get_inputs(idx)}
		return self.get_lot_share(idx, done) if done else 0

	def get_done_qty(self, idx):
		return sum(flt(card.for_quantity) for card in self.get_cards(idx) if card.docstatus == 1)

	def get_planned_output(self, idx, share):
		stage = self.get_stage(idx)
		round_down = math_floor if is_whole_number(stage.output_item) else floor_qty
		total = self.get_operation_qty(stage) * (self.get_done_share(idx) + share)
		planned = round_down(total) - self.get_done_qty(idx)
		limit = self.get_output_limit(idx)
		return round_down(max(planned if limit is None else min(planned, limit), 0))

	def get_closing_qty(self, idx):
		round_up = math_ceil if is_whole_number(self.get_stage(idx).output_item) else ceil_qty
		order = self.work_order
		return round_up(flt(order.qty) - flt(order.produced_qty) - flt(order.process_loss_qty))

	def get_card_share(self, idx, card):
		passed = defaultdict(float)
		for row in card.materials:
			passed[(row.item_code, row.source_warehouse)] += flt(row.transferred_qty)
		return self.get_lot_share(idx, passed)


def is_whole_number(item_code):
	uom = frappe.get_cached_value("Item", item_code, "stock_uom")
	return bool(cint(frappe.get_cached_value("UOM", uom, "must_be_whole_number")))


def floor_qty(qty):
	return math.floor(flt(qty) * 1000 + 0.000001) / 1000


def math_floor(qty):
	return math.floor(flt(qty) + 0.000001)


def ceil_qty(qty):
	return math.ceil(flt(qty) * 1000 - 0.000001) / 1000


def math_ceil(qty):
	return math.ceil(flt(qty) - 0.000001)


def get_job_cards(work_order):
	cards = frappe.get_all(
		"Job Card",
		filters={"work_order": work_order, "docstatus": ("<", 2), "is_corrective_job_card": 0},
		fields=JOB_CARD_FIELDS,
		order_by="creation asc",
	)
	names = [card.name for card in cards]
	items = get_child_rows("Job Card Item", names, "items")
	logs = get_child_rows("Job Card Time Log", names, "time_logs")
	stages = defaultdict(list)
	for card in cards:
		card.materials = items.get(card.name, [])
		card.time_logs = logs.get(card.name, [])
		card.update(get_timing(card.time_logs))
		stages[card.operation_row_id].append(card)
	return stages


def get_child_rows(doctype, parents, parentfield):
	rows = defaultdict(list)
	if not parents:
		return rows

	filters = {"parenttype": "Job Card", "parentfield": parentfield, "parent": ("in", parents)}
	for row in frappe.get_all(doctype, filters=filters, fields=["*"], order_by="idx"):
		rows[row.parent].append(row)
	return rows


def get_timing(logs):
	worked, running_since = 0.0, None
	for log in logs:
		if log.to_time:
			worked += time_diff_in_seconds(log.to_time, log.from_time)
		elif log.from_time:
			running_since = get_datetime(log.from_time)
	return {
		"started_at": logs[0].from_time if logs else None,
		"worked_seconds": worked,
		"running_since": running_since,
	}
