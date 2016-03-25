import frappe

def execute():
	frappe.reload_doctype("Quotation")
	frappe.db.sql("""update tabQuotation set title = customer_name""")

	frappe.reload_doctype("Sales Order")
	frappe.db.sql("""update `tabSales Order` set title = customer_name""")

	frappe.reload_doctype("Delivery Note")
	frappe.db.sql("""update `tabDelivery Note` set title = customer_name""")

	frappe.reload_doctype("Material Request")
	frappe.db.sql("""update `tabMaterial Request` set title = material_request_type""")

	frappe.reload_doctype("Supplier Quotation")
	frappe.db.sql("""update `tabSupplier Quotation` set title = supplier_name""")

	frappe.reload_doctype("Purchase Order")
	frappe.db.sql("""update `tabPurchase Order` set title = supplier_name""")

	frappe.reload_doctype("Purchase Receipt")
	frappe.db.sql("""update `tabPurchase Receipt` set title = supplier_name""")

	frappe.reload_doctype("Purchase Invoice")
	frappe.db.sql("""update `tabPurchase Invoice` set title = supplier_name""")

	frappe.reload_doctype("Stock Entry")
	frappe.db.sql("""update `tabStock Entry` set title = purpose""")

	frappe.reload_doctype("Sales Invoice")
	frappe.db.sql("""update `tabSales Invoice` set title = customer_name""")

	frappe.reload_doctype("Expense Claim")
	frappe.db.sql("""update `tabExpense Claim` set title = employee_name""")
