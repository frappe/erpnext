import frappe

def execute():
	frappe.reload_doctype('Supplier Quotation Item')
	for data in frappe.db.sql(""" select prevdoc_docname, prevdoc_detail_docname, name
		from `tabSupplier Quotation Item` where prevdoc_docname is not null""", as_dict=True):
		frappe.db.set_value("Supplier Quotation Item", data.name, "material_request", data.prevdoc_docname)
		frappe.db.set_value("Supplier Quotation Item", data.name, "material_request_item", data.prevdoc_detail_docname)