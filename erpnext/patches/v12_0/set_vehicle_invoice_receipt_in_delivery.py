import frappe

def execute():
	frappe.reload_doc('vehicles', 'doctype', 'vehicle_invoice_delivery')

	for d in frappe.get_all("Vehicle Invoice Delivery", fields=['name', 'vehicle']):
		if d.vehicle:
			vehicle_invoice = frappe.db.get_value("Vehicle Invoice",
				filters={"vehicle": d.vehicle, "docstatus": 1})

			frappe.db.set_value("Vehicle Invoice Delivery", d.name, 'vehicle_invoice', vehicle_invoice,
				update_modified=False)
