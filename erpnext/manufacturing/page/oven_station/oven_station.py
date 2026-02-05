import frappe

from erpnext.manufacturing.doctype.slab.api import get_slabs_for


@frappe.whitelist()
def get_slabs_for_heating(line, job_card_number=None):

    if job_card_number:
        # TODO: Get the slab number from the job card if the job card is active and in the current stage
        pass

    # If there is no job card, get the earliest slab for the line.
    slabs = get_slabs_for(line, next_stage="Heating")
    return slabs[0] if slabs else None
