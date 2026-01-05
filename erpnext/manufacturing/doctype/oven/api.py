import json
from datetime import datetime

import frappe

from erpnext.manufacturing.doctype.oven_operation.oven_operation import OvenOperation
from erpnext.manufacturing.doctype.oven_rack.oven_rack import OvenRack
from erpnext.manufacturing.doctype.slab.api import checkout_slab, move_slab_to
from erpnext.manufacturing.doctype.slab.slab import Slab
from erpnext.manufacturing.doctype.slab_history.slab_history import SlabHistory


@frappe.whitelist(allow_guest=True)
def get_oven_from_line(line: str):
	oven_list = frappe.db.get_list("Oven", filters={"line": line})
	if len(oven_list):
		return frappe.get_doc("Oven", oven_list[0].name)

	return None


@frappe.whitelist()
def load_slab_into_oven(oven_op: str):
	oven_operation = json.loads(oven_op)

	new_oven_operation = frappe.new_doc("Oven Operation")
	new_oven_operation.update(oven_operation)

	rack_name = new_oven_operation.oven_rack
	slab_name = new_oven_operation.slab

	now_date_time = datetime.now()

	try:
		frappe.db.begin()

		# Create a job card and get its number
		job_card = "ABC-123-231"
		# TODO: Create a new job card using a built-in method.

		new_oven_operation.in_time = now_date_time
		new_oven_operation.job_card = job_card
		new_oven_operation.save()

		move_slab_to(slab_name, "Heating", job_card)

		slab: Slab = frappe.get_doc("Slab", slab_name)
		heating_slab_history_item: SlabHistory = slab.slab_history[-1]

		if heating_slab_history_item.out_time is not None:
			raise Exception("Slab is in an invalid state")

		heating_slab_history_item.oven_params = new_oven_operation.name
		heating_slab_history_item.save()

		oven_rack: OvenRack = frappe.get_doc("Oven Rack", rack_name)
		oven_rack.current_slab = slab_name
		oven_rack.current_slab_template = slab.template
		oven_rack.start_time = now_date_time
		oven_rack.status = "Heating"
		oven_rack.save()

		frappe.db.commit()
	except Exception:
		frappe.db.rollback()

	oven_rack = frappe.get_doc("Oven Rack", rack_name)
	return oven_rack


@frappe.whitelist()
def unload_slab_from_oven(rack_name: str, slab_name: str, slab_template: str, values: str):
	# values is a JSON string containing slab_top_temp, slab_bottom_temp, remarks
	data = json.loads(values)

	# Find active operation for this rack
	op_name = frappe.db.get_value(
		"Oven Operation", {"oven_rack": rack_name, "slab": slab_name, "slab_color": slab_template}, "name"
	)
	if not op_name:
		frappe.throw("No active operation found for this rack")

	op = frappe.get_doc("Oven Operation", op_name)

	now = datetime.now()
	op.out_time = now
	op.slab_top_temp = data.get("slab_top_temp")
	op.slab_bottom_temp = data.get("slab_bottom_temp")
	op.remarks = data.get("remarks")

	# Calculate total time
	if op.in_time and op.out_time:
		duration = op.out_time - op.in_time
		op.total_time = duration.total_seconds() / 60

	# Reset Rack
	rack = frappe.get_doc("Oven Rack", rack_name)
	rack.status = "Idle"
	rack.current_slab = None
	rack.current_slab_template = None
	rack.start_time = None
	rack.save()

	checkout_slab(slab_name)

	op.submit()
	op.save()

	return rack
