import frappe
from frappe.utils import flt, get_datetime, now_datetime

from erpnext.manufacturing.doctype.work_order.services.plant_run.actions import get_operator
from erpnext.stock.doctype.quality_inspection_template.quality_inspection_template import (
	get_template_details,
)


class PlantRunState:
	def __init__(self, run):
		self.run = run
		self.work_order = run.work_order
		self.flow = run.get_flow()
		self.plan = self.flow.plan
		self.machines = {stage.workstation: stage.warehouse for stage in self.flow.stages}
		self.stock = get_stock([*self.plan.warehouses, *self.machines.values()])
		self.broken_machines = set(
			frappe.get_all(
				"Workstation",
				filters={"name": ("in", list(self.machines)), "status": "Problem"},
				pluck="name",
			)
		)

	def as_dict(self):
		return frappe._dict(
			now=now_datetime(),
			work_order=self.get_work_order(),
			plan=self.plan.as_dict(),
			stages=[self.get_stage(row) for row in self.work_order.operations],
			entries=self.get_entries(),
			levels=self.get_levels(),
			downtime=get_downtime_defaults(),
		)

	@property
	def all_cards(self):
		return [card for cards in self.flow.cards.values() for card in cards]

	def get_work_order(self):
		fields = ["name", "status", "docstatus", "qty", "produced_qty", "process_loss_qty", "production_item"]
		values = {field: self.work_order.get(field) for field in fields}
		worked_seconds, running_since = get_union_timing(
			[log for card in self.all_cards for log in card.time_logs]
		)
		values.update(
			item_name=self.work_order.item_name,
			stock_uom=self.work_order.stock_uom,
			bom_no=self.work_order.bom_no,
			bom_creator=self.plan.bom.bom_creator,
			actual_start_date=self.work_order.actual_start_date,
			actual_end_date=self.work_order.actual_end_date,
			is_paused=any(
				card.is_paused and not self.get_breakdown(card)
				for card in self.all_cards
				if card.docstatus == 0
			),
			worked_seconds=worked_seconds,
			running_since=running_since,
			charged_weight=self.get_charged_weight(),
		)
		return values

	def get_charged_weight(self):
		materials = {row.item_code for row in self.plan.raw_rows}
		return flt(
			sum(
				self.flow.get_weight(row.item_code, row.transferred_qty)
				for card in self.all_cards
				for row in card.materials
				if row.item_code in materials
			),
			3,
		)

	def get_stage(self, operation):
		idx, stage = operation.idx, self.flow.get_stage(operation.idx)
		cards = self.flow.get_cards(idx)
		card = self.flow.get_open_card(idx) or (cards[-1] if cards else None)
		phase = self.get_phase(idx, card)
		return frappe._dict(
			idx=idx,
			stage_name=operation.operation,
			operation=operation.operation,
			workstation=operation.workstation,
			machine_model=self.plan.machines.get(operation.workstation, {}).get("machine_model"),
			sequence_id=stage.sequence_id,
			is_packing=stage.is_packing,
			planned_minutes=flt(operation.time_in_mins),
			phase=phase,
			breakdown=self.get_breakdown(card),
			can_start=bool(phase == "waiting" and card and card.docstatus == 0 and self.flow.has_input(idx)),
			lot=len(cards),
			job_card=card,
			job_cards=[row.name for row in cards],
			worked_seconds=sum(row.worked_seconds for row in cards),
			inputs=self.flow.get_inputs(idx),
			items=self.get_stage_items(idx, card),
			output=self.get_output(stage, cards, card),
			quality=get_quality(card),
		)

	def get_breakdown(self, card):
		if not card or card.docstatus != 0 or not card.is_paused:
			return None
		if card.workstation not in self.broken_machines or not card.time_logs:
			return None
		return frappe._dict(since=card.time_logs[-1].to_time)

	def get_phase(self, idx, card):
		if self.flow.is_done(idx):
			return "done"
		if not card or card.docstatus == 1 or not card.started_at:
			return "waiting"
		if not any(flt(row.transferred_qty) for row in card.materials):
			return "ready"
		return "processing"

	def get_stage_items(self, idx, card):
		inputs = {(row.item_code, row.warehouse): row for row in self.flow.get_inputs(idx)}
		rows = card.materials if card else self.get_planned_rows(idx)
		return [self.get_item(row, inputs.get((row.item_code, row.source_warehouse))) for row in rows]

	def get_planned_rows(self, idx):
		return [
			frappe._dict(row.as_dict(), name=None, transferred_qty=0)
			for row in self.work_order.required_items
			if row.operation_row_id == idx
		]

	def get_item(self, row, source):
		return frappe._dict(
			name=row.name,
			item_code=row.item_code,
			item_name=row.item_name,
			uom=row.get("uom") or row.get("stock_uom"),
			source_warehouse=row.source_warehouse,
			required_qty=flt(row.required_qty),
			transferred_qty=flt(row.get("transferred_qty")),
			is_input=bool(source),
			waiting_qty=source.waiting_qty if source else 0,
			source_stage=source.stage_name if source else None,
			is_balance_item=not source and row.item_code in self.flow.balance_items,
			weight_factor=flt(self.plan.weight_factors.get(row.item_code)),
			has_serial_no=frappe.get_cached_value("Item", row.item_code, "has_serial_no"),
			has_batch_no=frappe.get_cached_value("Item", row.item_code, "has_batch_no"),
		)

	def get_output(self, stage, cards, card):
		done = [row for row in cards if row.docstatus == 1]
		return frappe._dict(
			item_code=stage.output_item,
			item_name=frappe.get_cached_value("Item", stage.output_item, "item_name"),
			uom=frappe.get_cached_value("Item", stage.output_item, "stock_uom"),
			weight_factor=flt(self.plan.weight_factors.get(stage.output_item)),
			planned_qty=flt(card.for_quantity) if card and card.docstatus == 0 else stage.output_qty,
			expected_qty=self.get_expected_qty(stage, card),
			done_qty=self.flow.get_done_qty(stage.idx),
			completed_qty=sum(flt(row.total_completed_qty) for row in done),
			process_loss_qty=sum(flt(row.process_loss_qty) for row in done),
		)

	def get_expected_qty(self, stage, card):
		if not card or card.docstatus != 0:
			return 0
		return self.flow.get_planned_output(stage.idx, self.flow.get_card_share(stage.idx, card))

	def get_entries(self):
		entry = frappe.qb.DocType("Stock Entry")
		detail = frappe.qb.DocType("Stock Entry Detail")
		bundle = frappe.qb.DocType("Serial and Batch Entry")
		batch = frappe.qb.DocType("Batch")
		rows = (
			frappe.qb.from_(entry)
			.join(detail)
			.on(detail.parent == entry.name)
			.left_join(bundle)
			.on(bundle.parent == detail.serial_and_batch_bundle)
			.left_join(batch)
			.on(batch.name == bundle.batch_no)
			.select(
				entry.name,
				entry.purpose,
				entry.job_card,
				entry.posting_date,
				entry.posting_time,
				detail.name.as_("detail"),
				detail.item_code,
				detail.item_name,
				detail.qty,
				detail.uom,
				detail.is_finished_item,
				batch.batch_id,
			)
			.where((entry.work_order == self.work_order.name) & (entry.docstatus == 1))
			.orderby(entry.creation, order=frappe.qb.desc)
			.orderby(detail.idx)
			.orderby(bundle.idx)
		).run(as_dict=True)
		return group_entries(rows)

	def get_levels(self):
		rows = [*self.plan.raw_rows, *self.plan.packing_rows]
		return frappe._dict(
			store={row.item_code: self.stock.get((row.item_code, row.source_warehouse), 0) for row in rows},
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
	entries, items = {}, {}
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
		if row.detail not in items:
			items[row.detail] = frappe._dict(
				item_code=row.item_code,
				item_name=row.item_name,
				qty=row.qty,
				uom=row.uom,
				is_finished_item=row.is_finished_item,
				batch_ids=[],
			)
			entry["items"].append(items[row.detail])
		if row.batch_id:
			items[row.detail].batch_ids.append(row.batch_id)
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


def get_union_timing(logs):
	spans = sorted(
		(get_datetime(log.from_time), get_datetime(log.to_time) if log.to_time else None)
		for log in logs
		if log.from_time
	)
	worked, start, end = 0.0, None, None
	for span_start, span_end in spans:
		if start and (end is None or span_start <= end):
			end = None if end is None or span_end is None else max(end, span_end)
			continue
		if start:
			worked += (end - start).total_seconds()
		start, end = span_start, span_end

	if start and end:
		worked += (end - start).total_seconds()
	return worked, start if start and end is None else None


def get_downtime_defaults():
	stop_reason = frappe.get_meta("Downtime Entry").get_field("stop_reason")
	return frappe._dict(
		stop_reasons=[reason for reason in (stop_reason.options or "").split("\n") if reason],
		operator=get_operator(),
	)
