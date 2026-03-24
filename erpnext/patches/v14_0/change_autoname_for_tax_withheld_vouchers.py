import frappe


def execute():
	if frappe.db.get_column_type("Tax Withheld Vouchers", "name") == "bigint":
		frappe.db.change_column_type("Tax Withheld Vouchers", "name", "varchar(140)")
