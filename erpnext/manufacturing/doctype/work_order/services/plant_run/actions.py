import frappe
from frappe import _
from frappe.utils import flt, now_datetime

from erpnext.manufacturing.doctype.job_card.mapper import make_stock_entry as make_transfer_entry
from erpnext.manufacturing.page.shop_floor.shop_floor import submit_quality_inspection


class PlantRun:
	def __init__(self, work_order):
		if isinstance(work_order, str):
			work_order = frappe.get_doc("Work Order", work_order)

		self.work_order = work_order
		if not work_order.is_plant_floor_order:
			frappe.throw(_("Work Order {0} is not made from a Plant Floor").format(work_order.name))

	@property
	def plant_floor(self):
		if not hasattr(self, "_plant_floor"):
			self._plant_floor = frappe.get_doc("Plant Floor", self.work_order.plant_floor)
		return self._plant_floor

	@property
	def active_job_card(self):
		names = frappe.get_all(
			"Job Card",
			filters={"work_order": self.work_order.name, "docstatus": 0, "is_corrective_job_card": 0},
			order_by="operation_row_id asc, creation asc",
			limit=1,
			pluck="name",
		)
		return frappe.get_doc("Job Card", names[0]) if names else None

	def set_qty(self, qty):
		if self.work_order.docstatus != 0:
			frappe.throw(_("The quantity can be changed only before the Work Order starts"))

		self.work_order.qty = flt(qty)
		self.work_order.save()

	def start(self):
		if self.work_order.docstatus == 0:
			self.work_order.submit()

		self.start_job_card(self.active_job_card)

	@staticmethod
	def start_job_card(job_card):
		if job_card and not job_card.time_logs:
			job_card.start_timer(start_time=now_datetime())

	def pause(self):
		self.get_job_card().pause_job(end_time=now_datetime())

	def resume(self):
		self.get_job_card().resume_job(start_time=now_datetime())

	def get_job_card(self, name=None):
		job_card = self.active_job_card
		if not job_card or (name and job_card.name != name):
			frappe.throw(_("Job Card {0} is not the stage in progress").format(name or ""))
		return job_card

	def consume(self, job_card, quantities):
		job_card = self.get_job_card(job_card)
		quantities = {item_code: flt(qty) for item_code, qty in (quantities or {}).items()}
		fixed_items = self.get_fixed_items(job_card)
		quantities.update(
			{row.item_code: row.required_qty for row in job_card.items if row.item_code in fixed_items}
		)
		self.validate_quantities(job_card, quantities)

		for row in job_card.items:
			row.required_qty = quantities[row.item_code]
		job_card.save()

		entry = make_transfer_entry(job_card.name)
		entry.insert()
		entry.submit()
		return entry.name

	def validate_quantities(self, job_card, quantities):
		planned = self.get_planned_quantities(job_card)
		fixed_items = self.get_fixed_items(job_card)
		tolerance = flt(self.plant_floor.formula_tolerance)
		for row in job_card.items:
			actual = quantities.get(row.item_code, 0)
			if actual <= 0:
				frappe.throw(_("{0} needs a quantity above zero").format(row.item_name or row.item_code))

			planned_qty = planned.get(row.item_code)
			if row.item_code in fixed_items or not planned_qty:
				continue

			variance = (actual - planned_qty) / planned_qty * 100
			if abs(variance) > tolerance + 0.0001:
				frappe.throw(
					_("{0} is {1}% off the formula. The allowed range is ±{2}%.").format(
						row.item_name or row.item_code, flt(abs(variance), 1), flt(tolerance)
					)
				)

	def get_planned_quantities(self, job_card):
		return {
			row.item_code: flt(row.required_qty)
			for row in self.work_order.required_items
			if row.operation_row_id == job_card.operation_row_id
		}

	def get_fixed_items(self, job_card):
		balance = {row.item_code for row in self.plant_floor.materials if row.is_balance_item}
		previous = [
			row.finished_good for row in self.work_order.operations if row.idx < job_card.operation_row_id
		]
		return balance | set(previous)

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
		for_quantity = max(flt(job_card.for_quantity), output_qty + rejected_qty)
		job_card.complete_job_card(
			qty=output_qty,
			for_quantity=for_quantity if for_quantity > flt(job_card.for_quantity) else 0,
			process_loss_qty=for_quantity - output_qty,
			end_time=now_datetime(),
			auto_submit=1,
		)

		next_job_card = self.active_job_card
		self.carry_output(job_card, output_qty, next_job_card)
		self.start_job_card(next_job_card)

	@staticmethod
	def carry_output(job_card, output_qty, next_job_card):
		if not next_job_card:
			return

		for row in next_job_card.items:
			if row.item_code == job_card.finished_good:
				row.required_qty = output_qty
		next_job_card.save()
