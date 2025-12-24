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

    total_qty = sum(row.required_qty for row in jc.items if row.required_qty > 0)
    jc.for_quantity = total_qty

    jc.save(ignore_permissions=True)

    se = make_stock_entry(job_card)
    if not se.items:
        frappe.throw(_("No remaining quantity to transfer for Job Card {0}.").format(job_card))

    se.insert()
    se.submit()
    return {
        "stock_entry": se.name,
        "total_for_quantity": total_qty,  
    }

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

@frappe.whitelist()
def quick_add_raw_materials(job_card, raw_material, qty):
    """Dialog → Creates Doctype record + Stock Entry."""
    add_doc = frappe.new_doc("Add Raw Materials")
    add_doc.job_card = job_card
    add_doc.raw_material = raw_material
    add_doc.qty = float(qty)
    add_doc.insert()
    add_doc.submit()

    jc = frappe.get_doc("Job Card", job_card)
    target_row = next((row for row in jc.items if row.item_code == raw_material), None)
    if not target_row:
        frappe.throw(_("No Job Card Item matches <b>{0}</b>").format(raw_material))
    if not target_row.source_warehouse:
        frappe.throw(_("No Source Warehouse for {0}").format(raw_material))
    
    target_row.required_qty += float(qty)

    total_qty = sum(row.required_qty for row in jc.items if row.required_qty > 0)
    jc.for_quantity = total_qty

    jc.flags.ignore_validate = True
    jc.save(ignore_permissions=True)
    
    se = frappe.new_doc("Stock Entry")
    se.job_card = job_card
    se.work_order = jc.work_order
    se.purpose = "Material Transfer for Manufacture"
    se.from_bom = 1

    se_item = se.append("items", {})
    se_item.item_code = raw_material
    se_item.item_name = target_row.item_name
    se_item.description = target_row.description or ""
    se_item.s_warehouse = target_row.source_warehouse
    se_item.qty = float(qty)  # ONLY added qty
    se_item.uom = target_row.uom
    se_item.stock_uom = target_row.stock_uom
    se_item.job_card_item = target_row.name
    se_item.t_warehouse = jc.wip_warehouse or jc.warehouse
    if not se_item.conversion_factor:
        se_item.conversion_factor = 1

    se.set_missing_values()
    se.set_stock_entry_type()
    # se.get_item_details()
    
    if not se.items:
        frappe.throw(_("No quantity to transfer"))

    se.insert()
    se.submit()

    jc = frappe.get_doc("Job Card", job_card)
    for row in jc.items:
        row.transferred_qty = row.required_qty
    jc.transferred_qty = total_qty

    jc.flags.ignore_validate = True
    jc.flags.ignore_validate_update_after_submit = True
    jc.save(ignore_permissions=True)

    frappe.db.commit()

    return {
        "success": True, 
        "stock_entry": se.name,
        "add_raw_doc": add_doc.name,
        "source_wh": target_row.source_warehouse,
        "new_item_qty": target_row.required_qty,
        "total_for_quantity": total_qty,
        "items_count": len(jc.items)
    }