from __future__ import unicode_literals
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
	company = frappe.get_all('Company', filters = {'country': 'India'})
	if not company:
		return

	fields = [
		# rearrange transporter name
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
			'fieldname': 'transporter_address',
			'label': 'Transporter Address Name',
			'fieldtype': 'Link',
			'insert_after': 'transporter_col_break',
			'options': 'Address',
			'print_hide': 1
		},
		{
			'fieldname': 'transporter_address_display',
			'label': 'Transporter Address',
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
	]

	create_custom_fields({ 'Sales Invoice': fields }, update=True)