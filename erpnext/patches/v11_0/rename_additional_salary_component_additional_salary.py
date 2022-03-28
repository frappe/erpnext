import frappe

# this patch should have been included with this PR https://github.com/frappe/erpnext/pull/14302


def execute():
	if frappe.db.table_exists("Additional Salary Component"):
		if not frappe.db.table_exists("Additional Salary"):
			frappe.rename_doc("DocType", "Additional Salary Component", "Additional Salary")

		frappe.delete_doc("DocType", "Additional Salary Component")
