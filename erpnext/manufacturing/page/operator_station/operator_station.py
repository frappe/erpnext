import frappe
import json
from frappe import _
from frappe.utils import flt
from erpnext.manufacturing.doctype.job_card.job_card import make_time_log, make_stock_entry as jc_make_stock_entry
from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry  as wo_make_stock_entry

@frappe.whitelist()
def get_operator_state(job_card):
    jc = frappe.get_doc("Job Card", job_card)
    if (jc.work_order):
        wo = frappe.get_doc("Work Order", jc.work_order)
    else:
        None

    state = {
        "distribution_started": 1 if jc.time_logs else 0,
        "distribution_start_time": jc.started_time,
        "job_card_submitted": jc.status == "Completed",
        "stock_entry_name":  wo.produced_qty > 0 and "MFG-SE-*" or ""
    }
    return state

@frappe.whitelist()
def start_distribution(job_card):
    """Start the Job Card when mixing starts."""
    print(f"DEBUG: Header transferred_qty={frappe.get_doc("Job Card", job_card)}")

    jc = frappe.get_doc("Job Card", job_card)
    start_time = frappe.utils.now_datetime()
    args = {
        "job_card_id": jc.name,
        "start_time": start_time,
        "employees": [{"employee": "HR-EMP-00002"}],  # TODO - update operator 
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
    job_card_qty = flt(jc.for_quantity, 3)
    total_transferred = sum([item.transferred_qty for item in jc.items])
    jc.transferred_qty = total_transferred  # Force header update!
    
    print(f"DEBUG: Header transferred_qty={jc.transferred_qty}, items sum={total_transferred}")
    bom_doc = frappe.get_doc("BOM", jc.bom_no)
    bom_qty = 0

    for bom_item in bom_doc.items:
        bom_qty = flt(bom_item.qty)
        
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
    wo.reload()

    se_doc = wo_make_stock_entry(work_order, "Manufacture", qty=job_card_qty)
    if isinstance(se_doc, dict):
        stock_entry_manufacture = frappe.get_doc(se_doc)
    else:
        stock_entry_manufacture = se_doc

    for item in stock_entry_manufacture.items:
        if item.is_finished_item:
            item.t_warehouse = wo.fg_warehouse  
            item.qty = bom_qty
            item.stock_qty = job_card_qty * item.conversion_factor
        elif not item.is_scrap_item: 
            item.s_warehouse = wo.source_warehouse
            item.qty = (item.qty/wo.qty) * job_card_qty 
            item.stock_qty = item.qty * item.conversion_factor

    # stock_entry_manufacture.fg_completed_qty = job_card_qty
    # stock_entry_manufacture.for_quantity = job_card_qty 
    fg_item = next((item for item in stock_entry_manufacture.items if item.is_finished_item), None)
    if fg_item:
        fg_item.qty = job_card_qty
        fg_item.stock_qty = job_card_qty

    stock_entry_manufacture.save(ignore_permissions=True)
    stock_entry_manufacture.submit()
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
        "stock_entry": stock_entry_manufacture.name,
        # "bom_qty": next_bom_data["bom_qty"], 
        # "next_work_order": next_bom_data["next_work_order"],
        "message": f"SE {stock_entry_manufacture.name} ({job_card_qty} qty). WO: {wo_status}"
    }
    