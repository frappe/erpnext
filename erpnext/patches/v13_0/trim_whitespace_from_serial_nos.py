import frappe

from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos


def execute():
	broken_sles = frappe.db.sql(
		"""
			select name, serial_no
			from `tabStock Ledger Entry`
			where
				is_cancelled = 0
				and ( serial_no like %s or serial_no like %s or serial_no like %s or serial_no like %s
					or serial_no = %s )
			""",
		(
			" %",  # leading whitespace
			"% ",  # trailing whitespace
			"%\n %",  # leading whitespace on newline
			"% \n%",  # trailing whitespace on newline
			"\n",  # just new line
		),
		as_dict=True,
	)

	frappe.db.MAX_WRITES_PER_TRANSACTION += len(broken_sles)

	if not broken_sles:
		return

	broken_serial_nos = set()

	# patch SLEs
	for sle in broken_sles:
		serial_no_list = get_serial_nos(sle.serial_no)
		correct_sr_no = "\n".join(serial_no_list)

		if correct_sr_no == sle.serial_no:
			continue

		frappe.db.set_value(
			"Stock Ledger Entry", sle.name, "serial_no", correct_sr_no, update_modified=False
		)
		broken_serial_nos.update(serial_no_list)

	if not broken_serial_nos:
		return

	# Patch serial No documents if they don't have purchase info
	# Purchase info is used for fetching incoming rate
	broken_sr_no_records = frappe.get_list(
		"Serial No",
		filters={
			"status": "Active",
			"name": ("in", broken_serial_nos),
			"purchase_document_type": ("is", "not set"),
		},
		pluck="name",
	)

	frappe.db.MAX_WRITES_PER_TRANSACTION += len(broken_sr_no_records)

	patch_savepoint = "serial_no_patch"
	for serial_no in broken_sr_no_records:
		try:
			frappe.db.savepoint(patch_savepoint)
			sn = frappe.get_doc("Serial No", serial_no)
			sn.update_serial_no_reference()
			sn.db_update()
		except Exception:
			frappe.db.rollback(save_point=patch_savepoint)
