import frappe
from frappe import _
from frappe.utils import flt

@frappe.whitelist()
def transfer_to_next_process(current_work_order, qty=None):
    """Transfer FG from Mixing → Next Process Source Warehouse."""
    wo = frappe.get_doc("Work Order", current_work_order)
    fg_item = wo.production_item
    fg_qty = flt(qty or wo.produced_qty)
    
    process_mapping = {
        "mixing": "distribution",
        "distribution": "pressed slab", 
        "pressed slab": "heated slab",
        "heated slab": "cooled slab",
        "cooled slab": "trimmed slab",
        "trimmed slab": "calibrated slab",
        "calibrated slab": "polished slab",
        "polished slab": "inspected slab"
    }

    current_process = wo.production_item.split(" - ")[-1].strip().lower() if " - " in wo.production_item else ""
    next_process = process_mapping.get(current_process)
    
    if not next_process:
        frappe.throw(_("No next process found after {0}").format(current_process))
    
    next_wo = frappe.db.get_value("Work Order", {
        "production_plan": wo.production_plan,
        "production_item": ["like", f"%{next_process}%"],
        "docstatus": ["<", 2] 
    }, "name")
    
    if not next_wo:
        all_wos = frappe.get_all("Work Order", 
            filters={"production_plan": wo.production_plan},
            fields=["name", "production_item"]
        )
        frappe.throw(f"Next WO for '{next_process}' not found.")
    
    next_wo_doc = frappe.get_doc("Work Order", next_wo)
    open_job_card = frappe.db.get_value("Job Card", {
        "work_order": next_wo,
        "status": "Open",
        "docstatus": 0
    }, "name", order_by="creation asc")

    if not open_job_card:
        frappe.throw(f"No open job cards available")
    bom_doc = frappe.get_doc("BOM", next_wo_doc.bom_no)

    transfer_qty = 0
    for bom_item in bom_doc.items:
        if bom_item.item_code == fg_item:  
            transfer_qty = flt(bom_item.stock_qty) 
            break
    
    if transfer_qty == 0:
        frappe.throw(f"BOM qty for {fg_item} not found in {next_wo} BOM")

    job_card_item = frappe.db.get_value("Job Card Item", {
        "parent": open_job_card,
        "item_code": fg_item,
        "parenttype": "Job Card"
    }, "name")
    
    if not job_card_item:
        frappe.throw(f"No Job Card Item found for {fg_item} in {open_job_card}")
        
    se = frappe.new_doc("Stock Entry")
    se.purpose = "Material Transfer for Manufacture"
    se.work_order = next_wo
    se.job_card = open_job_card  # No job card for inter-process transfer
    se.company = wo.company
    se.fg_completed_qty = transfer_qty
    
    se.append("items", {
        "item_code": fg_item,
        "qty": transfer_qty,
        "stock_uom": wo.stock_uom,
        "uom": wo.stock_uom,  
        "conversion_factor": 1.0, 
        "s_warehouse": wo.fg_warehouse,      
        "t_warehouse": next_wo_doc.wip_warehouse,   
        "basic_rate": 0,
        "job_card_item": job_card_item
    })
    
    se.set_stock_entry_type()
    se.set_missing_values()
    se.submit()

    job_card_item_doc = frappe.get_doc("Job Card Item", job_card_item)
    job_card_item_doc.transferred_qty += transfer_qty
    job_card_item_doc.save(ignore_permissions=True)

    open_jc_doc = frappe.get_doc("Job Card", open_job_card)
    open_jc_doc.transferred_qty = sum(item.transferred_qty for item in open_jc_doc.items)
    open_jc_doc.save(ignore_permissions=True)
    
    frappe.db.commit()
    
    return {
        "status": "Success",
        "transfer_se": se.name,
        "next_work_order": next_wo,
        "job_card": open_job_card,
        "job_card_item": job_card_item,
        "qty_transferred": transfer_qty,
        "from_warehouse": wo.fg_warehouse,
        "to_warehouse": next_wo_doc.wip_warehouse,
        "transferred_qty_updated": job_card_item_doc.transferred_qty,  # ✅ New!
        "header_transferred_qty": open_jc_doc.transferred_qty, 
        "message": f"Transferred {fg_qty} {fg_item} to {next_wo}"
    }
