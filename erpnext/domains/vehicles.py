from __future__ import unicode_literals
from copy import deepcopy

applies_to_fields = [
	{"label": "Applies to Vehicle", "fieldname": "applies_to_vehicle", "fieldtype": "Link", "options": "Vehicle",
		"insert_after": "sec_applies_to", "in_standard_filter": 1},
	{"label": "Vehicle Owner", "fieldname": "vehicle_owner", "fieldtype": "Link", "options": "Customer",
		"insert_after": "applies_to_item", "in_standard_filter": 1, "fetch_from": "applies_to_vehicle.vehicle_owner"},
	{"label": "License Plate", "fieldname": "vehicle_license_plate", "fieldtype": "Data", "depends_on": "eval:!doc.vehicle_unregistered",
		"insert_after": "col_break_applies_to", "fetch_from": "applies_to_vehicle.license_plate"},
	{"label": "Is Unregistered", "fieldname": "vehicle_unregistered", "fieldtype": "Check", "depends_on": "eval:!doc.vehicle_license_plate || doc.vehicle_unregistered",
		"insert_after": "vehicle_license_plate", "fetch_from": "applies_to_vehicle.unregistered"},
	{"label": "Vehicle Owner Name", "fieldname": "vehicle_owner_name", "fieldtype": "Data",
		"insert_after": "applies_to_item_name", "fetch_from": "vehicle_owner.customer_name", "read_only": 1,
		"depends_on": "eval:doc.vehicle_owner && doc.vehicle_owner_name != doc.vehicle_owner"},
	{"label": "", "fieldname": "col_break_vehicle_1", "fieldtype": "Column Break",
		"insert_after": "vehicle_owner_name"},
	{"label": "Chassis No", "fieldname": "vehicle_chassis_no", "fieldtype": "Data",
		"insert_after": "col_break_vehicle_1", "fetch_from": "applies_to_vehicle.chassis_no"},
	{"label": "Engine No", "fieldname": "vehicle_engine_no", "fieldtype": "Data",
		"insert_after": "vehicle_chassis_no", "fetch_from": "applies_to_vehicle.engine_no"},
	{"label": "", "fieldname": "col_break_vehicle_2", "fieldtype": "Column Break",
		"insert_after": "vehicle_engine_no"},
	{"label": "Odometer Reading", "fieldname": "vehicle_last_odometer", "fieldtype": "Int",
		"insert_after": "col_break_vehicle_2", "fetch_from": "applies_to_vehicle.last_odometer"},
	{"label": "Vehicle Color", "fieldname": "vehicle_color", "fieldtype": "Link", "options": "Vehicle Color",
		"insert_after": "vehicle_last_odometer", "fetch_from": "applies_to_vehicle.color"},
]

applies_to_project_fields = deepcopy(applies_to_fields)

project_first_odometer = {"label": "Odometer Reading (First)", "fieldname": "vehicle_first_odometer", "fieldtype": "Int",
	"insert_after": "col_break_vehicle_2"}
applies_to_project_fields.append(project_first_odometer)

project_last_odometer = [f for f in applies_to_project_fields if f['fieldname'] == 'vehicle_last_odometer'][0]
project_last_odometer.update({"label": "Odometer Reading (Last)", "fetch_from": "",
	"insert_after": "vehicle_first_odometer"})

service_person_fields = [
	{"label": "Service Advisor", "fieldname": "service_advisor", "fieldtype": "Link", "options": "Employee",
		"insert_after": "more_info_cb_2", "in_standard_filter": 1, "ignore_user_permissions": 1},
	{"label": "Service Manager", "fieldname": "service_manager", "fieldtype": "Link", "options": "Employee",
		"insert_after": "service_advisor", "in_standard_filter": 1, "ignore_user_permissions": 1},
]

