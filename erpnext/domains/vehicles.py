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

applies_to_appointment_fields = deepcopy(applies_to_transaction_fields)
for f in applies_to_appointment_fields:
	f['allow_on_submit'] = 1

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

# Project fields
project_fields = [
	{"label": "FQR No", "fieldname": "fqr_no", "fieldtype": "Data", "no_copy": 1,
		"insert_after": "cb_warranty_1"},

	{"label": "Is Periodic Maintenance", "fieldname": "is_periodic_maintenance", "fieldtype": "Check",
		"insert_after": "cb_work_details_2"},
	{"label": "Is General Repair", "fieldname": "is_general_repair", "fieldtype": "Check",
		"insert_after": "is_periodic_maintenance"},

	{"label": "Vehicle Status", "fieldname": "vehicle_status", "fieldtype": "Select",
		"insert_after": "delivery_status", "options": "Not Applicable\nNot Received\nIn Workshop\nDelivered",
		"default": "Not Applicable", "read_only": 1, "no_copy": 1, "in_standard_filter": 1},

	{"label": "Vehicle Booking Order", "fieldname": "vehicle_booking_order", "fieldtype": "Link",
		"insert_after": "service_manager", "options": "Vehicle Booking Order", "read_only": 1, "no_copy": 1, "in_standard_filter": 1},

	{"label": "Vehicle Panel Detail", "fieldname": "vehicle_panels", "fieldtype": "Table",
		"insert_after": "project_templates", "options": "Project Panel Detail", "hidden": 1},
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
		"insert_after": "sec_change_vehicle_details", "no_copy": 1, "report_hide": 1,
		"depends_on": "eval:!doc.change_vehicle_unregistered"},
	{"label": "Set Is Unregistered", "fieldname": "change_vehicle_unregistered", "fieldtype": "Check",
		"insert_after": "change_vehicle_license_plate", "no_copy": 1, "report_hide": 1},

	{"label": "", "fieldname": "cb_change_vehicle_details_1", "fieldtype": "Column Break",
		"insert_after": "change_vehicle_unregistered"},

	{"label": "Change Warranty Book No", "fieldname": "change_vehicle_warranty_no", "fieldtype": "Data",
		"insert_after": "cb_change_vehicle_details_1", "no_copy": 1, "report_hide": 1},

	{"label": "", "fieldname": "cb_change_vehicle_details_2", "fieldtype": "Column Break",
		"insert_after": "change_vehicle_warranty_no"},

	{"label": "Change Vehicle Delivery Date", "fieldname": "change_vehicle_delivery_date", "fieldtype": "Date",
		"insert_after": "cb_change_vehicle_details_2", "no_copy": 1, "report_hide": 1},
]

