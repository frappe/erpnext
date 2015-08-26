import frappe

def execute():
	# frappe.reload_doctype("Quotation")
	# frappe.db.sql("""update tabQuotation set title = customer_name""")
	#
	# frappe.reload_doctype("Sales Order")
	# frappe.db.sql("""update `tabSales Order` set title = customer_name""")

	frappe.reload_doctype("Delivery Note")
	frappe.db.sql("""update `tabDelivery Note` set title = customer_name""")
