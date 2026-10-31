from collections import defaultdict

import frappe
from frappe.utils import flt, get_datetime, now_datetime, time_diff_in_seconds

from erpnext.stock.doctype.quality_inspection_template.quality_inspection_template import (
	get_template_details,
)

JOB_CARD_FIELDS = [
	"name",
	"docstatus",
	"status",
	"is_paused",
	"operation_row_id",
	"for_quantity",
	"total_completed_qty",
	"process_loss_qty",
	"quality_inspection",
	"quality_inspection_template",
]


class PlantRunState:
	def __init__(self, run):
		self.run = run
		self.work_order = run.work_order
		self.plan = run.plant_floor.get_batch_plan(self.work_order.qty)
		self.stages = self.plan.get_stages()
		self.machines = {
			row.workstation: run.plant_floor.machine_warehouses.get(row.workstation)
			for row in run.plant_floor.stages
		}
		self.stock = get_stock([run.plant_floor.warehouse, *self.machines.values()])
		self.job_cards = self.get_job_cards()

	def as_dict(self):
		return frappe._dict(
			now=now_datetime(),
			work_order=self.get_work_order(),
			plan=self.plan.as_dict(),
			stages=[self.get_stage(row) for row in self.work_order.operations],
			entries=self.get_entries(),
			levels=self.get_levels(),
		)

	def get_work_order(self):
		fields = ["name", "status", "docstatus", "qty", "produced_qty", "process_loss_qty", "production_item"]
		values = {field: self.work_order.get(field) for field in fields}
		values.update(
			item_name=self.work_order.item_name,
			stock_uom=self.work_order.stock_uom,
			plant_floor=self.work_order.plant_floor,
			actual_start_date=self.work_order.actual_start_date,
			actual_end_date=self.work_order.actual_end_date,
			is_paused=any(card.is_paused for card in self.job_cards.values() if card.docstatus == 0),
			worked_seconds=sum(card.worked_seconds for card in self.job_cards.values()),
			running_since=next(
				(card.running_since for card in self.job_cards.values() if card.running_since), None
			),
		)
		return values

	def get_job_cards(self):
		cards = frappe.get_all(
			"Job Card",
			filters={"work_order": self.work_order.name, "docstatus": ("<", 2), "is_corrective_job_card": 0},
			fields=JOB_CARD_FIELDS,
			order_by="creation asc",
		)
		names = [card.name for card in cards]
		items, logs = get_child_rows("Job Card Item", names), get_child_rows("Job Card Time Log", names)
		for card in cards:
			card.materials = items.get(card.name, [])
			card.update(get_timing(logs.get(card.name, [])))
		return {card.operation_row_id: card for card in cards}

	def get_stage(self, operation):
		card = self.job_cards.get(operation.idx)
		stage = self.stages[operation.idx - 1]
		return frappe._dict(
			idx=operation.idx,
			stage_name=operation.description or operation.operation,
			operation=operation.operation,
			workstation=operation.workstation,
			machine_model=self.run.plant_floor.machine_models.get(operation.workstation),
			is_packing=stage.is_packing,
			planned_minutes=flt(operation.time_in_mins),
			phase=get_phase(card),
			job_card=card,
			items=self.get_stage_items(operation, card),
			output=self.get_output(stage, card),
			quality=get_quality(card),
		)

	def get_stage_items(self, operation, card):
		planned = {
			row.item_code: row
			for row in self.work_order.required_items
			if row.operation_row_id == operation.idx
		}
		rows = card.materials if card else planned.values()
		fixed = self.run.get_fixed_items(frappe._dict(operation_row_id=operation.idx))
		return [
			frappe._dict(
				item_code=row.item_code,
				item_name=row.item_name,
				uom=row.get("uom") or row.get("stock_uom"),
				available_qty=self.stock.get((row.item_code, planned[row.item_code].source_warehouse), 0),
				planned_qty=flt(planned[row.item_code].required_qty),
				required_qty=flt(row.required_qty),
				transferred_qty=flt(row.get("transferred_qty")),
				is_balance_item=row.item_code in self.balance_items,
				is_fixed=row.item_code in fixed,
			)
			for row in rows
		]

	@property
	def balance_items(self):
		return {row.item_code for row in self.run.plant_floor.materials if row.is_balance_item}

	def get_output(self, stage, card):
		return frappe._dict(
			item_code=stage.output_item,
			item_name=frappe.get_cached_value("Item", stage.output_item, "item_name"),
			uom=frappe.get_cached_value("Item", stage.output_item, "stock_uom"),
			planned_qty=flt(card.for_quantity) if card else stage.output_qty,
			completed_qty=flt(card.total_completed_qty) if card else 0,
			process_loss_qty=flt(card.process_loss_qty) if card else 0,
		)

	def get_entries(self):
		entry = frappe.qb.DocType("Stock Entry")
		detail = frappe.qb.DocType("Stock Entry Detail")
		bundle = frappe.qb.DocType("Serial and Batch Entry")
		rows = (
			frappe.qb.from_(entry)
			.join(detail)
			.on(detail.parent == entry.name)
			.left_join(bundle)
			.on(bundle.parent == detail.serial_and_batch_bundle)
			.select(
				entry.name,
				entry.purpose,
				entry.job_card,
				entry.posting_date,
				entry.posting_time,
				detail.item_code,
				detail.item_name,
				detail.qty,
				detail.uom,
				detail.is_finished_item,
				bundle.batch_no,
			)
			.where((entry.work_order == self.work_order.name) & (entry.docstatus == 1))
			.orderby(entry.creation, order=frappe.qb.desc)
			.orderby(detail.idx)
		).run(as_dict=True)
		return group_entries(rows)

	def get_levels(self):
		store = self.run.plant_floor.warehouse
		return frappe._dict(
			store={item: qty for (item, warehouse), qty in self.stock.items() if warehouse == store},
			machines={
				workstation: self.get_machine_weight(warehouse)
				for workstation, warehouse in self.machines.items()
			},
		)

	def get_machine_weight(self, warehouse):
		factors = self.plan.weight_factors
		return sum(
			qty / flt(factors[item])
			for (item, stock_warehouse), qty in self.stock.items()
			if stock_warehouse == warehouse and flt(factors.get(item))
		)


