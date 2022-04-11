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


# Vehicle Details / Applies To
applies_to_fields = [
	{"label": "Applies to Model", "fieldname": "applies_to_variant_of", "fieldtype": "Link", "options": "Item",
		"insert_after": "sec_applies_to", "in_standard_filter": 1, "hidden": 1, "read_only": 1,
		"fetch_from": "applies_to_item.variant_of"},
	{"label": "Applies to Model Name", "fieldname": "applies_to_variant_of_name", "fieldtype": "Data",
		"insert_after": "applies_to_variant_of", "hidden": 1, "read_only": 1, "fetch_from": "applies_to_variant_of.item_name"},

	{"label": "Applies to Vehicle", "fieldname": "applies_to_vehicle", "fieldtype": "Link", "options": "Vehicle",
		"insert_after": "applies_to_variant_of_name", "in_standard_filter": 1},

	{"label": "License Plate", "fieldname": "vehicle_license_plate", "fieldtype": "Data",
		"insert_after": "applies_to_item_name", "depends_on": "eval:!doc.vehicle_unregistered"},
	{"label": "Is Unregistered", "fieldname": "vehicle_unregistered", "fieldtype": "Check",
		"insert_after": "vehicle_license_plate", "depends_on": "eval:!doc.vehicle_license_plate || doc.vehicle_unregistered"},

	{"label": "", "fieldname": "col_break_vehicle_1", "fieldtype": "Column Break",
		"insert_after": "vehicle_unregistered"},

	{"label": "Chassis No", "fieldname": "vehicle_chassis_no", "fieldtype": "Data",
		"insert_after": "col_break_vehicle_1"},
	{"label": "Engine No", "fieldname": "vehicle_engine_no", "fieldtype": "Data",
		"insert_after": "vehicle_chassis_no"},

	{"label": "", "fieldname": "col_break_vehicle_2", "fieldtype": "Column Break",
		"insert_after": "vehicle_engine_no"},

	{"label": "Vehicle Color", "fieldname": "vehicle_color", "fieldtype": "Link", "options": "Vehicle Color",
		"insert_after": "col_break_vehicle_2"},
]

applies_to_transaction_fields = deepcopy(applies_to_fields)
vehicle_last_odometer = {"label": "Odometer Reading", "fieldname": "vehicle_last_odometer", "fieldtype": "Int"}
insert_field_after('vehicle_color', vehicle_last_odometer, applies_to_transaction_fields)

