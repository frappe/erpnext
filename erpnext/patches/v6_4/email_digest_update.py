import frappe

def execute():
	frappe.reload_doctype("Email Digest")
	frappe.db.sql("""update `tabEmail Digest` set expense_year_to_date =
		income_year_to_date""")
