from __future__ import unicode_literals

applies_to_fields = [
	{"label": "Applies to Vehicle", "fieldname": "applies_to_vehicle", "fieldtype": "Link", "options": "Vehicle",
		"insert_after": "sec_applies_to", "in_standard_filter": 1},
	{"label": "License Plate", "fieldname": "vehicle_license_plate", "fieldtype": "Data", "no_copy": 0,
		"insert_after": "col_break_applies_to", "read_only": 0, "fetch_from": "applies_to_vehicle.license_plate"},
	{"label": "", "fieldname": "col_break_vehicle_1", "fieldtype": "Column Break",
		"insert_after": "applies_to_item_name"},
	{"label": "Chassis No", "fieldname": "vehicle_chassis_no", "fieldtype": "Data", "no_copy": 0,
		"insert_after": "col_break_vehicle_1", "read_only": 0, "fetch_from": "applies_to_vehicle.chassis_no"},
	{"label": "Engine No", "fieldname": "vehicle_engine_no", "fieldtype": "Data", "no_copy": 0,
		"insert_after": "vehicle_chassis_no", "read_only": 0, "fetch_from": "applies_to_vehicle.engine_no"},
	{"label": "", "fieldname": "col_break_vehicle_2", "fieldtype": "Column Break",
		"insert_after": "vehicle_engine_no"},
	{"label": "Odometer Reading", "fieldname": "vehicle_last_odometer", "fieldtype": "Int", "no_copy": 0,
		"insert_after": "col_break_vehicle_2", "read_only": 0, "fetch_from": "applies_to_vehicle.last_odometer"},
	{"label": "Color", "fieldname": "vehicle_color", "fieldtype": "Data", "no_copy": 0,
		"insert_after": "vehicle_last_odometer", "read_only": 0, "fetch_from": "applies_to_vehicle.color"},
]

service_person_fields = [
	{"label": "Service Advisor", "fieldname": "service_advisor", "fieldtype": "Link", "options": "Employee",
		"insert_after": "more_info_cb_2", "in_standard_filter": 1},
	{"label": "Service Manager", "fieldname": "service_manager", "fieldtype": "Link", "options": "Employee",
		"insert_after": "service_advisor", "in_standard_filter": 1},
]

for d in applies_to_fields:
	d['translatable'] = 0

common_properties = [
	[('Delivery Note Item', 'Sales Invoice Item', 'Purchase Receipt Item', 'Purchase Invoice Item', 'Stock Entry Detail'),
		{"fieldname": "vehicle", "property": "in_standard_filter", "value": 1}],

	[('Quotation', 'Sales Order', 'Delivery Note', 'Sales Invoice'),
		{"fieldname": "sec_applies_to", "property": "hidden", "value": 0}],

	[('Quotation', 'Sales Order', 'Delivery Note', 'Sales Invoice'),
		{"fieldname": "applies_to_item", "property": "fetch_from", "value": "applies_to_vehicle.item_code"}],

	[('Quotation', 'Sales Order', 'Delivery Note', 'Sales Invoice'),
		{"fieldname": "sec_applies_to", "property": "label", "value": "Vehicle Details"}],

	[('Sales Invoice',),
		{"fieldname": "sec_insurance", "property": "hidden", "value": 0}],
]

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
		{"doctype": "Customer", "fieldname": "is_insurance_company", "property": "in_standard_filter", "value": 1},
		{"doctype": "Sales Invoice", "fieldname": "bill_to", "property": "hidden", "value": 0},
		{"doctype": "Delivery Note", "fieldname": "received_by_type", "property": "default", "value": "Employee"}
	],
	'custom_fields': {
		"Sales Invoice": applies_to_fields + service_person_fields,
		"Delivery Note": applies_to_fields + service_person_fields,
		"Sales Order": applies_to_fields + service_person_fields,
		"Quotation": applies_to_fields + service_person_fields,
	},
	'default_portal_role': 'Customer'
}

for dts, prop_template in common_properties:
	for doctype in dts:
		prop = prop_template.copy()
		prop['doctype'] = doctype
		data['properties'].append(prop)
