# Copyright (c) 2013, FinByz Tech Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
import re
from frappe import _
from frappe.utils import nowdate

def execute(filters=None):
	if not filters: filters.setdefault('posting_date', [nowdate(), nowdate()])
	columns, data = [], []
	columns = get_columns()
	data = get_data(filters)
	return columns, data

def get_data(filters):
	
	conditions = get_conditions(filters)

	data = frappe.db.sql("""
		SELECT
			dn.name as dn_id, dn.posting_date, dn.company, dn.company_gstin, dn.customer, dn.customer_gstin, dni.item_code, dni.item_name, dni.description, dni.gst_hsn_code, dni.uom, dni.qty, dni.amount, dn.mode_of_transport, dn.distance, dn.transporter_name, dn.gst_transporter_id, dn.lr_no, dn.lr_date, dn.vehicle_no, dn.gst_vehicle_type, dn.company_address, dn.shipping_address_name
		FROM
			`tabDelivery Note` AS dn join `tabDelivery Note Item` AS dni on (dni.parent = dn.name)
		WHERE
			dn.docstatus < 2 
			%s """ % conditions, as_dict=1)

	unit = {
		'Bag': "BAGS",
		'Bottle': "BOTTLES",
		'Kg': "KILOGRAMS",
		'Liter': "LITERS",
		'Meter': "METERS",
		'Nos': "NUMBERS",
		'PKT': "PACKS",
		'Roll': "ROLLS",
		'Set': "SETS"
	}

	# Regular expression set to remove all the special characters 
	special_characters = "[$%^*()+\\[\]{};':\"\\|<>.?]"

	for row in data:
		set_defaults(row)
		set_taxes(row, filters)
		set_address_details(row, special_characters)
		
		# Eway Bill accepts date as dd/mm/yyyy and not dd-mm-yyyy
		row.posting_date = '/'.join(str(row.posting_date).replace("-", "/").split('/')[::-1])
		row.lr_date = '/'.join(str(row.lr_date).replace("-", "/").split('/')[::-1])

		if row.gst_vehicle_type == 'Over Dimensional Cargo (ODC)':
			row.gst_vehicle_type = 'ODC'

		row.item_name = re.sub(special_characters, " ", row.item_name)
		row.description = row.item_name

		row.uom = unit.get(row.uom, row.uom)

		# For removing special charactes and numbers from customer.
		row.customer = re.sub(special_characters[:-1] + "&0-9" + "]", "", row.customer)

	return data

def get_conditions(filters):
	
	conditions = ""

	conditions += filters.get('company') and " AND dn.company = '%s' " % filters.get('company') or ""
	conditions += filters.get('posting_date') and " AND dn.posting_date >= '%s' AND dn.posting_date <= '%s' " % (filters.get('posting_date')[0], filters.get('posting_date')[1]) or ""
	conditions += filters.get('delivery_note') and " AND dn.name = '%s' " % filters.get('delivery_note') or ""
	conditions += filters.get('customer') and " AND dn.customer = '%s' " % filters.get('customer').replace("'", "\'") or ""

	return conditions

def set_defaults(row):
	row.setdefault(u'supply_type', "Outward")
	row.setdefault(u'sub_type', "Supply")
	row.setdefault(u'doc_type', "Delivery Challan")

def set_address_details(row, special_characters):

	if row.get('company_address'):
		address_line1, address_line2, city, pincode, state = frappe.db.get_value("Address", row.get('company_address'), ['address_line1', 'address_line2', 'city', 'pincode', 'state'])

		row.update({'from_address_1': re.sub(special_characters, "", address_line1 or '')})
		row.update({'from_address_2': re.sub(special_characters, "", address_line2 or '')})
		row.update({'from_place': city and city.upper() or ''})
		row.update({'from_pin_code': pincode and pincode.replace(" ", "") or ''})
		row.update({'from_state': state and state.upper() or ''})
		row.update({'dispatch_state': row.from_state})
		
	if row.get('shipping_address_name'):
		address_line1, address_line2, city, pincode, state = frappe.db.get_value("Address", row.get('shipping_address_name'), ['address_line1', 'address_line2', 'city', 'pincode', 'state'])

		row.update({'to_address_1': re.sub(special_characters, "", address_line1 or '')})
		row.update({'to_address_2': re.sub(special_characters, "", address_line2 or '')})
		row.update({'to_place': city and city.upper() or ''})
		row.update({'to_pin_code': pincode and pincode.replace(" ", "") or ''})
		row.update({'to_state': state and state.upper() or ''})
		row.update({'ship_to_state': row.to_state})

