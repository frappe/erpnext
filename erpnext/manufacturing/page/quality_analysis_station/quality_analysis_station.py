import frappe

from erpnext.manufacturing.doctype.slab.api import checkout_slab, get_slabs_for
from erpnext.manufacturing.doctype.slab_quality_report.api import create_slab_quality_report


@frappe.whitelist()
def start_qa_process(slab_number: str):
    # TODO:
	#	1. Get the job card for quality analysis on the given line.
	#	2. Start the job card.
	#	3. Move the slab to quality check.
	#	4. Return the job card number.
    pass


@frappe.whitelist()
def submit_qa_report(report: str | dict, shift: str, job_card: str, slab_number: str):
    # 1. Create the slab quality report.
    create_slab_quality_report(report, shift, job_card)

    # 2. TODO: Finish the job card.

    # 3. Checkout the slab from QA Station.
    checkout_slab(slab_number)
    pass


@frappe.whitelist()
def get_slab_or_jobcard_for_qa(line: str, job_card_number: str):
    if job_card_number:
        # TODO: If the job card number is provided, return its associated slab if the job card is active and on the current line.
        pass

    # TODO: Else, get the earliest open job card for the operation.

    # If there are no active job cards, get the earliest finished slab
    slabs = get_slabs_for(line, next_stage="Quality Check")

    qa_slab = slabs[0] if slabs else None
    return qa_slab
