import frappe
from frappe import _
from frappe.utils import flt

@frappe.whitelist()
def get_mixer_ingredients(job_card):
    jc = frappe.get_doc("Job Card", job_card)
    if not jc.bom_no:
        frappe.throw(_("No BOM set on Job Card {0}").format(job_card))

    bom_doc = frappe.get_doc("BOM", jc.bom_no)

    ingredients = []
    for row in bom_doc.items:
        qty = flt(row.stock_qty) 
        ingredients.append({
            "item_code": row.item_code,
            "item_name": row.item_name,
            "stock_uom": row.stock_uom,
            "stock_uom_qty": qty,
        })

    return ingredients


@frappe.whitelist()
def confirm_materials(job_card, ingredients):
    """Create Stock Entry from mixer quantities and mark Job Card ready."""
    import json
    ingredients = json.loads(ingredients)

    jc = frappe.get_doc("Job Card", job_card)
    se = frappe.new_doc("Stock Entry")
    se.stock_entry_type = "Material Issue"
    se.job_card = jc.name
    se.company = jc.company
    # optional: set from_warehouse, posting_date, etc.

    for ing in ingredients:
        se.append("items", {
            "item_code": ing["item_code"],
            "qty": flt(ing["qty"]),
            "uom": ing["unit"],
            "stock_uom": ing["unit"],
            "conversion_factor": 1,
        })

    se.insert()
    se.submit()

    # 2) Mark Job Card that materials are confirmed (custom field)
    jc.db_set("materials_confirmed", 1)

    return {"stock_entry": se.name}

@frappe.whitelist()
def get_batch_info(batch_no):
    """Get batch context (colour, phase, etc.)"""
    wo = frappe.db.exists("Work Order", batch_no)
    if wo:
        wo_doc = frappe.get_doc("Work Order", batch_no)
        return {
            "colour": wo_doc.get("custom_colour") or wo_doc.get("item_name") or "Standard",
            "phase": "Preparation Phase",
            "planned_qty": wo_doc.qty,
            "produced_qty": wo_doc.produced_qty
        }
    return {"colour": "Standard", "phase": "Preparation Phase"}
