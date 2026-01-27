import json
from datetime import datetime

import frappe

from erpnext.manufacturing.doctype.oven_operation.oven_operation import OvenOperation
from erpnext.manufacturing.doctype.oven_rack.oven_rack import OvenRack
from erpnext.manufacturing.doctype.slab.api import checkout_slab, move_slab_to
from erpnext.manufacturing.doctype.slab.slab import Slab
from erpnext.manufacturing.doctype.slab_history.slab_history import SlabHistory
from erpnext.manufacturing.doctype.job_card.job_card import make_time_log
from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry as wo_make_stock_entry
from frappe.utils import flt
from frappe import _


@frappe.whitelist(allow_guest=True)
def get_oven_from_line(line: str):
	oven_list = frappe.db.get_list("Oven", filters={"line": line})
	if len(oven_list):
		return frappe.get_doc("Oven", oven_list[0].name)

	return None


@frappe.whitelist()
def load_slab_into_oven(oven_op: str, job_card: str):
	oven_operation = json.loads(oven_op)

	new_oven_operation = frappe.new_doc("Oven Operation")
	new_oven_operation.update(oven_operation)

	rack_name = new_oven_operation.oven_rack
	slab_name = new_oven_operation.slab

	now_date_time = datetime.now()

	try:
		frappe.db.begin()

		# Start the Job Card
		start_heating(job_card)

		new_oven_operation.in_time = now_date_time
		new_oven_operation.job_card = job_card
		new_oven_operation.save()

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
		raise

	oven_rack = frappe.get_doc("Oven Rack", rack_name)
	return oven_rack


@frappe.whitelist()
def unload_slab_from_oven(rack_name: str, slab_name: str, slab_template: str, values: str):
	# values is a JSON string containing slab_top_temp, slab_bottom_temp, remarks
	data = json.loads(values)

	# Find active operation for this rack
	op_name = frappe.db.get_value(
		"Oven Operation", {"oven_rack": rack_name, "slab": slab_name, "slab_color": slab_template, "docstatus": 0}, "name"
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

	# Complete the Job Card
	res = {}
	if op.job_card:
		res = finish_heating(op.job_card)

	# Reset Rack
	rack = frappe.get_doc("Oven Rack", rack_name)
	rack.status = "Idle"
	rack.current_slab = None
	rack.current_slab_template = None
	rack.start_time = None
	rack.save()

	# checkout_slab(slab_name)

	op.submit()
	op.save()

	return {
		"rack": rack,
		"finish_results": res
	}


@frappe.whitelist()
def start_heating(job_card):
    """Start the Job Card when heating starts."""
    jc = frappe.get_doc("Job Card", job_card)
    start_time = frappe.utils.now_datetime()
    args = {
        "job_card_id": jc.name,
        "start_time": start_time,
        "status": "Work In Progress",
    }

    make_time_log(args)
    jc.reload()
    jc.job_started = 1
    jc.save(ignore_permissions=True)
    return {
        "status": jc.status,
        "heating_started": jc.job_started,
        "heating_start_time": jc.started_time,
        "current_time": jc.current_time,
    }

@frappe.whitelist()
def finish_heating(job_card):
    """Complete the Job Card when heating is finished."""
    jc = frappe.get_doc("Job Card", job_card)
    job_card_qty = flt(jc.total_completed_qty or jc.for_quantity, 3)
    
    args = {
        "job_card_id": jc.name,
        "complete_time": frappe.utils.now_datetime(),
        "completed_qty": job_card_qty,
        "status": "Completed",
    }

    make_time_log(args)
    last_tl = frappe.get_last_doc("Job Card Time Log", filters={"parent": jc.name})
    if last_tl:
        frappe.db.set_value("Job Card Time Log", last_tl.name, "completed_qty", job_card_qty)

    jc.reload()
    jc.status = "Completed"
    jc.completed_qty = job_card_qty
    jc.job_started = 0
    if jc.docstatus == 0:
        jc.submit()
    else:
        jc.save(ignore_permissions=True)

    jc.reload()
    jc.db_set("status", "Completed")
    jc.reload()

    # Move slab to next stage
    slabs = frappe.get_all("Slab", 
        filters={
            "current_job_card": jc.name,
            "status": "Heating",
            "docstatus": 0
        },
        fields=["name"],
        order_by="creation desc"
    )
    if slabs:
        move_slab_to(slab_number=slabs[0].name, next_stage="Cooling", job_card_number=jc.name, checkout_and_move=True)
    
    work_order = jc.work_order
    wo = frappe.get_doc("Work Order", work_order)
    wo.produced_qty = job_card_qty
    wo.material_transferred_for_manufacturing = job_card_qty
    wo.flags.ignore_validate_update_after_submit = True
    wo.save()
    wo.reload()

    # Create Manufacture Stock Entry
    se_doc = wo_make_stock_entry(work_order, "Manufacture", qty=job_card_qty)
    if isinstance(se_doc, dict):
        stock_entry_manufacture = frappe.get_doc(se_doc)
    else:
        stock_entry_manufacture = se_doc

    # Set warehouses and rates
    for item in stock_entry_manufacture.items:
        if item.is_finished_item:
            item.t_warehouse = wo.fg_warehouse  
            item.qty = job_card_qty
            item.stock_qty = job_card_qty * item.conversion_factor
            item.allow_zero_valuation_rate = 1 
        elif not item.is_scrap_item: 
            item.s_warehouse = wo.source_warehouse
            item.qty = (item.qty/wo.qty) * job_card_qty 
            item.stock_qty = item.qty * item.conversion_factor
            item.allow_zero_valuation_rate = 1 

    stock_entry_manufacture.fg_completed_qty = job_card_qty
    stock_entry_manufacture.save(ignore_permissions=True)
    stock_entry_manufacture.submit()
    
    return {
        "status": wo.get_status(),
        "work_order": work_order,
        "job_card_qty": job_card_qty,
        "stock_entry": stock_entry_manufacture.name
    }
