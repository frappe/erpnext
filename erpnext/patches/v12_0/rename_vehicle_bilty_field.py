import frappe
from frappe.model.utils.rename_field import rename_field

def execute():
	frappe.reload_doc('vehicles', 'doctype', 'vehicle_receipt')
	frappe.reload_doc('vehicles', 'doctype', 'vehicle_booking_order')

	if frappe.db.has_column('Vehicle Receipt', 'supplier_delivery_note'):
		rename_field('Vehicle Receipt', 'supplier_delivery_note', 'lr_no')
	if frappe.db.has_column('Vehicle Booking Order', 'supplier_delivery_note'):
		rename_field('Vehicle Booking Order', 'supplier_delivery_note', 'lr_no')
