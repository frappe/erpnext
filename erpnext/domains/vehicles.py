from __future__ import unicode_literals
from copy import deepcopy


def insert_field_after(after_fieldname, new_field, field_list):
	new_field['insert_after'] = after_fieldname

	after_field_index = -1
	next_field = None
	for i, f in enumerate(field_list):
		if f.get('fieldname') == after_fieldname:
			after_field_index = i
		if f.get('insert_after') == after_fieldname:
			next_field = f

	if after_field_index != -1:
		field_list.insert(after_field_index + 1, new_field)
	if next_field:
		next_field['insert_after'] = new_field['fieldname']


def get_field(fieldname, field_list):
	for f in field_list:
		if f.get('fieldname') == fieldname:
			return f

	return None


# Vehicle Details
applies_to_fields = [
	{"label": "Applies to Model", "fieldname": "applies_to_variant_of", "fieldtype": "Link", "options": "Item",
		"insert_after": "sec_applies_to", "in_standard_filter": 1, "hidden": 1, "read_only": 1, "fetch_from": "applies_to_item.variant_of"},
	{"label": "Applies to Model Name", "fieldname": "applies_to_variant_of_name", "fieldtype": "Data",
		"insert_after": "applies_to_variant_of", "hidden": 1, "read_only": 1, "fetch_from": "applies_to_variant_of.item_name"},

	{"label": "Applies to Vehicle", "fieldname": "applies_to_vehicle", "fieldtype": "Link", "options": "Vehicle",
		"insert_after": "applies_to_variant_of_name", "in_standard_filter": 1},

	{"label": "License Plate", "fieldname": "vehicle_license_plate", "fieldtype": "Data", "depends_on": "eval:!doc.vehicle_unregistered",
		"insert_after": "applies_to_item_name", "read_only": 0, "fetch_from": ""},
	{"label": "Is Unregistered", "fieldname": "vehicle_unregistered", "fieldtype": "Check", "depends_on": "eval:!doc.vehicle_license_plate || doc.vehicle_unregistered",
		"insert_after": "vehicle_license_plate", "read_only": 0, "fetch_from": ""},

	{"label": "", "fieldname": "col_break_vehicle_1", "fieldtype": "Column Break",
		"insert_after": "vehicle_unregistered"},

	{"label": "Chassis No", "fieldname": "vehicle_chassis_no", "fieldtype": "Data",
		"insert_after": "col_break_vehicle_1", "read_only": 0, "fetch_from": ""},
	{"label": "Engine No", "fieldname": "vehicle_engine_no", "fieldtype": "Data",
		"insert_after": "vehicle_chassis_no", "read_only": 0, "fetch_from": ""},

	{"label": "", "fieldname": "col_break_vehicle_2", "fieldtype": "Column Break",
		"insert_after": "vehicle_engine_no"},

	{"label": "Vehicle Color", "fieldname": "vehicle_color", "fieldtype": "Link", "options": "Vehicle Color",
		"insert_after": "col_break_vehicle_2", "read_only": 0, "fetch_from": ""},
	{"label": "Odometer Reading", "fieldname": "vehicle_last_odometer", "fieldtype": "Int",
		"insert_after": "vehicle_color", "read_only": 0, "fetch_from": "", "no_copy": 0},
]


# Applies to Project Fields
applies_to_project_fields = deepcopy(applies_to_fields)

project_first_odometer = {"label": "Odometer Reading (First)", "fieldname": "vehicle_first_odometer", "fieldtype": "Int"}
insert_field_after('vehicle_color', project_first_odometer, applies_to_project_fields)
get_field('vehicle_last_odometer', applies_to_project_fields).update({"label": "Odometer Reading (Last)",
	"fetch_from": ""})

vehicle_warranty_no = {"label": "Warranty Book No", "fieldname": "vehicle_warranty_no", "fieldtype": "Data",
	"insert_after": "cb_warranty_1"}
applies_to_project_fields.append(vehicle_warranty_no)

fqr_no = {"label": "FQR No", "fieldname": "fqr_no", "fieldtype": "Data", "no_copy": 1,
	"insert_after": "cb_warranty_2"}
applies_to_project_fields.append(fqr_no)


