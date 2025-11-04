import frappe


def execute():
	# Update the reference_name, reference_doctype fields for Serial No where it is null

	if not frappe.db.has_column("Serial and Batch Bundle", "posting_date"):
		return

	sabb = frappe.qb.DocType("Serial and Batch Bundle")
	sabb_entry = frappe.qb.DocType("Serial and Batch Entry")
	serial_no = frappe.qb.DocType("Serial No").as_("sn")

	query = (
		frappe.qb.update(serial_no)
		.join(sabb_entry)
		.on(sabb_entry.serial_no == serial_no.name)
		.join(sabb)
		.on(sabb.name == sabb_entry.parent)
		.set(serial_no.reference_name, serial_no.purchase_document_no)
		.set(serial_no.reference_doctype, sabb.voucher_type)
		.set(serial_no.posting_date, sabb.posting_date)
		.where(
			(sabb.voucher_no == serial_no.purchase_document_no)
			& (sabb.is_cancelled == 0)
			& (sabb_entry.docstatus == 1)
		)
	)

	query.run()