# Vehicle Owner
vehicle_owner_fields = [
	{"label": "Vehicle Owner", "fieldname": "vehicle_owner", "fieldtype": "Link", "options": "Customer",
		"insert_after": ""},
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

# Service Persons
service_person_fields = [
	{"label": "Service Advisor", "fieldname": "service_advisor", "fieldtype": "Link", "options": "Sales Person",
		"insert_after": "more_info_cb_2", "in_standard_filter": 1},
	{"label": "Service Manager", "fieldname": "service_manager", "fieldtype": "Link", "options": "Sales Person",
		"insert_after": "more_info_cb_3", "in_standard_filter": 1},
]

material_request_service_person_fields = deepcopy(service_person_fields)
[d for d in material_request_service_person_fields if d['fieldname'] == 'service_advisor'][0]['insert_after'] = 'more_info_cb_1'
[d for d in material_request_service_person_fields if d['fieldname'] == 'service_manager'][0]['insert_after'] = 'more_info_cb_2'

project_service_person_fields = deepcopy(service_person_fields)
[d for d in project_service_person_fields if d['fieldname'] == 'service_advisor'][0]['insert_after'] = 'project_type'
[d for d in project_service_person_fields if d['fieldname'] == 'service_manager'][0]['insert_after'] = 'service_advisor'

# Project fields
project_fields = [
	{"label": "Vehicle Workshop", "fieldname": "vehicle_workshop", "fieldtype": "Link", "options": "Vehicle Workshop",
		"insert_after": "reference_no", "bold": 1, "allow_in_quick_entry": 1, "in_standard_filter": 1},

	{"label": "FQR No", "fieldname": "fqr_no", "fieldtype": "Data", "no_copy": 1,
		"insert_after": "cb_warranty_1"},

	{"label": "Is Periodic Maintenance", "fieldname": "is_periodic_maintenance", "fieldtype": "Check",
		"insert_after": "project_name"},
	{"label": "Is General Repair", "fieldname": "is_general_repair", "fieldtype": "Check",
		"insert_after": "is_periodic_maintenance"},
]

# Applies To Project Fields
applies_to_project_fields = deepcopy(applies_to_fields)

project_vehicle_warranty_no = {"label": "Warranty Book No", "fieldname": "vehicle_warranty_no", "fieldtype": "Data"}
insert_field_after('vehicle_color', project_vehicle_warranty_no, applies_to_project_fields)

project_vehicle_delivery_date = {"label": "Vehicle Delivery Date", "fieldname": "vehicle_delivery_date", "fieldtype": "Date"}
insert_field_after('vehicle_warranty_no', project_vehicle_delivery_date, applies_to_project_fields)

# Change Vehicle Detail Fields
project_change_vehicle_details_section = {"label": "Change Vehicle Details",
	"fieldname": "sec_change_vehicle_details", "fieldtype": "Section Break", "collapsible": 1,
	"depends_on": "applies_to_vehicle"}
insert_field_after('vehicle_delivery_date', project_change_vehicle_details_section, applies_to_project_fields)

project_change_vehicle_details_fields = [
	{"label": "Change License Plate", "fieldname": "change_vehicle_license_plate", "fieldtype": "Data",
		"insert_after": "sec_change_vehicle_details", "no_copy": 1, "report_hide": 1},

	{"label": "", "fieldname": "cb_change_vehicle_details_1", "fieldtype": "Column Break",
		"insert_after": "change_vehicle_license_plate"},

	{"label": "Change Warranty Book No", "fieldname": "change_vehicle_warranty_no", "fieldtype": "Data",
		"insert_after": "cb_change_vehicle_details_1", "no_copy": 1, "report_hide": 1},

	{"label": "", "fieldname": "cb_change_vehicle_details_2", "fieldtype": "Column Break",
		"insert_after": "change_vehicle_warranty_no"},

	{"label": "Change Vehicle Delivery Date", "fieldname": "change_vehicle_delivery_date", "fieldtype": "Date",
		"insert_after": "cb_change_vehicle_details_2", "no_copy": 1, "report_hide": 1},
]

# Project Vehicle Status Fields
project_vehicle_readings_section = {"label": "Vehicle Readings & Checklist",
	"fieldname": "sec_vehicle_status", "fieldtype": "Section Break", "collapsible": 0}
insert_field_after('change_vehicle_delivery_date', project_vehicle_readings_section, project_change_vehicle_details_fields)

project_vehicle_reading_fields = [
	{"label": "Odometer Reading (First)", "fieldname": "vehicle_first_odometer", "fieldtype": "Int",
		"insert_after": "sec_vehicle_status", "no_copy": 1},
	{"label": "Vehicle Received Date/Time", "fieldname": "vehicle_received_dt", "fieldtype": "Datetime",
		"insert_after": "vehicle_first_odometer", "read_only": 1, "no_copy": 1},
	{"label": "Odometer Reading (Last)", "fieldname": "vehicle_last_odometer", "fieldtype": "Int",
		"insert_after": "vehicle_received_dt", "no_copy": 1},
	{"label": "Vehicle Delivered Date/Time", "fieldname": "vehicle_delivered_dt", "fieldtype": "Datetime",
		"insert_after": "vehicle_last_odometer", "read_only": 1, "no_copy": 1},
	{"label": "Receive Vehicle", "fieldname": "receive_vehicle_btn", "fieldtype": "Button",
		"insert_after": "vehicle_delivered_dt", "hidden": 1},
	{"label": "Deliver Vehicle", "fieldname": "deliver_vehicle_btn", "fieldtype": "Button",
		"insert_after": "receive_vehicle_btn", "hidden": 1},

	{"label": "", "fieldname": "cb_vehicle_status_1", "fieldtype": "Column Break",
		"insert_after": "deliver_vehicle_btn"},

	{"label": "Fuel Level (%)", "fieldname": "fuel_level", "fieldtype": "Percent", "precision": 0,
		"insert_after": "cb_vehicle_status_1", "no_copy": 1},
	{"label": "No of Keys", "fieldname": "keys", "fieldtype": "Int",
		"insert_after": "fuel_level"},
	{"label": "Vehicle Status", "fieldname": "vehicle_status", "fieldtype": "Select",
		"options": "Not Received\nIn Workshop\nDelivered", "default": "Not Received",
		"insert_after": "keys", "read_only": 1, "no_copy": 1, "in_standard_filter": 1},

	{"label": "", "fieldname": "cb_vehicle_status_2", "fieldtype": "Column Break",
		"insert_after": "vehicle_status"},

	{"label": "Vehicle Checklist", "fieldname": "vehicle_checklist_html", "fieldtype": "HTML",
		"insert_after": "cb_vehicle_status_2"},
	{"label": "Vehicle Checklist", "fieldname": "vehicle_checklist", "fieldtype": "Table", "options": "Vehicle Checklist Item",
		"insert_after": "vehicle_checklist_html", "hidden": 1},
]

# Project Type Fields
project_type_fields = [
	{"label": "Is Periodic Maintenance", "fieldname": "is_periodic_maintenance", "fieldtype": "Select",
		"insert_after": "sec_defaults", "options": "\nNo\nYes"},
	{"label": "Is General Repair", "fieldname": "is_general_repair", "fieldtype": "Select",
		"insert_after": "is_periodic_maintenance", "options": "\nNo\nYes"},
	{"label": "", "fieldname": "cb_defaults_0", "fieldtype": "Column Break",
		"insert_after": "is_general_repair"},
]

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
for d in applies_to_transaction_fields:
	d['translatable'] = 0
for d in applies_to_project_fields:
	d['translatable'] = 0
for d in project_vehicle_reading_fields:
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
for d in project_fields:
	d['translatable'] = 0
for d in project_type_fields:
	d['translatable'] = 0
for d in project_change_vehicle_details_fields:
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
		{"doctype": "Sales Invoice", "fieldname": "bill_multiple_projects", "property": "hidden", "value": 0},
		{"doctype": "Sales Invoice", "fieldname": "bill_multiple_projects", "property": "label", "value": "Bill Multiple Repair Orders"},
		{"doctype": "Project", "fieldname": "bill_to", "property": "hidden", "value": 0},
		{"doctype": "Project", "fieldname": "sec_warranty", "property": "hidden", "value": 0},
		{"doctype": "Project", "fieldname": "previous_project", "property": "label", "value": "Previous Repair Order"},
		{"doctype": "Project Type", "fieldname": "previous_project_mandatory", "property": "label", "value": "Previous Repair Order Mandatory"},
		{"doctype": "Project", "fieldname": "project_name", "property": "label", "value": "Voice of Customer"},
		{"doctype": "Payment Terms Template", "fieldname": "include_in_vehicle_booking", "property": "hidden", "value": 0},
	],
	'custom_fields': {
		"Item": item_fields,
		"Sales Invoice": sales_invoice_vehicle_owner_fields + applies_to_transaction_fields + service_person_fields,
		"Delivery Note": applies_to_transaction_fields + service_person_fields,
		"Sales Order": applies_to_transaction_fields + service_person_fields,
		"Quotation": applies_to_transaction_fields + service_person_fields,
		"Purchase Order": applies_to_transaction_fields,
		"Purchase Receipt": applies_to_transaction_fields,
		"Purchase Invoice": applies_to_transaction_fields,
		"Material Request": applies_to_transaction_fields + material_request_service_person_fields,
		"Project": project_fields + applies_to_project_fields + project_change_vehicle_details_fields +
			project_vehicle_reading_fields + project_vehicle_owner_fields + project_service_person_fields,
		"Journal Entry": accounting_dimension_fields,
		"Journal Entry Account": accounting_dimension_table_fields,
		"Payment Entry": accounting_dimension_fields,
		"Project Type": project_type_fields,
	},
	'default_portal_role': 'Customer'
}

for dts, prop_template in common_properties:
	for doctype in dts:
		prop = prop_template.copy()
		prop['doctype'] = doctype
		data['properties'].append(prop)
