import frappe

from erpnext.manufacturing.doctype.slab.api import move_slab_to


@frappe.whitelist()
def create_preliminary_quality_check(slab_name, slab_template, h_bend, v_bend, d1_bend, d2_bend, depth, remarks):
    doc = frappe.new_doc("Preliminary Quality Check")
    doc.slab = slab_name
    doc.slab_template = slab_template
    doc.h_bend = int(h_bend)
    doc.v_bend = int(v_bend)
    doc.d1_bend = int(d1_bend)
    doc.d2_bend = int(d2_bend)
    doc.depth = depth
    doc.remarks = remarks
    doc.insert()

    move_slab_to(slab_name, "Quarantine")

    return doc