# Project Vehicle Reading Fields
project_vehicle_reading_fields = [
	{"label": "Vehicle Readings", "fieldname": "sec_vehicle_status", "fieldtype": "Section Break",
		"insert_after": "vehicle_panels", "collapsible": 0},

	{"label": "Odometer Reading (First)", "fieldname": "vehicle_first_odometer", "fieldtype": "Int",
		"insert_after": "sec_vehicle_status", "no_copy": 1},
	{"label": "Vehicle Received Date", "fieldname": "vehicle_received_date", "fieldtype": "Date",
		"insert_after": "vehicle_first_odometer", "read_only": 1, "no_copy": 1, "in_standard_filter": 1, "search_index": 1},
	{"label": "Vehicle Received Time", "fieldname": "vehicle_received_time", "fieldtype": "Time",
		"insert_after": "vehicle_received_date", "read_only": 1, "no_copy": 1},

	{"label": "", "fieldname": "cb_vehicle_status_1", "fieldtype": "Column Break",
		"insert_after": "vehicle_received_time"},

	{"label": "Odometer Reading (Last)", "fieldname": "vehicle_last_odometer", "fieldtype": "Int",
		"insert_after": "cb_vehicle_status_1", "no_copy": 1},
	{"label": "Vehicle Delivered Date", "fieldname": "vehicle_delivered_date", "fieldtype": "Date",
		"insert_after": "vehicle_last_odometer", "read_only": 1, "no_copy": 1, "in_standard_filter": 1, "search_index": 1},
	{"label": "Vehicle Delivered Time", "fieldname": "vehicle_delivered_time", "fieldtype": "Time",
		"insert_after": "vehicle_delivered_date", "read_only": 1, "no_copy": 1},

	{"label": "", "fieldname": "cb_vehicle_status_2", "fieldtype": "Column Break",
		"insert_after": "vehicle_delivered_time"},

	{"label": "Fuel Level (%)", "fieldname": "fuel_level", "fieldtype": "Percent", "precision": 0,
		"insert_after": "cb_vehicle_status_2", "no_copy": 1},
	{"label": "No of Keys", "fieldname": "keys", "fieldtype": "Int",
		"insert_after": "fuel_level"},

	{"label": "Checklist", "fieldname": "sec_vehicle_checklist", "fieldtype": "Section Break",
		"insert_after": "keys", "collapsible": 0},

	{"label": "Vehicle Checklist", "fieldname": "vehicle_checklist_html", "fieldtype": "HTML",
		"insert_after": "sec_vehicle_checklist"},
	{"label": "Vehicle Checklist", "fieldname": "vehicle_checklist", "fieldtype": "Table", "options": "Vehicle Checklist Item",
		"insert_after": "vehicle_checklist_html", "hidden": 1},

	{"label": "", "fieldname": "cb_vehicle_checklist_1", "fieldtype": "Column Break",
		"insert_after": "vehicle_checklist"},

	{"label": "Customer Request Checklist", "fieldname": "customer_request_checklist_html", "fieldtype": "HTML",
		"insert_after": "cb_vehicle_checklist_1"},
	{"label": "Customer Request Checklist", "fieldname": "customer_request_checklist", "fieldtype": "Table", "options": "Vehicle Checklist Item",
		"insert_after": "customer_request_checklist_html", "hidden": 1},
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

# Project Template Fields
project_template_fields = [
	{"label": "Checklist", "fieldname": "sec_vehicle_checklist", "fieldtype": "Section Break",
		"insert_after": "tasks"},

	{"label": "Customer Request Checklist", "fieldname": "customer_request_checklist_html", "fieldtype": "HTML",
		"insert_after": "sec_vehicle_checklist"},
	{"label": "Customer Request Checklist", "fieldname": "customer_request_checklist", "fieldtype": "Table", "options": "Vehicle Checklist Item",
		"insert_after": "customer_request_checklist_html", "hidden": 1},

	{"label": "", "fieldname": "cb_vehicle_checklist_1", "fieldtype": "Column Break",
		"insert_after": "customer_request_checklist"},
]

project_template_detail_fields = [
	{"label": "Panel Job", "fieldname": "is_panel_job", "fieldtype": "Check",
		"insert_after": "project_template_name", "in_list_view": 1, "columns": 1}
]

project_template_category_fields = deepcopy(project_template_fields)
[d for d in project_template_category_fields if d['fieldname'] == 'sec_vehicle_checklist'][0]['insert_after'] = 'description'

# Customer Vehicle Selector Fields
customer_vehicle_selector_fields = [
	{"label": "Customer Vehicles", "fieldname": "sec_customer_vehicle_selector", "fieldtype": "Section Break",
		"collapsible": 1, "collapsible_depends_on": "eval:!doc.applies_to_vehicle || (!doc.customer && !doc.party_name)"},
	{"label": "Customer Vehicle Selector HTML", "fieldname": "customer_vehicle_selector_html", "fieldtype": "HTML",
		"insert_after": "sec_customer_vehicle_selector"},
]

project_customer_vehicle_selector = deepcopy(customer_vehicle_selector_fields)
[d for d in project_customer_vehicle_selector if d['fieldname'] == 'sec_customer_vehicle_selector'][0]['insert_after'] = 'secondary_contact_mobile'

appointment_customer_vehicle_selector = deepcopy(customer_vehicle_selector_fields)
[d for d in appointment_customer_vehicle_selector if d['fieldname'] == 'sec_customer_vehicle_selector'][0]['insert_after'] = 'secondary_contact_mobile'

customer_customer_vehicle_selector = deepcopy(customer_vehicle_selector_fields)
[d for d in customer_customer_vehicle_selector if d['fieldname'] == 'sec_customer_vehicle_selector'][0]['insert_after'] = 'contact_html'
[d for d in customer_customer_vehicle_selector if d['fieldname'] == 'sec_customer_vehicle_selector'][0]['collapsible_depends_on'] = "eval:true"
[d for d in customer_customer_vehicle_selector if d['fieldname'] == 'sec_customer_vehicle_selector'][0]['depends_on'] = "eval:!doc.__islocal"

# Opportunity Fields
opportunity_fields = [
	{"label": "Financer", "fieldname": "vehicle_sb_1", "fieldtype": "Section Break",
		"insert_after": "status"},
	{"label": "Financer", "fieldname": "financer", "fieldtype": "Link", "options": "Customer",
		"insert_after": "vehicle_sb_1"},
	{"label": "", "fieldname": "vehcle_cb_1", "fieldtype": "Column Break",
		"insert_after": "financer"},
	{"label": "Financer Name", "fieldname": "financer_name", "fieldtype": "Data", "fetch_from": "financer.customer_name", "read_only": 1,
		"insert_after": "vehcle_cb_1", "depends_on": "eval:doc.financer && doc.financer_name != doc.financer"},
	{"label": "", "fieldname": "vehcle_cb_2", "fieldtype": "Column Break",
		"insert_after": "financer_name"},
	{"label": "Finance Type", "fieldname": "finance_type", "fieldtype": "Select", "options": "\nFinanced\nLeased",
		"insert_after": "vehcle_cb_2", "depends_on": "financer"},

	{"label": "", "fieldname": "vehicle_sb_2", "fieldtype": "Section Break",
		"insert_after": "items"},
	{"label": "Delivery Period", "fieldname": "delivery_period", "fieldtype": "Link", "options": "Vehicle Allocation Period",
		"insert_after": "vehicle_sb_2", "no_copy": 1},
	{"label": "", "fieldname": "vehcle_cb_3", "fieldtype": "Column Break",
		"insert_after": "delivery_period"},
	{"label": "First/Additional", "fieldname": "first_additional", "fieldtype": "Select", "options": "\nFirst\nAdditional\nReplacement",
		"insert_after": "vehcle_cb_3", "no_copy": 1},

	{"label": "Key Features You Like", "fieldname": "liked_features", "fieldtype": "Small Text",
		"insert_after": "feedback_cb_1", "no_copy": 1},
	{"label": "Interior", "fieldname": "rating_interior", "fieldtype": "Rating",
		"insert_after": "ratings_section", "no_copy": 1},
	{"label": "", "fieldname": "rating_cb_1", "fieldtype": "Column Break",
		"insert_after": "rating_interior"},
	{"label": "Exterior", "fieldname": "rating_exterior", "fieldtype": "Rating",
		"insert_after": "rating_cb_1", "no_copy": 1},
	{"label": "", "fieldname": "rating_cb_2", "fieldtype": "Column Break",
		"insert_after": "rating_exterior"},
	{"label": "Specifications", "fieldname": "rating_specifications", "fieldtype": "Rating",
		"insert_after": "rating_cb_2", "no_copy": 1},
	{"label": "", "fieldname": "rating_cb_3", "fieldtype": "Column Break",
		"insert_after": "rating_specifications"},
	{"label": "Price", "fieldname": "rating_price", "fieldtype": "Rating",
		"insert_after": "rating_cb_3", "no_copy": 1},
]

applies_to_opportunity_fields = deepcopy(applies_to_transaction_fields)
[d.update({"no_copy": 1}) for d in applies_to_opportunity_fields if d["fieldtype"] != "Column Break"]

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
	{"label": "Booking Customer Name", "fieldname": "booking_customer_name", "fieldtype": "Data",
		"insert_after": "applies_to_item_name", "read_only": 1, "fetch_from": "vehicle_booking_order.customer_name"},

	{"label": "", "fieldname": "vehicle_accounting_dimensions_cb_2", "fieldtype": "Column Break",
		"insert_after": "booking_customer_name"},

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
field_lists = [
	applies_to_fields, applies_to_transaction_fields, applies_to_project_fields, applies_to_appointment_fields,
	project_vehicle_reading_fields, vehicle_owner_fields, sales_invoice_vehicle_owner_fields, service_person_fields,
	material_request_service_person_fields, accounting_dimension_fields, accounting_dimension_table_fields,
	item_fields, project_fields, project_type_fields, project_change_vehicle_details_fields,
	project_template_fields, project_template_category_fields, project_template_detail_fields,
	customer_vehicle_selector_fields, project_customer_vehicle_selector, appointment_customer_vehicle_selector,
	customer_customer_vehicle_selector, opportunity_fields, applies_to_opportunity_fields,
]

for field_list in field_lists:
	for d in field_list:
		d['translatable'] = 0

common_properties = [
	# Unhide Vehicle Details Section
	[('Quotation', 'Sales Order', 'Delivery Note', 'Sales Invoice', 'Purchase Order', 'Purchase Receipt', 'Purchase Invoice', 'Project', 'Material Request', 'Appointment', 'Opportunity'),
		{"fieldname": "sec_applies_to", "property": "hidden", "value": 0}],

	# Vehicle Details Section Label
	[('Quotation', 'Sales Order', 'Delivery Note', 'Sales Invoice', 'Purchase Order', 'Purchase Receipt', 'Purchase Invoice', 'Project', 'Material Request', 'Appointment', 'Opportunity'),
		{"fieldname": "sec_applies_to", "property": "label", "value": "Vehicle Details"}],

	# Vehicle Details Collapsible
	[('Quotation', 'Sales Order', 'Delivery Note', 'Sales Invoice', 'Purchase Order', 'Purchase Receipt', 'Purchase Invoice', 'Project', 'Material Request', 'Appointment', 'Opportunity'),
		{"fieldname": "sec_applies_to", "property": "collapsible_depends_on",
			"value": "eval:doc.applies_to_item || doc.applies_to_serial_no || doc.applies_to_vehicle || doc.vehicle_license_plate || doc.vehicle_chassis_no || doc.vehicle_engine_no"}],

	# Vehicle Details Applies To Serial No hidden
	[('Quotation', 'Sales Order', 'Delivery Note', 'Sales Invoice', 'Purchase Order', 'Purchase Receipt', 'Purchase Invoice', 'Project', 'Material Request', 'Appointment', 'Opportunity'),
		{"fieldname": "applies_to_serial_no", "property": "hidden", "value": 1}],

	# Applies to Model label
	[('Quotation', 'Sales Order', 'Delivery Note', 'Sales Invoice', 'Purchase Order', 'Purchase Receipt', 'Purchase Invoice', 'Project', 'Material Request', 'Appointment', 'Opportunity'),
		{"fieldname": "applies_to_variant_of", "property": "label", "value": "Applies to Model"}],
	[('Quotation', 'Sales Order', 'Delivery Note', 'Sales Invoice', 'Purchase Order', 'Purchase Receipt', 'Purchase Invoice', 'Project', 'Material Request', 'Appointment', 'Opportunity'),
		{"fieldname": "applies_to_variant_of_name", "property": "label", "value": "Applies to Model Name"}],

	# Customer (User) Label
	[('Quotation', 'Sales Order', 'Delivery Note', 'Sales Invoice', 'Project', 'Material Request'),
		{"fieldname": "customer", "property": "label", "value": "Customer (User)"}],
	[('Quotation', 'Sales Order', 'Delivery Note', 'Sales Invoice', 'Project', 'Material Request'),
		{"fieldname": "customer_name", "property": "label", "value": "Customer Name (User)"}],

	# Unhide Insurance Section
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
		'Vehicle Manager',
		'Vehicle Stock User',
		'Vehicle Registration User',
		'Sales Admin',
	],
	'modules': [

	],
	'properties': [
		{"doctype": "Item", "fieldname": "is_vehicle", "property": "in_standard_filter", "value": 1},
		{"doctype": "Customer", "fieldname": "is_insurance_company", "property": "in_standard_filter", "value": 1},
		{"doctype": "Sales Invoice", "fieldname": "bill_to", "property": "hidden", "value": 0},
		{"doctype": "Sales Invoice", "fieldname": "claim_billing", "property": "hidden", "value": 0},
		{"doctype": "Project", "fieldname": "bill_to", "property": "hidden", "value": 0},
		{"doctype": "Project", "fieldname": "sec_warranty", "property": "hidden", "value": 0},
		{"doctype": "Project", "fieldname": "previous_project", "property": "label", "value": "Previous Repair Order"},
		{"doctype": "Project", "fieldname": "project_name", "property": "label", "value": "Voice of Customer"},
		{"doctype": "Project Type", "fieldname": "previous_project_mandatory", "property": "label", "value": "Previous Repair Order Mandatory"},
		{"doctype": "Payment Terms Template", "fieldname": "include_in_vehicle_booking", "property": "hidden", "value": 0},
		{"doctype": "Project Template Detail", "fieldname": "project_template_name", "property": "columns", "value": 7},
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
			project_vehicle_reading_fields + project_customer_vehicle_selector,
		"Appointment": applies_to_appointment_fields + appointment_customer_vehicle_selector,
		"Journal Entry": accounting_dimension_fields,
		"Journal Entry Account": accounting_dimension_table_fields,
		"Payment Entry": accounting_dimension_fields,
		"Project Type": project_type_fields,
		"Project Template": project_template_fields,
		"Project Template Category": project_template_category_fields,
		"Project Template Detail": project_template_detail_fields,
		"Customer": customer_customer_vehicle_selector,
		"Opportunity": opportunity_fields + applies_to_opportunity_fields,
	},
	'default_portal_role': 'Customer'
}

for dts, prop_template in common_properties:
	for doctype in dts:
		prop = prop_template.copy()
		prop['doctype'] = doctype
		data['properties'].append(prop)
