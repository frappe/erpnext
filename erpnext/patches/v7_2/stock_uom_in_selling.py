import frappe

def execute():
	frappe.reload_doctype('Sales Order')
	frappe.reload_doctype('Sales Invoice')
	frappe.reload_doctype('Quotation')
	frappe.reload_doctype('Delivery Note')

	doctype_list = ['Sales Order Item', 'Delivery Note Item', 'Quotation Item', 'Sales Invoice Item']

	for doctype in doctype_list:
		frappe.reload_doctype(doctype)
		frappe.db.sql("""update `tab{doctype}` 
		 		set uom = stock_uom, conversion_factor = 1, stock_qty = qty""".format(doctype=doctype))