from typing import cast

import frappe

from erpnext.manufacturing.doctype.job_card.job_card import JobCard
from erpnext.manufacturing.doctype.operation.api import get_open_job_cards
from erpnext.manufacturing.doctype.slab.api import get_slabs_for
from erpnext.manufacturing.doctype.slab.slab import Slab
from erpnext.manufacturing.page.operator_station.operator_station import (
    get_top_job_card_for_process,
    start_process,
)


@frappe.whitelist()
def get_cooling_data(line):
    # 1. Get Incoming Slabs (Ready for Cooling)
    incoming_slabs = get_slabs_for(line, "Cooling", limit=50)

    # 2. Get Cooling Queue (Active Job Cards)
    # Fetch WIP job cards for "Cooling" process.
    # We exclude "Material Transferred" as those are done but waiting for next move.
    cooling_queue = get_open_job_cards(
        process="Cooling",
        line=line,
        include_wip=True,
        include_material_transferred=False # Explicitly exclude
    )

    return {
        "incoming_slabs": incoming_slabs,
        "cooling_queue": cooling_queue
    }


@frappe.whitelist()
def start_cooling_process(slab_number: str):
    slab = cast(Slab, frappe.get_doc("Slab", slab_number))
    #    1. Get the job card for cooling on the given line.
    job_card = get_top_job_card_for_process("Cooling", slab.line, False)

    if not job_card:
        frappe.throw("No Job Card found for the Cooling process.")

    job_card = cast(JobCard, job_card)

    #    2. Start the job card.
    #    3. Move the slab to cooling.
    start_process(job_card.name, slab_name=slab.name or "", slab_template=slab.template, process_name="Cooling")

    #    4. Return the job card number.
    return job_card.name
