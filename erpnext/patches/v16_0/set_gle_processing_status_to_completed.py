import frappe


def execute():
	PCV = frappe.qb.DocType("Period Closing Voucher")

	frappe.qb.update(PCV).set(PCV.gle_processing_status, "Completed").where(
		(PCV.docstatus == 1) & ((PCV.gle_processing_status.isnull()) | (PCV.gle_processing_status == ""))
	).run()
