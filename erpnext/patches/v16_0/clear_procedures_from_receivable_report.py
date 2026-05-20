import frappe


def execute():
	frappe.db.sql("drop function if exists ar_genkey")
	frappe.db.sql("drop procedure if exists ar_init_tmp_table")
	frappe.db.sql("drop procedure if exists ar_allocate_to_tmp_table")

	if frappe.db.get_single_value("Accounts Settings", "receivable_payable_fetch_method") == "Raw SQL":
		frappe.db.set_single_value(
			"Accounts Settings", "receivable_payable_fetch_method", "UnBuffered Cursor"
		)
