import frappe

vehicle_copy_fields = [
	'applies_to_item_name',
	'vehicle_chassis_no',
	'vehicle_engine_no',
	'vehicle_license_plate',
]


def remove_vehicle_details_if_empty(doc):
	if not doc.get('applies_to_vehicle'):
		for f in vehicle_copy_fields:
			if doc.meta.has_field(f):
				doc.set(f, None)


def update_vehicle_registration_order_payment(vehicle_registration_order):
	vro = frappe.get_doc("Vehicle Registration Order", vehicle_registration_order)
	vro.update_payment_status(update=True)
	vro.set_status(update=True)
	vro.notify_update()
