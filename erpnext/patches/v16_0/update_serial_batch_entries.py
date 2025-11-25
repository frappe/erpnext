import frappe


def execute():
	if frappe.db.has_table("Serial and Batch Entry"):
		frappe.db.sql(
			"""
				UPDATE `tabSerial and Batch Entry` SABE, `tabSerial and Batch Bundle` SABB
				SET
					SABE.posting_datetime = SABB.posting_datetime,
					SABE.voucher_type = SABB.voucher_type,
					SABE.voucher_no = SABB.voucher_no,
					SABE.voucher_detail_no = SABB.voucher_detail_no,
					SABE.type_of_transaction = SABB.type_of_transaction
				WHERE SABE.parent = SABB.name
			"""
		)
