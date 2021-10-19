import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	# Rename table
	frappe.rename_doc("DocType", "Vehicle Invoice Receipt", "Vehicle Invoice", force=1)

	frappe.reload_doc('vehicles', 'doctype', 'vehicle_invoice_movement')
	frappe.reload_doc('vehicles', 'doctype', 'vehicle_invoice_movement_detail')
	frappe.reload_doc('vehicles', 'doctype', 'vehicle_invoice')
	frappe.reload_doc('vehicles', 'doctype', 'vehicle_invoice_delivery')
	frappe.reload_doc('vehicles', 'doctype', 'vehicle')

	# Rename fieldname
	if frappe.db.has_column('Vehicle Invoice Delivery', 'vehicle_invoice_receipt'):
		rename_field('Vehicle Invoice Delivery', 'vehicle_invoice_receipt', 'vehicle_invoice')

	# Set status in Vehicle Invoice
	invoices = frappe.get_all("Vehicle Invoice")
	for d in invoices:
		doc = frappe.get_doc("Vehicle Invoice", d.name)
		doc.set_status(update=True, update_modified=False, update_vehicle=False)
		doc.clear_cache()

	vehicles = frappe.get_all("Vehicle")
	for d in vehicles:
		doc = frappe.get_doc("Vehicle", d.name)
		doc.update_invoice_status(update=True, update_modified=False)
		doc.clear_cache()
