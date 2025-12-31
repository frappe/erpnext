import frappe
import json
from frappe import _
from frappe.utils import flt
from erpnext.manufacturing.doctype.job_card.job_card import make_time_log, make_stock_entry as jc_make_stock_entry
from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry  as wo_make_stock_entry


@frappe.whitelist()
def start_distribution(job_card):
    """Start the Job Card when mixing starts."""
    jc = frappe.get_doc("Job Card", job_card)
    start_time = frappe.utils.now_datetime()
    args = {
        "job_card_id": jc.name,
        "start_time": start_time,
        "employees": [{"employee": "HR-EMP-00003"}],  # TODO - update operator 
        "status": "Work In Progress",
    }

    make_time_log(args)
    jc.reload()
    jc.job_started = 1
    jc.save(ignore_permissions=True)
    return {
        "status": jc.status,
        "mixer_started": jc.job_started,
        "mixer_start_time": jc.started_time,
        "current_time": jc.current_time,
    }

@frappe.whitelist()
def finish_distribution(job_card):
    """Complete the Job Card when mixing is finished."""
    jc = frappe.get_doc("Job Card", job_card)
    job_card_qty = flt(jc.for_quantity or 0, 3)
    args = {
        "job_card_id": jc.name,
        "complete_time": frappe.utils.now_datetime(),
        "completed_qty": job_card_qty,
        "status": "Completed",
    }

    make_time_log(args)
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

    work_order = jc.work_order
    wo = frappe.get_doc("Work Order", work_order)

    se_doc = wo_make_stock_entry(work_order, "Manufacture", qty=job_card_qty)
    if isinstance(se_doc, dict):
        se = frappe.get_doc(se_doc)
    else:
        se = se_doc

    for item in se.items:
        if item.is_finished_item:
            item.t_warehouse = wo.fg_warehouse  
            item.qty = job_card_qty
        elif not item.is_scrap_item: 
            item.s_warehouse = wo.source_warehouse

    se.fg_completed_qty = job_card_qty
    se.for_quantity = job_card_qty 
    fg_item = next((item for item in se.items if item.is_finished_item), None)
    if fg_item:
        fg_item.qty = job_card_qty
        fg_item.stock_qty = job_card_qty
    se.save()
    se.submit()

    wo.update_work_order_qty()
    wo.reload()
    wo_status = wo.get_status()
    # next_bom_data = get_next_process_bom_qty(work_order)
    
    return {
        "status": wo_status,
        "work_order_status": wo_status,
        "work_order": work_order,
        "job_card_qty": job_card_qty,
        "produced_qty": wo.produced_qty,
        "total_qty": wo.qty,
        "stock_entry": se.name,
        # "bom_qty": next_bom_data["bom_qty"], 
        # "next_work_order": next_bom_data["next_work_order"],
        "message": f"SE {se.name} ({job_card_qty} qty). WO: {wo_status}"
    }
    