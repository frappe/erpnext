import frappe

from erpnext.manufacturing.doctype.slab.api import move_slab_to
from erpnext.manufacturing.doctype.slab.slab import Slab


@frappe.whitelist()
def create_preliminary_quality_check(slab_name, slab_template, h_bend, v_bend, d1_bend, d2_bend, depth, remarks):
    move_slab_to(slab_name, "Quarantine")

    doc = frappe.new_doc("Preliminary Quality Check")
    doc.slab = slab_name
    doc.slab_template = slab_template
    doc.h_bend = int(h_bend)
    doc.v_bend = int(v_bend)
    doc.d1_bend = int(d1_bend)
    doc.d2_bend = int(d2_bend)
    doc.depth = depth
    doc.remarks = remarks
    doc.insert(ignore_permissions=True)

    slab: Slab = frappe.get_doc("Slab", slab_name)

    last_history_item = next((h for h in slab.slab_history if h.station == "Quarantine"), None)
    if not last_history_item:
        raise Exception("Slab is not in quarantine.")

    last_history_item.preliminary_qc = doc.name
    slab.save(ignore_permissions=True)

    return doc
