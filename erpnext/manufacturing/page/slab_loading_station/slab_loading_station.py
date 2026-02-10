import frappe

from erpnext.manufacturing.doctype.job_card.job_card import JobCard
from erpnext.manufacturing.doctype.operation.api import transfer_to_next_process
from erpnext.manufacturing.doctype.slab.api import checkout_slab
from erpnext.manufacturing.doctype.slab.slab import Slab


@frappe.whitelist()
def unload_slab_to_trimming(slab_number: str):

	try:
		slab: Slab = frappe.get_doc("Slab", slab_number)

		last_job_card: JobCard = frappe.get_doc("Job Card", slab.current_job_card)

		work_order = frappe.get_doc("Work Order", last_job_card.work_order)

		frappe.db.begin()

		checkout_slab(slab_number)
		transfer_to_next_process(
			work_order.name,
			last_job_card.total_completed_qty,
			last_job_card.operation,
			last_job_card.mixer_number,
		)

		frappe.db.commit()

	except Exception:
		frappe.db.rollback()
