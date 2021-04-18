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