def set_taxes(row, filters):
	taxes = frappe.get_list("Sales Taxes and Charges", 
				filters={
					'parent': row.dn_id
				}, 
				fields=('item_wise_tax_detail', 'account_head'))

	account_list = ["cgst_account", "sgst_account", "igst_account", "cess_account"]
	taxes_list = frappe.get_list("GST Account",
		filters={
			"parent": "GST Settings", 
			"company": filters.company
		},
		fields=account_list)

	item_tax_rate = {}

	for tax in taxes:
		item_wise_tax = json.loads(tax.item_wise_tax_detail)
		item_tax_rate[tax.account_head] = item_wise_tax.get(row.item_code)

	tax_rate = []

	tax = taxes_list[0]
	for key in account_list:
		if tax[key] not in item_tax_rate.keys():
			item_tax_rate[tax[key]] = [0.0, 0.0]

		tax_rate.append(str(item_tax_rate[tax[key]][0]))
		row.update({key[:5] + "amount": round(item_tax_rate.get(tax[key], 0.0)[1], 2)})
		item_tax_rate.pop(tax[key])

	row.amount = float(row.amount) + sum(i[1] for i in item_tax_rate.values())
	row.update({'tax_rate': '+'.join(tax_rate)})

def get_columns():
	columns = [
		{
			"fieldname": "supply_type",
			"label": _("Supply Type"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "sub_type",
			"label": _("Sub Type"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "doc_type",
			"label": _("Doc Type"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "dn_id",
			"label": _("Doc Name"),
			"fieldtype": "Link",
			"options": "Delivery Note",
			"width": 140
		},
		{
			"fieldname": "posting_date",
			"label": _("Doc Date"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "company",
			"label": _("From Party Name"),
			"fieldtype": "Link",
			"options": "Company",
			"width": 120
		},
		{
			"fieldname": "company_gstin",
			"label": _("From GSTIN"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "from_address_1",
			"label": _("From Address 1"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "from_address_2",
			"label": _("From Address 2"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "from_place",
			"label": _("From Place"),
			"fieldtype": "Data",
			"width": 80
		},
		{
			"fieldname": "from_pin_code",
			"label": _("From Pin Code"),
			"fieldtype": "Data",
			"width": 80
		},
		{
			"fieldname": "from_state",
			"label": _("From State"),
			"fieldtype": "Data",
			"width": 80
		},
		{
			"fieldname": "dispatch_state",
			"label": _("Dispatch State"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "customer",
			"label": _("To Party Name"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "customer_gstin",
			"label": _("To GSTIN"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "to_address_1",
			"label": _("To Address 1"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "to_address_2",
			"label": _("To Address 2"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "to_place",
			"label": _("To Place"),
			"fieldtype": "Data",
			"width": 80
		},
		{
			"fieldname": "to_pin_code",
			"label": _("To Pin Code"),
			"fieldtype": "Data",
			"width": 80
		},
		{
			"fieldname": "to_state",
			"label": _("To State"),
			"fieldtype": "Data",
			"width": 80
		},
		{
			"fieldname": "ship_to_state",
			"label": _("Ship To State"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "item_name",
			"label": _("Product"),
			"fieldtype": "Link",
			"options": "Item",
			"width": 120
		},
		{
			"fieldname": "description",
			"label": _("Description"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "gst_hsn_code",
			"label": _("HSN"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "uom",
			"label": _("Unit"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "qty",
			"label": _("Qty"),
			"fieldtype": "Float",
			"width": 100
		},
		{
			"fieldname": "amount",
			"label": _("Accessable Value"),
			"fieldtype": "Float",
			"width": 120
		},
		{
			"fieldname": "tax_rate",
			"label": _("Tax Rate"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "cgst_amount",
			"label": _("CGST Amount"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "sgst_amount",
			"label": _("SGST Amount"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "igst_amount",
			"label": _("IGST Amount"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "cess_amount",
			"label": _("CESS Amount"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "mode_of_transport",
			"label": _("Mode of Transport"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "distance",
			"label": _("Distance"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "transporter_name",
			"label": _("Transporter Name"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "gst_transporter_id",
			"label": _("Transporter ID"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "lr_no",
			"label": _("Transport Receipt No"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "lr_date",
			"label": _("Transport Receipt Date"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "vehicle_no",
			"label": _("Vehicle No"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "gst_vehicle_type",
			"label": _("Vehicle Type"),
			"fieldtype": "Data",
			"width": 100
		},
	]

	return columns