import frappe
import json
from frappe import _
from frappe.utils import flt
from erpnext.manufacturing.doctype.job_card.job_card import make_stock_entry
from erpnext.manufacturing.doctype.job_card.job_card import make_time_log

@frappe.whitelist()
def get_mixer_state(job_card):
    jc = frappe.get_doc("Job Card", job_card)
    return {
        "status": jc.status,
        "docstatus": jc.docstatus,
        "mixer_materials_confirmed": jc.transferred_qty > 0,
        "mixer_started": 1 if jc.time_logs else 0,
        "mixer_start_time": jc.started_time,
        "mixer_finished": jc.current_time or 0, 
    }

@frappe.whitelist()
def get_mixer_ingredients(job_card):
    jc = frappe.get_doc("Job Card", job_card)
    if not jc.bom_no:
        frappe.throw(_("No BOM set on Job Card {0}").format(job_card))

    jc.reload()

    bom_doc = frappe.get_doc("BOM", jc.bom_no)
    bom_by_code = {row.item_code: row for row in bom_doc.items}
    ingredients = []
    for row in jc.items:
        bom_row = bom_by_code.get(row.item_code)
        if not bom_row:
            continue

        qty = flt(row.required_qty) or flt(bom_row.stock_qty)

        # qty = flt(row.stock_qty) 
        ingredients.append({
            "item_code": row.item_code,
            "item_name": row.item_name,
            "stock_uom": row.stock_uom,
            "stock_uom_qty": qty,
            "additional_ingredients_added": getattr(row, "additional_ingredients_added", 0)
        })

    return ingredients


@frappe.whitelist()
def confirm_materials(job_card, ingredients):
    """Create Stock Entry from mixer quantities and mark Job Card ready."""
    ingredients = json.loads(ingredients)
    jc = frappe.get_doc("Job Card", job_card)

    qty_by_code = {ing["item_code"]: flt(ing["qty"]) for ing in ingredients}
    added_by_code = {ing["item_code"]: bool(ing.get("is_added")) for ing in ingredients}

    for row in jc.items:
        if row.item_code in qty_by_code:
            row.required_qty = qty_by_code[row.item_code]
            row.additional_ingredients_added = added_by_code.get(row.item_code, 0)

    jc.save(ignore_permissions=True)

    se = make_stock_entry(job_card)
    if not se.items:
        frappe.throw(_("No remaining quantity to transfer for Job Card {0}.").format(job_card))

    se.insert()
    se.submit()
    return {"stock_entry": se.name}

@frappe.whitelist()
def start_mixing(job_card):
    """Start the Job Card when mixing starts."""
    jc = frappe.get_doc("Job Card", job_card)
    start_time = frappe.utils.now_datetime()
    args = {
        "job_card_id": jc.name,
        "start_time": start_time,
        "employees": [{"employee": "HR-EMP-00002"}], 
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
def finish_mixing(job_card, completed_qty):
    """Complete the Job Card when mixing is finished."""
    jc = frappe.get_doc("Job Card", job_card)

    args = {
        "job_card_id": jc.name,
        "complete_time": frappe.utils.now_datetime(),
        "completed_qty": float(completed_qty or 0),
        "status": "Completed",
    }

    make_time_log(args)
    jc.reload()
    jc.status = "Completed"
    jc.completed_qty = float(completed_qty or 0)
    jc.job_started = 0
    if jc.docstatus == 0:
        jc.submit()
    else:
        jc.save(ignore_permissions=True)

    return {
        "status": jc.status,
        "docstatus": jc.docstatus,
    }

