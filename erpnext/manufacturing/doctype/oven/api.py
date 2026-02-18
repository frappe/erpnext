import json
import frappe

from erpnext.manufacturing.doctype.job_card.job_card import JobCard
from erpnext.manufacturing.doctype.production_line.production_line import get_all_child_lines
from erpnext.manufacturing.doctype.oven.oven import Oven
from erpnext.manufacturing.doctype.oven_operation.oven_operation import OvenOperation
from erpnext.manufacturing.doctype.oven_rack.oven_rack import OvenRack
from erpnext.manufacturing.doctype.slab.slab import Slab
from erpnext.manufacturing.doctype.slab_history.slab_history import SlabHistory
from erpnext.manufacturing.page.operator_station.operator_station import (
	finish_process,
	get_top_job_card_for_process,
	start_process,
	stop_machine,
)


@frappe.whitelist(allow_guest=True)
def get_oven_from_line(line: str):
	oven_list = frappe.db.get_list("Oven", filters={"line": line})
	if len(oven_list):
		return frappe.get_doc("Oven", oven_list[0].name)

	return None


@frappe.whitelist()
def load_slab_into_oven(oven_op: str, line: str, job_card_name: str, slab_template: str):
	oven_operation = json.loads(oven_op)

	new_oven_operation: OvenOperation = frappe.new_doc("Oven Operation")
	new_oven_operation.update(oven_operation)

	rack_name = new_oven_operation.oven_rack
	slab_name = new_oven_operation.slab
	oven_rack: OvenRack = frappe.get_doc("Oven Rack", rack_name)
	# slab: Slab = frappe.get_doc("Slab", slab_name)
	child_lines = get_all_child_lines(line)

	if not job_card_name:
		jc: JobCard = get_top_job_card_for_process(
			"Heating", child_lines if child_lines else line, include_wip=False
		)
		job_card_name = jc.name

	now_date_time = frappe.utils.now_datetime()

	try:
		frappe.db.begin()

		# Start the Job Card
		start_process(job_card_name, slab_name, slab_template, "Heating")
		slab: Slab = frappe.get_doc("Slab", slab_name)

		new_oven_operation.in_time = now_date_time
		new_oven_operation.job_card = job_card_name
		new_oven_operation.save()

		heating_slab_history_item: SlabHistory = [h for h in slab.slab_history if h.station == "Heating"][0]

		if heating_slab_history_item.out_time is not None:
			raise Exception("Slab is in an invalid state")

		heating_slab_history_item.oven_params = new_oven_operation.name
		heating_slab_history_item.save()

		oven_rack.current_slab = slab_name
		oven_rack.current_slab_template = slab.template
		oven_rack.start_time = now_date_time
		oven_rack.status = "Heating"
		oven_rack.save()

		frappe.db.commit()
	except Exception:
		frappe.db.rollback()
		raise

	oven_rack = frappe.get_doc("Oven Rack", rack_name)
	return oven_rack


@frappe.whitelist()
def unload_slab_from_oven(rack_name: str, slab_name: str, slab_template: str, values: str):
	# values is a JSON string containing slab_top_temp, slab_bottom_temp, remarks
	data = json.loads(values)

	# Find active operation for this rack
	op_name = frappe.db.get_value(
		"Oven Operation",
		{"oven_rack": rack_name, "slab": slab_name, "slab_color": slab_template, "docstatus": 0},
		"name",
	)
	if not op_name:
		frappe.throw("No active operation found for this rack")

	op: OvenOperation = frappe.get_doc("Oven Operation", op_name)

	now = frappe.utils.now_datetime()
	op.out_time = now
	op.slab_top_temp = data.get("slab_top_temp")
	op.slab_bottom_temp = data.get("slab_bottom_temp")
	op.remarks = data.get("remarks")

	# Calculate total time
	if op.in_time and op.out_time:
		duration = op.out_time - op.in_time
		op.total_time = duration.total_seconds() / 60

	# Reset Rack
	rack: OvenRack = frappe.get_doc("Oven Rack", rack_name)
	rack.status = "Idle"
	rack.current_slab = None
	rack.current_slab_template = None
	rack.start_time = None

	try:
		frappe.db.begin()
		rack.save()

		op.submit()
		op.save()

		# Complete the Job Card
		if op.job_card:
			finish_process(op.job_card, "Heating", should_stop_machine=False)
			# Check if any of the racks in the oven are in use
			oven: Oven = frappe.get_doc("Oven", rack.parent)

			# Stop the oven only if all the racks are idle.
			is_in_use = False
			for rack in oven.racks:
				if rack.status == "Heating":
					is_in_use = True
					break

			if not is_in_use:
				stop_machine("Heating", oven.line, None)

		frappe.db.commit()

	except Exception:
		frappe.db.rollback()
		raise

	return {"rack": rack}