def get_child_rows(doctype, parents):
	rows = defaultdict(list)
	if not parents:
		return rows

	for row in frappe.get_all(doctype, filters={"parent": ("in", parents)}, fields=["*"], order_by="idx"):
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


def get_phase(card):
	if not card or (card.docstatus == 0 and not card.started_at):
		return "waiting"
	if card.docstatus == 1:
		return "done"
	if not any(flt(row.transferred_qty) for row in card.materials):
		return "ready"
	return "processing"


def get_quality(card):
	if not card or not card.quality_inspection_template:
		return None

	return frappe._dict(
		template=card.quality_inspection_template,
		inspection=card.quality_inspection,
		parameters=[
			frappe._dict(
				specification=row.specification,
				numeric=row.numeric,
				min_value=row.min_value,
				max_value=row.max_value,
			)
			for row in get_template_details(card.quality_inspection_template)
		],
	)


def group_entries(rows):
	entries = {}
	for row in rows:
		entry = entries.setdefault(
			row.name,
			frappe._dict(
				name=row.name,
				purpose=row.purpose,
				job_card=row.job_card,
				posting_date=row.posting_date,
				posting_time=row.posting_time,
				items=[],
			),
		)
		entry["items"].append(
			frappe._dict(
				item_code=row.item_code,
				item_name=row.item_name,
				qty=row.qty,
				uom=row.uom,
				is_finished_item=row.is_finished_item,
				batch_no=row.batch_no,
			)
		)
	return list(entries.values())


def get_stock(warehouses):
	warehouses = list(filter(None, set(warehouses)))
	if not warehouses:
		return {}

	bins = frappe.get_all(
		"Bin",
		filters={"warehouse": ("in", warehouses), "actual_qty": ("!=", 0)},
		fields=["item_code", "warehouse", "actual_qty"],
	)
	return {(row.item_code, row.warehouse): flt(row.actual_qty) for row in bins}