# Vehicle Owner
vehicle_owner_fields = [
	{"label": "Vehicle Owner", "fieldname": "vehicle_owner", "fieldtype": "Link", "options": "Customer",
		"insert_after": "", "in_standard_filter": 0, "fetch_from": "", "read_only": 0},
	{"label": "Vehicle Owner Name", "fieldname": "vehicle_owner_name", "fieldtype": "Data",
		"insert_after": "vehicle_owner", "fetch_from": "vehicle_owner.customer_name", "read_only": 1,
		"depends_on": "eval:doc.vehicle_owner && doc.vehicle_owner_name != doc.vehicle_owner"},
]

sales_invoice_vehicle_owner_fields = deepcopy(vehicle_owner_fields)
sales_invoice_vehicle_owner_field = [f for f in sales_invoice_vehicle_owner_fields if f['fieldname'] == 'vehicle_owner'][0]
sales_invoice_vehicle_owner_field['insert_after'] = 'bill_to_name'

project_vehicle_owner_fields = deepcopy(vehicle_owner_fields)
project_vehicle_owner_column_break = {"label": "", "fieldname": "col_break_customer_details_2", "fieldtype": "Column Break",
	"insert_after": "bill_to_name"}
project_vehicle_owner_fields.insert(0, project_vehicle_owner_column_break)

project_vehicle_owner_field = [f for f in project_vehicle_owner_fields if f['fieldname'] == 'vehicle_owner'][0]
project_vehicle_owner_field['insert_after'] = 'col_break_customer_details_2'

# Service Person
service_person_fields = [
	{"label": "Service Advisor", "fieldname": "service_advisor", "fieldtype": "Link", "options": "Sales Person",
		"insert_after": "more_info_cb_2", "in_standard_filter": 1},
	{"label": "Service Manager", "fieldname": "service_manager", "fieldtype": "Link", "options": "Sales Person",
		"insert_after": "more_info_cb_3", "in_standard_filter": 1},
]

material_request_service_person_fields = deepcopy(service_person_fields)
[d for d in material_request_service_person_fields if d['fieldname'] == 'service_advisor'][0]['insert_after'] = 'more_info_cb_1'
[d for d in material_request_service_person_fields if d['fieldname'] == 'service_manager'][0]['insert_after'] = 'more_info_cb_2'

# Accounting Dimensions
accounting_dimension_fields = [
	{"label": "Applies to Vehicle", "fieldname": "applies_to_vehicle", "fieldtype": "Link", "options": "Vehicle",
		"insert_after": "cost_center", "in_standard_filter": 1, "ignore_user_permissions": 1},
	{"label": "Vehicle Booking Order", "fieldname": "vehicle_booking_order", "fieldtype": "Link", "options": "Vehicle Booking Order",
		"insert_after": "project", "in_standard_filter": 1, "ignore_user_permissions": 1},

	{"label": "", "fieldname": "vehicle_accounting_dimensions_cb_1", "fieldtype": "Column Break",
		"insert_after": "vehicle_booking_order"},

	{"label": "Vehicle Item Name", "fieldname": "applies_to_item_name", "fieldtype": "Data",
		"insert_after": "vehicle_accounting_dimensions_cb_1", "read_only": 1, "fetch_from": "applies_to_vehicle.item_name"},

	{"label": "", "fieldname": "vehicle_accounting_dimensions_cb_2", "fieldtype": "Column Break",
		"insert_after": "applies_to_item_name"},

	{"label": "Chassis No", "fieldname": "vehicle_chassis_no", "fieldtype": "Data",
		"insert_after": "vehicle_accounting_dimensions_cb_2", "read_only": 1, "fetch_from": "applies_to_vehicle.chassis_no"},
	{"label": "Engine No", "fieldname": "vehicle_engine_no", "fieldtype": "Data",
		"insert_after": "vehicle_chassis_no", "read_only": 1, "fetch_from": "applies_to_vehicle.engine_no"},
	{"label": "License Plate", "fieldname": "vehicle_license_plate", "fieldtype": "Data", "depends_on": "eval:!doc.vehicle_unregistered",
		"insert_after": "vehicle_engine_no", "read_only": 1, "fetch_from": "applies_to_vehicle.license_plate"},
]

accounting_dimension_table_fields = deepcopy(accounting_dimension_fields)
for d in accounting_dimension_table_fields:
	if 'in_standard_filter' in d:
		del d['in_standard_filter']

