import frappe
from frappe.utils import flt


def execute():
	precision = frappe.get_precision("Job Card Item", "required_qty")
	updates, job_cards = {}, set()
	for row in get_open_job_card_items():
		required_qty = flt(row.required_qty, precision)
		if required_qty != flt(row.required_qty):
			updates[row.name] = {"required_qty": required_qty}
			job_cards.add(row.parent)

	frappe.db.bulk_update("Job Card Item", updates, update_modified=False)
	for job_card in job_cards:
		frappe.get_doc("Job Card", job_card).set_status(update_status=True)


def get_open_job_card_items():
	job_card = frappe.qb.DocType("Job Card")
	job_card_item = frappe.qb.DocType("Job Card Item")

	return (
		frappe.qb.from_(job_card_item)
		.join(job_card)
		.on(job_card_item.parent == job_card.name)
		.select(job_card_item.name, job_card_item.parent, job_card_item.required_qty)
		.where((job_card.docstatus == 0) & (job_card_item.parenttype == "Job Card"))
	).run(as_dict=True)
