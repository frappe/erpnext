import frappe
import json
from frappe import _
from frappe.utils import flt
from erpnext.manufacturing.doctype.job_card.job_card import make_time_log, make_stock_entry as jc_make_stock_entry
from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry  as wo_make_stock_entry

@frappe.whitelist()
def get_mixer_state(job_card):
    jc = frappe.get_doc("Job Card", job_card)
    wo = frappe.get_doc("Work Order", jc.work_order) if jc.work_order else None
    return {
        "status": jc.status,
        "docstatus": jc.docstatus,
        "mixer_materials_confirmed": jc.transferred_qty > 0,
        "mixer_started": 1 if jc.time_logs else 0,
        "mixer_start_time": jc.started_time,
        "mixer_finished": jc.current_time or 0, 
        "job_card_submitted": jc.status == "Completed",
        "job_card_completed": jc.total_completed_qty > 0,
        "prepared_qty": wo.produced_qty if wo else jc.total_completed_qty,
        "stock_entry_name": wo.produced_qty > 0 and "MFG-SE-*" or "",
        "work_order_status": wo.get_status() if wo else "Draft"
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

    se = jc_make_stock_entry(job_card)
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
        "employees": [{"employee": "HR-EMP-00003"}], 
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
    jc.db_set("status", "Completed")  # Direct DB update
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
    next_bom_data = get_next_process_bom_qty(work_order)
    
    return {
        "status": wo_status,
        "work_order_status": wo_status,
        "work_order": work_order,
        "job_card_qty": job_card_qty,
        "produced_qty": wo.produced_qty,
        "total_qty": wo.qty,
        "stock_entry": se.name,
        "bom_qty": next_bom_data["bom_qty"], 
        "next_work_order": next_bom_data["next_work_order"],
        "message": f"SE {se.name} ({job_card_qty} qty). WO: {wo_status}"
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
    se_item.qty = float(qty)  
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

@frappe.whitelist()
def transfer_to_next_process(mixing_work_order, qty=None):
    """Transfer FG from Mixing → Next Process Source Warehouse."""

    mixing_wo = frappe.get_doc("Work Order", mixing_work_order)
    fg_item = mixing_wo.production_item
    fg_qty = flt(qty or mixing_wo.produced_qty)
    
    process_mapping = {
        "Mixing": "Distribution",
        "Distribution": "Pressing", 
        "Pressing": "Heating",
        "Heating": "Cooling",
        "Cooling": "Trimming",
        "Trimming": "Calibration",
        "Calibration": "Polishing",
        "Polishing": "Quality Analysis"
    }

    current_process = mixing_wo.description.split(" - ")[-1].strip() if " - " in mixing_wo.description else ""
    next_process = process_mapping.get(current_process)
    
    if not next_process:
        frappe.throw(_("No next process found after {0}").format(current_process))
    
    next_wo = frappe.db.get_value("Work Order", {
        "production_plan": mixing_wo.production_plan,
        "description": ["like", f"%{next_process}%"],
        "docstatus": ["<", 2] 
    }, "name")
    
    if not next_wo:
        all_wos = frappe.get_all("Work Order", 
            filters={"production_plan": mixing_wo.production_plan},
            fields=["name", "production_item", "description"]
        )
        frappe.throw(f"Next WO for '{next_process}' not found.")
    
    next_wo_doc = frappe.get_doc("Work Order", next_wo)
    bom_doc = frappe.get_doc("BOM", next_wo_doc.bom_no)

    transfer_qty = 0
    for bom_item in bom_doc.items:
        if bom_item.item_code == fg_item:  
            transfer_qty = flt(bom_item.stock_qty) 
            break
    
    if transfer_qty == 0:
        frappe.throw(f"BOM qty for {fg_item} not found in {next_wo} BOM")
        
    se = frappe.new_doc("Stock Entry")
    se.purpose = "Material Transfer for Manufacture"
    se.work_order = next_wo
    se.job_card = ""  # No job card for inter-process transfer
    se.company = mixing_wo.company
    se.fg_completed_qty = transfer_qty
    
    se.append("items", {
        "item_code": fg_item,
        "qty": transfer_qty,
        "stock_uom": mixing_wo.stock_uom,
        "uom": mixing_wo.stock_uom,  
        "conversion_factor": 1.0, 
        "s_warehouse": mixing_wo.fg_warehouse,      
        "t_warehouse": next_wo_doc.wip_warehouse,   
        "basic_rate": 0  
    })
    
    se.set_stock_entry_type()
    se.set_missing_values()
    se.submit()
    
    return {
        "status": "Success",
        "transfer_se": se.name,
        "next_work_order": next_wo,
        "qty_transferred": transfer_qty,
        "from_warehouse": mixing_wo.fg_warehouse,
        "to_warehouse": next_wo_doc.wip_warehouse,
        "message": f"Transferred {fg_qty} {fg_item} to {next_wo}"
    }


@frappe.whitelist()
def get_next_process_bom_qty(mixing_work_order):
    """Get BOM qty required for NEXT process"""
    mixing_wo = frappe.get_doc("Work Order", mixing_work_order)
    current_process = mixing_wo.description.split(" - ")[-1].strip()
    process_mapping = {
        "Mixing": "Distribution",
        "Distribution": "Pressing", 
        "Pressing": "Heating",
        "Heating": "Cooling",
        "Cooling": "Trimming",
        "Trimming": "Calibration",
        "Calibration": "Polishing",
        "Polishing": "Quality Analysis"
    }
    next_process = process_mapping.get(current_process)
    
    next_wo = frappe.db.get_value("Work Order", {
        "production_plan": mixing_wo.production_plan,
        "description": ["like", f"%{next_process}%"],
        "docstatus": ["<", 2]
    }, "name")
    
    if not next_wo:
        return {"bom_qty": 0}
    
    next_wo_doc = frappe.get_doc("Work Order", next_wo)
    bom_doc = frappe.get_doc("BOM", next_wo_doc.bom_no)
    fg_item = mixing_wo.production_item
    
    for bom_item in bom_doc.items:
        if bom_item.item_code == fg_item:
            return {
                "bom_qty": flt(bom_item.stock_qty),
                "next_work_order": next_wo,
                "next_process": next_process
            }
    
    return {"bom_qty": 0}

@frappe.whitelist()
def get_all_mixers(job_card, production_line=None):
    filters = {}
    if job_card:
        jc = frappe.get_doc("Job Card", job_card)
        filters["line_no"] = jc.production_line or production_line
    
    mixers_list = frappe.get_all("Mixer", filters=filters, order_by="line_no")
    return mixers_list

@frappe.whitelist()
def assign_mixer_to_job_card(job_card, mixer):
    jc = frappe.get_doc("Job Card", job_card)
    mixer_number = frappe.get_doc("Mixer", mixer)

    jc.mixer_number = mixer_number
    
    jc.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "status": "success",
        "mixer_number": mixer_number
    }