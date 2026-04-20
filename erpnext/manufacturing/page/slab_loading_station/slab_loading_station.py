import frappe

from erpnext.manufacturing.doctype.job_card.job_card import JobCard
from erpnext.manufacturing.doctype.operation.api import transfer_to_next_process
from erpnext.manufacturing.doctype.slab.api import checkout_slab
from erpnext.manufacturing.doctype.slab.slab import Slab


@frappe.whitelist()
def unload_slab_to_trimming(slab_number: str):
	try:
		frappe.db.begin()
		finish_curing(slab_number)
		frappe.db.commit()

	except Exception:
		frappe.db.rollback()


def finish_curing(slab_number: str):
	slab: Slab = frappe.get_doc("Slab", slab_number) # pyright: ignore[reportAssignmentType]
	last_job_card: JobCard = frappe.get_doc("Job Card", str(slab.last_active_job_card)) # pyright: ignore[reportAssignmentType]
	work_order = frappe.get_doc("Work Order", last_job_card.work_order)

	checkout_slab(slab_number)
	transfer_to_next_process(
		last_job_card.name,
		work_order.name,
		last_job_card.total_completed_qty,
		last_job_card.operation,
		last_job_card.mixer_number,
	)
