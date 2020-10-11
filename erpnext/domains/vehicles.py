from __future__ import unicode_literals

applies_to_fields = [
	{"label": "Applies to Vehicle", "fieldname": "applies_to_vehicle", "fieldtype": "Link", "options": "Vehicle",
		"insert_after": "sec_applies_to"},
	{"label": "License Plate", "fieldname": "vehicle_license_plate", "fieldtype": "Data", "no_copy": 1,
		"insert_after": "col_break_applies_to", "read_only": 1, "fetch_from": "applies_to_vehicle.license_plate"},
	{"label": "", "fieldname": "col_break_vehicle_1", "fieldtype": "Column Break",
		"insert_after": "vehicle_license_plate"},
	{"label": "Chassis No", "fieldname": "vehicle_chassis_no", "fieldtype": "Data", "no_copy": 1,
		"insert_after": "col_break_vehicle_1", "read_only": 1, "fetch_from": "applies_to_vehicle.chassis_no"},
	{"label": "Engine No", "fieldname": "vehicle_engine_no", "fieldtype": "Data", "no_copy": 1,
		"insert_after": "vehicle_chassis_no", "read_only": 1, "fetch_from": "applies_to_vehicle.engine_no"},
	{"label": "", "fieldname": "col_break_vehicle_2", "fieldtype": "Column Break",
		"insert_after": "vehicle_engine_no"},
	{"label": "Odometer Value (Last)", "fieldname": "vehicle_last_odometer", "fieldtype": "Int", "no_copy": 1,
		"insert_after": "col_break_vehicle_2", "read_only": 1, "fetch_from": "applies_to_vehicle.last_odometer"},
	{"label": "Color", "fieldname": "vehicle_color", "fieldtype": "Data", "no_copy": 1,
		"insert_after": "vehicle_last_odometer", "read_only": 1, "fetch_from": "applies_to_vehicle.color"},
]

for d in applies_to_fields:
	d['translatable'] = 0

data = {
	'desktop_icons': [
		'Vehicle',
	],
	'set_value': [

	],
	'restricted_roles': [

	],
	'modules': [

	],
	'properties': [
		{"doctype": "Item", "fieldname": "is_vehicle", "property": "in_standard_filter", "value": 1},
		{"doctype": "Delivery Note Item", "fieldname": "vehicle", "property": "in_standard_filter", "value": 1},
		{"doctype": "Sales Invoice Item", "fieldname": "vehicle", "property": "in_standard_filter", "value": 1},
		{"doctype": "Purchase Receipt Item", "fieldname": "vehicle", "property": "in_standard_filter", "value": 1},
		{"doctype": "Purchase Invoice Item", "fieldname": "vehicle", "property": "in_standard_filter", "value": 1},
		{"doctype": "Stock Entry Detail", "fieldname": "vehicle", "property": "in_standard_filter", "value": 1},

		{"doctype": "Sales Invoice", "fieldname": "sec_applies_to", "property": "hidden", "value": 0},
		{"doctype": "Delivery Note", "fieldname": "sec_applies_to", "property": "hidden", "value": 0},
		{"doctype": "Sales Order", "fieldname": "sec_applies_to", "property": "hidden", "value": 0},
		{"doctype": "Quotation", "fieldname": "sec_applies_to", "property": "hidden", "value": 0},

		{"doctype": "Sales Invoice", "fieldname": "applies_to_item", "property": "fetch_from", "value": "applies_to_vehicle.item_code"},
		{"doctype": "Delivery Note", "fieldname": "applies_to_item", "property": "fetch_from", "value": "applies_to_vehicle.item_code"},
		{"doctype": "Sales Order", "fieldname": "applies_to_item", "property": "fetch_from", "value": "applies_to_vehicle.item_code"},
		{"doctype": "Quotation", "fieldname": "applies_to_item", "property": "fetch_from", "value": "applies_to_vehicle.item_code"},
	],
	'custom_fields': {
		"Sales Invoice": applies_to_fields,
		"Delivery Note": applies_to_fields,
		"Sales Order": applies_to_fields,
		"Quotation": applies_to_fields,
	},
	'default_portal_role': 'Customer'
}
