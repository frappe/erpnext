import frappe


def execute():
	if (
		frappe.db.sql(
			"""select data_type FROM information_schema.columns
            where column_name = 'name' and table_name = 'tabTax Withheld Vouchers'"""
		)[0][0]
		== "bigint"
	):
		frappe.db.change_column_type("Tax Withheld Vouchers", "name", "varchar(140)")
