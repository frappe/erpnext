import frappe
from frappe import _
from frappe.utils import flt, now_datetime

from erpnext.manufacturing.doctype.job_card.job_card import OverlapError
from erpnext.manufacturing.doctype.job_card.mapper import make_stock_entry as make_transfer_entry
from erpnext.manufacturing.doctype.work_order.mapper import create_job_card
from erpnext.manufacturing.doctype.work_order.services.plant_run.flow import EPSILON, PlantFlow
from erpnext.manufacturing.doctype.work_order.services.plant_run.lot import Lot
from erpnext.manufacturing.doctype.work_order.services.plant_run.picks import (
	PickedSerialBatch,
	get_pick_options,
)
from erpnext.manufacturing.page.shop_floor.shop_floor import submit_quality_inspection


class MachineBusyError(frappe.ValidationError):
	pass


class PlantRun:
	def __init__(self, work_order: str):
		self.work_order = frappe.get_doc("Work Order", work_order)
		if not self.work_order.track_semi_finished_goods:
			frappe.throw(
				_(
					"Work Order {0} does not make an item at each operation, so the Plant Builder cannot run it"
				).format(work_order)
			)

	def get_flow(self):
		return PlantFlow(self.work_order)

	def get_open_job_card(self, stage_idx):
		card = self.get_flow().get_open_card(stage_idx)
		return frappe.get_doc("Job Card", card.name) if card else None

	def get_job_card(self, name):
		job_card = frappe.get_doc("Job Card", name)
		if job_card.work_order != self.work_order.name or job_card.docstatus != 0:
			frappe.throw(_("Job Card {0} is not an open stage of this Work Order").format(name))
		return job_card

	def get_running_job_cards(self):
		names = frappe.get_all(
			"Job Card",
			filters={"work_order": self.work_order.name, "docstatus": 0, "is_corrective_job_card": 0},
			pluck="name",
		)
		return [job_card for job_card in map(self.get_job_card, names) if job_card.time_logs]

	def set_qty(self, qty):
		if self.work_order.docstatus != 0:
			frappe.throw(_("The quantity can be changed only before the Work Order starts"))

		self.work_order.qty = flt(qty)
		self.work_order.save()

	def start(self, job_card=None):
		if self.work_order.docstatus == 0:
			self.work_order.submit()
			return self.start_ready_stages()

		flow = self.get_flow()
		names = [job_card] if job_card else [card.name for card in self.get_startable_cards(flow)]
		for card in map(self.get_job_card, names):
			if not flow.has_input(card.operation_row_id):
				frappe.throw(_("{0} waits for the stages before it").format(card.operation))
			self.validate_machine_is_free(card)
			self.start_job_card(card)

	@staticmethod
	def get_startable_cards(flow):
		cards = [flow.get_open_card(stage.idx) for stage in flow.stages if flow.has_input(stage.idx)]
		return [card for card in cards if card and not card.started_at]

	@staticmethod
	def start_job_card(job_card, wait_if_reserved=False):
		if job_card.time_logs:
			return

		try:
			frappe.db.savepoint("start_stage")
			job_card.start_timer(start_time=now_datetime())
		except OverlapError:
			frappe.db.rollback(save_point="start_stage")
			frappe.clear_last_message()
			if not wait_if_reserved:
				frappe.throw(
					_(
						"{0} is reserved for another Job Card by capacity planning. Start this stage when its slot is free, or turn off capacity planning in Manufacturing Settings."
					).format(frappe.bold(job_card.workstation)),
					MachineBusyError,
				)

	def pause(self):
		running = [job_card for job_card in self.get_running_job_cards() if not job_card.is_paused]
		if not running:
			frappe.throw(_("No stage is running"))
		for job_card in running:
			job_card.pause_job(end_time=now_datetime())

	def resume(self):
		for job_card in self.get_running_job_cards():
			if job_card.is_paused and not is_broken_down(job_card.workstation):
				job_card.resume_job(start_time=now_datetime())

	def report_breakdown(self, job_card):
		job_card = self.get_job_card(job_card)
		if job_card.is_paused or not job_card.time_logs:
			frappe.throw(_("Only a running machine can be stopped for a breakdown"))

		job_card.pause_job(end_time=now_datetime())
		frappe.get_doc("Workstation", job_card.workstation).db_set("status", "Problem", notify=True)

	def restart_machine(self, job_card, stop_reason, remarks=None, operator=None):
		job_card = self.get_job_card(job_card)
		if not is_broken_down(job_card.workstation):
			frappe.throw(_("{0} is not stopped for a breakdown").format(frappe.bold(job_card.workstation)))

		operator = operator or get_operator()
		if not operator:
			frappe.throw(_("Pick the operator who reports the breakdown"))

		downtime = frappe.get_doc(
			{
				"doctype": "Downtime Entry",
				"workstation": job_card.workstation,
				"operator": operator,
				"from_time": job_card.time_logs[-1].to_time,
				"to_time": now_datetime(),
				"stop_reason": stop_reason,
				"remarks": remarks,
			}
		).insert()

		frappe.get_doc("Workstation", job_card.workstation).db_set("status", "Idle", notify=True)
		job_card.resume_job(start_time=now_datetime())
		return downtime.name

	def preview(self, job_card, quantities):
		return Lot(self.get_flow(), self.get_job_card(job_card), quantities).get_preview()

	def consume(self, job_card, quantities, picks=None):
		job_card = self.get_job_card(job_card)
		if job_card.is_paused:
			frappe.throw(_("Resume the Work Order before you consume materials"))

		lot = Lot(self.get_flow(), job_card, quantities)
		lot.validate()
		quantities = lot.resolved_quantities

		job_card.db_set("for_quantity", lot.for_quantity)
		job_card.set("items", [row for row in job_card.items if quantities[row.name] > 0])
		for row in job_card.items:
			row.required_qty = quantities[row.name]
		job_card.save()

		entry = make_transfer_entry(job_card.name)
		PickedSerialBatch(entry, picks).apply()
		entry.insert()
		entry.submit()
		return entry.name

	def get_pick_options(self, job_card, row_name):
		row = next((row for row in self.get_job_card(job_card).items if row.name == row_name), None)
		if not row:
			frappe.throw(_("This stage does not consume that material"))
		return get_pick_options(row.item_code, row.source_warehouse)

	def produce(self, job_card, output_qty, rejected_qty=0, readings=None):
		job_card = self.get_job_card(job_card)
		if job_card.is_paused:
			frappe.throw(_("Resume the Work Order before you record the output"))
		if not any(flt(row.transferred_qty) for row in job_card.items):
			frappe.throw(_("Consume the materials of this stage first"))

		if readings and job_card.quality_inspection_template:
			readings = [{**row, "reading_value": str(row.get("reading_value") or "")} for row in readings]
			submit_quality_inspection(job_card.name, frappe.as_json(readings))
			job_card.reload()

		output_qty, rejected_qty = flt(output_qty), flt(rejected_qty)
		for_quantity = flt(job_card.for_quantity)
		if output_qty + rejected_qty > for_quantity + EPSILON:
			frappe.throw(
				_("You cannot make more than {0} {1} from the materials that went in").format(
					for_quantity, frappe.get_cached_value("Item", job_card.finished_good, "stock_uom")
				)
			)

		job_card.complete_job_card(
			qty=output_qty,
			process_loss_qty=for_quantity - output_qty,
			end_time=now_datetime(),
			auto_submit=1,
		)
		self.make_lots()
		self.start_ready_stages()

	def make_lots(self):
		flow = self.get_flow()
		for stage in flow.stages:
			if stage.inputs and not flow.get_open_card(stage.idx) and flow.has_input(stage.idx):
				self.make_lot(flow, stage)

	def make_lot(self, flow, stage):
		waiting = {(row.item_code, row.warehouse): row.waiting_qty for row in flow.get_inputs(stage.idx)}
		qty = flow.get_planned_output(stage.idx, flow.get_lot_share(stage.idx, waiting))
		operation = self.work_order.operations[stage.idx - 1]
		create_job_card(
			self.work_order, frappe._dict(operation.as_dict(), job_card_qty=qty), auto_create=True
		)

	def start_ready_stages(self):
		for card in self.get_startable_cards(self.get_flow()):
			job_card = frappe.get_doc("Job Card", card.name)
			if not self.get_busy_job_cards(job_card) and not is_broken_down(job_card.workstation):
				self.start_job_card(job_card, wait_if_reserved=True)

	def validate_machine_is_free(self, job_card):
		if is_broken_down(job_card.workstation):
			frappe.throw(
				_("{0} is stopped for a breakdown. Restart it first.").format(
					frappe.bold(job_card.workstation)
				),
				MachineBusyError,
			)

		if busy := self.get_busy_job_cards(job_card):
			frappe.throw(
				_("{0} is busy with {1}. Start this stage when it is free.").format(
					frappe.bold(job_card.workstation), ", ".join(busy)
				),
				MachineBusyError,
			)

	@staticmethod
	def get_busy_job_cards(job_card):
		busy = frappe.get_all(
			"Job Card",
			filters={
				"workstation": job_card.workstation,
				"docstatus": 0,
				"status": ("in", ["Work In Progress", "On Hold"]),
				"name": ("!=", job_card.name),
			},
			pluck="name",
		)
		return busy if len(busy) >= job_card.get_production_capacity() else []


def is_broken_down(workstation):
	return frappe.db.get_value("Workstation", workstation, "status") == "Problem"


def get_operator():
	return frappe.db.get_value("Employee", {"user_id": frappe.session.user, "status": "Active"})
