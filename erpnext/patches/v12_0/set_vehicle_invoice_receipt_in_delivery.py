import frappe

def execute():
	frappe.reload_doc('vehicles', 'doctype', 'vehicle_invoice_delivery')

	for d in frappe.get_all("Vehicle Invoice Delivery", fields=['name', 'vehicle']):
		if d.vehicle:
			vehicle_invoice_receipt = frappe.db.get_value("Vehicle Invoice Receipt",
				filters={"vehicle": d.vehicle, "docstatus": 1})

			frappe.db.set_value("Vehicle Invoice Delivery", d.name, 'vehicle_invoice_receipt', vehicle_invoice_receipt,
				update_modified=False)