accounting_dimension_fields = [
	{"label": "", "fieldname": "vehicle_accounting_dimensions_cb_1", "fieldtype": "Column Break",
		"insert_after": "project"},
	{"label": "Vehicle Booking Order", "fieldname": "vehicle_booking_order", "fieldtype": "Link", "options": "Vehicle Booking Order",
		"insert_after": "vehicle_accounting_dimensions_cb_1", "in_standard_filter": 1, "ignore_user_permissions": 1},
	{"label": "", "fieldname": "vehicle_accounting_dimensions_cb_2", "fieldtype": "Column Break",
		"insert_after": "vehicle_booking_order"},
	{"label": "Applies to Vehicle", "fieldname": "applies_to_vehicle", "fieldtype": "Link", "options": "Vehicle",
		"insert_after": "vehicle_accounting_dimensions_cb_2", "in_standard_filter": 1, "ignore_user_permissions": 1,
		"fetch_from": "", "fetch_if_empty": 0},

	{"label": "Vehicle Item Name", "fieldname": "applies_to_item_name", "fieldtype": "Data",
		"insert_after": "cost_center", "read_only": 1, "fetch_from": "applies_to_vehicle.item_name"},
	{"label": "Chassis No", "fieldname": "vehicle_chassis_no", "fieldtype": "Data",
		"insert_after": "project", "read_only": 1, "fetch_from": "applies_to_vehicle.chassis_no"},
	{"label": "Engine No", "fieldname": "vehicle_engine_no", "fieldtype": "Data",
		"insert_after": "vehicle_booking_order", "read_only": 1, "fetch_from": "applies_to_vehicle.engine_no"},
	{"label": "License Plate", "fieldname": "vehicle_license_plate", "fieldtype": "Data", "depends_on": "eval:!doc.vehicle_unregistered",
		"insert_after": "applies_to_vehicle", "read_only": 1, "fetch_from": "applies_to_vehicle.license_plate"},
]

for d in applies_to_fields:
	d['translatable'] = 0
for d in applies_to_project_fields:
	d['translatable'] = 0
for d in service_person_fields:
	d['translatable'] = 0
for d in accounting_dimension_fields:
	d['translatable'] = 0

common_properties = [
	[('Delivery Note Item', 'Sales Invoice Item', 'Purchase Receipt Item', 'Purchase Invoice Item', 'Stock Entry Detail'),
		{"fieldname": "vehicle", "property": "in_standard_filter", "value": 1}],

	[('Quotation', 'Sales Order', 'Delivery Note', 'Sales Invoice', 'Purchase Order', 'Purchase Receipt', 'Purchase Invoice', 'Project'),
		{"fieldname": "sec_applies_to", "property": "hidden", "value": 0}],

	[('Quotation', 'Sales Order', 'Delivery Note', 'Sales Invoice', 'Purchase Order', 'Purchase Receipt', 'Purchase Invoice', 'Project'),
		{"fieldname": "applies_to_item", "property": "fetch_from", "value": "applies_to_vehicle.item_code"}],

	[('Quotation', 'Sales Order', 'Delivery Note', 'Sales Invoice', 'Purchase Order', 'Purchase Receipt', 'Purchase Invoice', 'Project'),
		{"fieldname": "sec_applies_to", "property": "label", "value": "Vehicle Details"}],

	[('Quotation', 'Sales Order', 'Delivery Note', 'Sales Invoice', 'Project'),
		{"fieldname": "customer", "property": "label", "value": "Customer (User)"}],
	[('Quotation', 'Sales Order', 'Delivery Note', 'Sales Invoice', 'Project'),
		{"fieldname": "customer_name", "property": "label", "value": "Customer Name (User)"}],

	[('Sales Invoice', 'Quotation', 'Project'),
		{"fieldname": "sec_insurance", "property": "hidden", "value": 0}],

	[('Item', 'Item Group', 'Brand', 'Item Source'),
		{"fieldname": "is_vehicle", "property": "hidden", "value": 0}],
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
		{"doctype": "Project", "fieldname": "bill_to", "property": "hidden", "value": 0},
		{"doctype": "Delivery Note", "fieldname": "received_by_type", "property": "default", "value": "Employee"},
		{"doctype": "Payment Terms Template", "fieldname": "include_in_vehicle_booking", "property": "hidden", "value": 0},
		{"doctype": "Transaction Type", "fieldname": "vehicle_booking_defaults_section", "property": "hidden", "value": 0},
	],
	'custom_fields': {
		"Sales Invoice": applies_to_fields + service_person_fields,
		"Delivery Note": applies_to_fields + service_person_fields,
		"Sales Order": applies_to_fields + service_person_fields,
		"Quotation": applies_to_fields + service_person_fields,
		"Purchase Order": applies_to_fields,
		"Purchase Receipt": applies_to_fields,
		"Purchase Invoice": applies_to_fields,
		"Project": applies_to_project_fields + service_person_fields,
		"Journal Entry": accounting_dimension_fields,
		"Journal Entry Account": accounting_dimension_fields,
		"Payment Entry": accounting_dimension_fields,
	},
	'default_portal_role': 'Customer'
}

for dts, prop_template in common_properties:
	for doctype in dts:
		prop = prop_template.copy()
		prop['doctype'] = doctype
		data['properties'].append(prop)
