import frappe

from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos


def execute():
	broken_sles = frappe.db.sql("""
			select name, serial_no
			from `tabStock Ledger Entry`
			where
				is_cancelled = 0
				and (serial_no like %s or serial_no like %s or serial_no like %s or serial_no like %s)
			""",
			(
				" %",    # leading whitespace
				"% ",    # trailing whitespace
				"%\n %", # leading whitespace on newline
				"% \n%", # trailing whitespace on newline
			),
			as_dict=True,
		)

	frappe.db.MAX_WRITES_PER_TRANSACTION += len(broken_sles)

	if not broken_sles:
		return

	broken_serial_nos = set()

	for sle in broken_sles:
		serial_no_list = get_serial_nos(sle.serial_no)
		correct_sr_no = "\n".join(serial_no_list)

		if correct_sr_no == sle.serial_no:
			continue

		frappe.db.set_value("Stock Ledger Entry", sle.name, "serial_no", correct_sr_no, update_modified=False)
		broken_serial_nos.update(serial_no_list)

	if not broken_serial_nos:
		return

	broken_sr_no_records = [sr[0] for sr in frappe.db.sql("""
							select name
							from `tabSerial No`
							where status='Active'
								and coalesce(purchase_document_type, '') = ''
								and name in %s """, (list(broken_serial_nos),)
							)]

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
