import frappe


def execute():
	frappe.reload_doctype("Payment Entry")
	frappe.db.sql("""update `tabPayment Entry` set status = CASE
		WHEN docstatus = 1 THEN 'Submitted'
		WHEN docstatus = 2 THEN 'Cancelled'
		ELSE 'Draft'
		END;""")
