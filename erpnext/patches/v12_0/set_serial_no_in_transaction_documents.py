import frappe

def execute():
	if "Vehicles" not in frappe.get_active_domains():
		return

	doctype_list = ['Quotation', 'Sales Order', 'Delivery Note', 'Purchase Receipt', 'Material Request',
		'Sales Invoice', 'Purchase Invoice', 'Purchase Order', 'Project', 'Appointment']

	for doctype in doctype_list:
		frappe.reload_doctype(doctype)

		frappe.db.sql("Update `tab{0}` SET applies_to_serial_no = applies_to_vehicle".format(doctype))
