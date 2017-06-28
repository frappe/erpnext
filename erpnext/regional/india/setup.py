# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe, os, json
from frappe.custom.doctype.custom_field.custom_field import create_custom_field
from frappe.permissions import add_permission
from erpnext.regional.india import states

def setup(company=None, patch=True):
	make_custom_fields()
	add_permissions()
	add_custom_roles_for_reports()
	add_hsn_codes()
	update_address_template()
	if not patch:
		make_fixtures()

def update_address_template():
	with open(os.path.join(os.path.dirname(__file__), 'address_template.html'), 'r') as f:
		html = f.read()

	address_template = frappe.db.get_value('Address Template', 'India')
	if address_template:
		frappe.db.set_value('Address Template', 'India', 'template', html)
	else:
		# make new html template for India
		frappe.get_doc(dict(
			doctype='Address Template',
			country='India',
			template=html
		)).insert()

def add_hsn_codes():
	if frappe.db.count('GST HSN Code') > 100:
		return

	with open(os.path.join(os.path.dirname(__file__), 'hsn_code_data.json'), 'r') as f:
		hsn_codes = json.loads(f.read())

	frappe.db.commit()
	frappe.db.sql('truncate `tabGST HSN Code`')

	for d in hsn_codes:
		hsn_code = frappe.new_doc('GST HSN Code')
		hsn_code.update(d)
		hsn_code.name = hsn_code.hsn_code
		hsn_code.db_insert()

	frappe.db.commit()

def add_custom_roles_for_reports():
	for report_name in ('GST Sales Register', 'GST Purchase Register',
		'GST Itemised Sales Register', 'GST Itemised Purchase Register'):

		if not frappe.db.get_value('Custom Role', dict(report=report_name)):
			frappe.get_doc(dict(
				doctype='Custom Role',
				report=report_name,
				roles= [
					dict(role='Accounts User'),
					dict(role='Accounts Manager')
				]
			)).insert()

def add_permissions():
	for doctype in ('GST HSN Code', 'GST Settings'):
		add_permission(doctype, 'Accounts Manager', 0)
		add_permission(doctype, 'All', 0)

def make_custom_fields():
	custom_fields = {
		'Address': [
			dict(fieldname='gstin', label='Party GSTIN', fieldtype='Data',
				insert_after='fax'),
			dict(fieldname='gst_state', label='GST State', fieldtype='Select',
				options='\n'.join(states), insert_after='gstin')
		],
		'Purchase Invoice': [
			dict(fieldname='supplier_gstin', label='Supplier GSTIN',
				fieldtype='Data', insert_after='supplier_address',
				options='supplier_address.gstin'),
			dict(fieldname='company_gstin', label='Company GSTIN',
				fieldtype='Data', insert_after='shipping_address',
				options='shipping_address.gstin'),
		],
		'Sales Invoice': [
			dict(fieldname='customer_gstin', label='Customer GSTIN',
				fieldtype='Data', insert_after='shipping_address',
				options='shipping_address_name.gstin'),
			dict(fieldname='company_gstin', label='Company GSTIN',
				fieldtype='Data', insert_after='company_address',
				options='company_address.gstin'),
		],
		'Item': [
			dict(fieldname='gst_hsn_code', label='GST HSN Code',
				fieldtype='Link', options='GST HSN Code', insert_after='item_group'),
		],
		'Sales Invoice Item': [
			dict(fieldname='gst_hsn_code', label='GST HSN Code',
				fieldtype='Data', options='item_code.gst_hsn_code',
				insert_after='income_account'),
		],
		'Purchase Invoice Item': [
			dict(fieldname='gst_hsn_code', label='GST HSN Code',
				fieldtype='Data', options='item_code.gst_hsn_code',
				insert_after='expense_account'),
		]
	}

	for doctype, fields in custom_fields.items():
		for df in fields:
			create_custom_field(doctype, df)

def make_fixtures():
	docs = [
		{'doctype': 'Salary Component', 'salary_component': 'Professional Tax', 'description': 'Professional Tax', 'type': 'Deduction'},
		{'doctype': 'Salary Component', 'salary_component': 'Provident Fund', 'description': 'Provident fund', 'type': 'Deduction'},
		{'doctype': 'Salary Component', 'salary_component': 'House Rent Allowance', 'description': 'House Rent Allowance', 'type': 'Earning'},
		{'doctype': 'Salary Component', 'salary_component': 'Basic', 'description': 'Basic', 'type': 'Earning'},
		{'doctype': 'Salary Component', 'salary_component': 'Arrear', 'description': 'Arrear', 'type': 'Earning'},
		{'doctype': 'Salary Component', 'salary_component': 'Leave Encashment', 'description': 'Leave Encashment', 'type': 'Earning'}
	]

	for d in docs:
		try:
			doc = frappe.get_doc(d)
			doc.flags.ignore_permissions = True
			doc.insert()
		except frappe.NameError:
			pass