# Item Fields
item_fields = [
	{"label": "Vehicle Allocation Required From Delivery Period", "fieldname": "vehicle_allocation_required_from_delivery_period",
		"fieldtype": "Link", "options": "Vehicle Allocation Period",
		"insert_after": "vehicle_allocation_required", "depends_on": "vehicle_allocation_required", "ignore_user_permissions": 1},
]

# Set Translatable = 0
for d in applies_to_fields:
	d['translatable'] = 0
for d in applies_to_project_fields:
	d['translatable'] = 0
for d in vehicle_owner_fields:
	d['translatable'] = 0
for d in sales_invoice_vehicle_owner_fields:
	d['translatable'] = 0
for d in project_vehicle_owner_fields:
	d['translatable'] = 0
for d in service_person_fields:
	d['translatable'] = 0
for d in material_request_service_person_fields:
	d['translatable'] = 0
for d in accounting_dimension_fields:
	d['translatable'] = 0
for d in accounting_dimension_table_fields:
	d['translatable'] = 0
for d in item_fields:
	d['translatable'] = 0

common_properties = [
	[('Delivery Note Item', 'Sales Invoice Item', 'Purchase Receipt Item', 'Purchase Invoice Item', 'Stock Entry Detail'),
		{"fieldname": "vehicle", "property": "in_standard_filter", "value": 0}],

	[('Quotation', 'Sales Order', 'Delivery Note', 'Sales Invoice', 'Purchase Order', 'Purchase Receipt', 'Purchase Invoice', 'Project', 'Material Request'),
		{"fieldname": "sec_applies_to", "property": "hidden", "value": 0}],

	[('Quotation', 'Sales Order', 'Delivery Note', 'Sales Invoice', 'Purchase Order', 'Purchase Receipt', 'Purchase Invoice', 'Project', 'Material Request'),
		{"fieldname": "sec_applies_to", "property": "label", "value": "Vehicle Details"}],

	[('Quotation', 'Sales Order', 'Delivery Note', 'Sales Invoice', 'Purchase Order', 'Purchase Receipt', 'Purchase Invoice', 'Project', 'Material Request'),
		{"fieldname": "sec_applies_to", "property": "collapsible_depends_on",
			"value": "eval:doc.applies_to_item || doc.applies_to_vehicle || doc.vehicle_license_plate || doc.vehicle_chassis_no || doc.vehicle_engine_no"}],

	[('Quotation', 'Sales Order', 'Delivery Note', 'Sales Invoice', 'Purchase Order', 'Purchase Receipt', 'Purchase Invoice', 'Project', 'Material Request'),
		{"fieldname": "applies_to_item", "property": "fetch_from", "value": "applies_to_vehicle.item_code"}],

	[('Quotation', 'Sales Order', 'Delivery Note', 'Sales Invoice', 'Project', 'Material Request'),
		{"fieldname": "customer", "property": "label", "value": "Customer (User)"}],
	[('Quotation', 'Sales Order', 'Delivery Note', 'Sales Invoice', 'Project', 'Material Request'),
		{"fieldname": "customer_name", "property": "label", "value": "Customer Name (User)"}],

	[('Sales Invoice', 'Quotation', 'Project'),
		{"fieldname": "sec_insurance", "property": "hidden", "value": 0}],

	[('Project',),
		{"fieldname": "sec_warranty", "property": "hidden", "value": 0}],

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
		'Vehicle Stock User',
		'Vehicle Registration User',
		'Sales Admin'
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
		"Item": item_fields,
		"Sales Invoice": sales_invoice_vehicle_owner_fields + applies_to_fields + service_person_fields,
		"Delivery Note": applies_to_fields + service_person_fields,
		"Sales Order": applies_to_fields + service_person_fields,
		"Quotation": applies_to_fields + service_person_fields,
		"Purchase Order": applies_to_fields,
		"Purchase Receipt": applies_to_fields,
		"Purchase Invoice": applies_to_fields,
		"Material Request": applies_to_fields + material_request_service_person_fields,
		"Project": project_vehicle_owner_fields + applies_to_project_fields + service_person_fields,
		"Journal Entry": accounting_dimension_fields,
		"Journal Entry Account": accounting_dimension_table_fields,
		"Payment Entry": accounting_dimension_fields,
	},
	'default_portal_role': 'Customer'
}

for dts, prop_template in common_properties:
	for doctype in dts:
		prop = prop_template.copy()
		prop['doctype'] = doctype
		data['properties'].append(prop)
