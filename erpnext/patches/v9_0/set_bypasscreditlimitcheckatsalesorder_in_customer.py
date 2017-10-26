import frappe

def execute():
	frappe.reload_doctype("Customer")
	
	if "bypass_credit_limit_check_at_sales_order" in frappe.db.get_table_columns("Customer"):
		frappe.db.sql("""
			update `tabCustomer`
			set bypass_credit_limit_check_at_sales_order = 0
			where (bypass_credit_limit_check_at_sales_order is NULL)""")