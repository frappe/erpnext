from __future__ import unicode_literals
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
	company = frappe.get_all('Company', filters = {'country': 'India'})
	if not company:
		return

	fields = [
		{
			'fieldname': 'transporter_info',
 			'label': 'Transporter Info',
 			'fieldtype': 'Section Break',
 			'insert_after': 'terms',
 			'collapsible': 1,
 			'collapsible_depends_on': 'transporter',
 			'print_hide': 1
		},
		{
			'fieldname': 'transporter',
			'label': 'Transporter',
			'fieldtype': 'Link',
			'insert_after': 'transporter_info',
			'options': 'Supplier',
			'print_hide': 1
		},
		{
			'fieldname': 'transporter_name',
			'label': 'Transporter Name',
			'fieldtype': 'Data',
			'insert_after': 'transporter',
			'fetch_from': 'transporter.name',
			'read_only': 1,
			'print_hide': 1,
			'translatable': 0
		},
		{
			'fieldname': 'gst_transporter_id',
			'label': 'GST Transporter ID',
			'fieldtype': 'Data',
			'insert_after': 'transporter_name',
			'fetch_from': 'transporter.gst_transporter_id',
			'print_hide': 1,
			'translatable': 0
		},
		{
			'fieldname': 'driver',
			'label': 'Driver',
			'fieldtype': 'Link',
			'insert_after': 'gst_transporter_id',
			'options': 'Driver',
			'print_hide': 1
		},
		{
			'fieldname': 'lr_no',
			'label': 'Transport Receipt No',
			'fieldtype': 'Data',
			'insert_after': 'driver',
			'print_hide': 1,
			'translatable': 0
		},
		{
			'fieldname': 'vehicle_no',
			'label': 'Vehicle No',
			'fieldtype': 'Data',
			'insert_after': 'lr_no',
			'print_hide': 1,
			'translatable': 0
		},
		{
			'fieldname': 'distance',
			'label': 'Distance (in km)',
			'fieldtype': 'Float',
			'insert_after': 'vehicle_no',
			'print_hide': 1
		},
		{
			'fieldname': 'transporter_col_break',
			'fieldtype': 'Column Break',
			'insert_after': 'distance'
		},
		{
			'fieldname': 'transporter_address',
			'label': 'Transporter Address Name',
			'fieldtype': 'Link',
			'insert_after': 'transporter_col_break',
			'options': 'Address',
			'print_hide': 1
		},
		{
			'fieldname': 'transporter_address_display',
			'label': 'Transporter Address Preview',
			'fieldtype': 'Small Text',
			'insert_after': 'transporter_address',
			'read_only': 1,
			'print_hide': 1,
			'translatable': 0
		},
		{
			'fieldname': 'mode_of_transport',
			'label': 'Mode of Transport',
			'fieldtype': 'Select',
			'options': '\nRoad\nAir\nRail\nShip',
			'default': 'Road',
			'insert_after': 'transporter_address_display',
			'print_hide': 1,
			'translatable': 0
		},
		{
			'fieldname': 'driver_name',
			'label': 'Driver Name',
			'fieldtype': 'Data',
			'insert_after': 'mode_of_transport',
			'fetch_from': 'driver.full_name',
			'print_hide': 1,
			'translatable': 0
		},
		{
			'fieldname': 'lr_date',
			'label': 'Transport Receipt Date',
			'fieldtype': 'Date',
			'insert_after': 'driver_name',
			'default': 'Today',
			'print_hide': 1
		},
		{
			'fieldname': 'gst_vehicle_type',
			'label': 'GST Vehicle Type',
			'fieldtype': 'Select',
			'options': 'Regular\nOver Dimensional Cargo (ODC)',
			'depends_on': 'eval:(doc.mode_of_transport === "Road")',
			'default': 'Regular',
			'insert_after': 'lr_date',
			'print_hide': 1,
			'translatable': 0
		},
		{
			'fieldname': 'ewaybill',
			'label': 'e-Way Bill No.',
			'fieldtype': 'Data',
			'depends_on': 'eval:(doc.docstatus === 1)',
			'allow_on_submit': 1,
			'insert_after': 'tax_id',
			'translatable': 0
		}
	]

	create_custom_fields({ 'Sales Invoice': fields }, update=True)
	frappe.reload_doctype('Sales Invoice')