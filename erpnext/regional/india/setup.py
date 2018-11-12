# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe, os, json
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.permissions import add_permission
from erpnext.regional.india import states

def setup(company=None, patch=True):
	if not patch:
		update_address_template()
		make_fixtures()

# TODO: for all countries
def setup_company_independent_fixtures():
	make_custom_fields()
	add_permissions()
	add_custom_roles_for_reports()
	frappe.enqueue('erpnext.regional.india.setup.add_hsn_sac_codes', now=frappe.flags.in_test)
	add_print_formats()

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

def add_hsn_sac_codes():
	# HSN codes
	with open(os.path.join(os.path.dirname(__file__), 'hsn_code_data.json'), 'r') as f:
		hsn_codes = json.loads(f.read())

	create_hsn_codes(hsn_codes, code_field="hsn_code")

	# SAC Codes
	with open(os.path.join(os.path.dirname(__file__), 'sac_code_data.json'), 'r') as f:
		sac_codes = json.loads(f.read())
	create_hsn_codes(sac_codes, code_field="sac_code")

def create_hsn_codes(data, code_field):
	for d in data:
		hsn_code = frappe.new_doc('GST HSN Code')
		hsn_code.description = d["description"]
		hsn_code.hsn_code = d[code_field]
		hsn_code.name = d[code_field]
		try:
			hsn_code.db_insert()
		except frappe.DuplicateEntryError:
			pass

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
		add_permission(doctype, 'All', 0)

def add_print_formats():
	frappe.reload_doc("regional", "print_format", "gst_tax_invoice")
	frappe.reload_doc("accounts", "print_format", "gst_pos_invoice")

	frappe.db.sql(""" update `tabPrint Format` set disabled = 0 where
		name in('GST POS Invoice', 'GST Tax Invoice') """)

def make_custom_fields():
	hsn_sac_field = dict(fieldname='gst_hsn_code', label='HSN/SAC',
		fieldtype='Data', options='item_code.gst_hsn_code', insert_after='description',
		allow_on_submit=1, print_hide=1)
	invoice_gst_fields = [
		dict(fieldname='gst_section', label='GST Details', fieldtype='Section Break',
			insert_after='language', print_hide=1, collapsible=1),
		dict(fieldname='invoice_copy', label='Invoice Copy',
			fieldtype='Select', insert_after='gst_section', print_hide=1, allow_on_submit=1,
			options='Original for Recipient\nDuplicate for Transporter\nDuplicate for Supplier\nTriplicate for Supplier'),
		dict(fieldname='reverse_charge', label='Reverse Charge',
			fieldtype='Select', insert_after='invoice_copy', print_hide=1,
			options='Y\nN', default='N'),
		dict(fieldname='invoice_type', label='Invoice Type',
			fieldtype='Select', insert_after='invoice_copy', print_hide=1,
			options='Regular\nSEZ\nExport\nDeemed Export', default='Regular'),
		dict(fieldname='export_type', label='Export Type',
			fieldtype='Select', insert_after='invoice_type', print_hide=1,
			depends_on='eval:in_list(["SEZ", "Export", "Deemed Export"], doc.invoice_type)',
			options='\nWith Payment of Tax\nWithout Payment of Tax'),
		dict(fieldname='ecommerce_gstin', label='E-commerce GSTIN',
			fieldtype='Data', insert_after='export_type', print_hide=1),
		dict(fieldname='gst_col_break', fieldtype='Column Break', insert_after='ecommerce_gstin'),
		dict(fieldname='reason_for_issuing_document', label='Reason For Issuing document',
			fieldtype='Select', insert_after='gst_col_break', print_hide=1,
			depends_on='eval:doc.is_return==1',
			options='\n01-Sales Return\n02-Post Sale Discount\n03-Deficiency in services\n04-Correction in Invoice\n05-Change in POS\n06-Finalization of Provisional assessment\n07-Others')
	]

	purchase_invoice_gst_fields = [
			dict(fieldname='supplier_gstin', label='Supplier GSTIN',
				fieldtype='Data', insert_after='supplier_address',
				options='supplier_address.gstin', print_hide=1),
			dict(fieldname='company_gstin', label='Company GSTIN',
				fieldtype='Data', insert_after='shipping_address',
				options='shipping_address.gstin', print_hide=1),
			dict(fieldname='place_of_supply', label='Place of Supply',
				fieldtype='Data', insert_after='shipping_address',
				print_hide=1, read_only=0),
			dict(fieldname='eligibility_for_itc', label='Eligibility For ITC',
				fieldtype='Select', insert_after='reason_for_issuing_document', print_hide=1,
				options='input\ninput service\ncapital goods\nineligible', default="ineligible"),
			dict(fieldname='itc_integrated_tax', label='Availed ITC Integrated Tax',
				fieldtype='Data', insert_after='eligibility_for_itc', print_hide=1),
			dict(fieldname='itc_central_tax', label='Availed ITC Central Tax',
				fieldtype='Data', insert_after='itc_integrated_tax', print_hide=1),
			dict(fieldname='itc_state_tax', label='Availed ITC State/UT Tax',
				fieldtype='Data', insert_after='itc_central_tax', print_hide=1),
			dict(fieldname='itc_cess_amount', label='Availed ITC Cess',
				fieldtype='Data', insert_after='itc_state_tax', print_hide=1),
		]

	sales_invoice_gst_fields = [
			dict(fieldname='billing_address_gstin', label='Billing Address GSTIN',
				fieldtype='Data', insert_after='customer_address',
				options='customer_address.gstin', print_hide=1),
			dict(fieldname='customer_gstin', label='Customer GSTIN',
				fieldtype='Data', insert_after='shipping_address',
				options='shipping_address_name.gstin', print_hide=1),
			dict(fieldname='place_of_supply', label='Place of Supply',
				fieldtype='Data', insert_after='customer_gstin',
				print_hide=1, read_only=0),
			dict(fieldname='company_gstin', label='Company GSTIN',
				fieldtype='Data', insert_after='company_address',
				options='company_address.gstin', print_hide=1),
			dict(fieldname='port_code', label='Port Code',
				fieldtype='Data', insert_after='reason_for_issuing_document', print_hide=1,
				depends_on="eval:doc.invoice_type=='Export' "),
			dict(fieldname='shipping_bill_number', label=' Shipping Bill Number',
				fieldtype='Data', insert_after='port_code', print_hide=1,
				depends_on="eval:doc.invoice_type=='Export' "),
			dict(fieldname='shipping_bill_date', label='Shipping Bill Date',
				fieldtype='Date', insert_after='shipping_bill_number', print_hide=1,
				depends_on="eval:doc.invoice_type=='Export' ")
		]

	custom_fields = {
		'Address': [
			dict(fieldname='gstin', label='Party GSTIN', fieldtype='Data',
				insert_after='fax'),
			dict(fieldname='gst_state', label='GST State', fieldtype='Select',
				options='\n'.join(states), insert_after='gstin'),
			dict(fieldname='gst_state_number', label='GST State Number',
				fieldtype='Int', insert_after='gst_state', read_only=1),
		],
		'Purchase Invoice': invoice_gst_fields + purchase_invoice_gst_fields,
		'Sales Invoice': invoice_gst_fields + sales_invoice_gst_fields,
		"Delivery Note": sales_invoice_gst_fields,
		'Item': [
			dict(fieldname='gst_hsn_code', label='HSN/SAC',
				fieldtype='Link', options='GST HSN Code', insert_after='item_group'),
		],
		'Quotation Item': [hsn_sac_field],
		'Supplier Quotation Item': [hsn_sac_field],
		'Sales Order Item': [hsn_sac_field],
		'Delivery Note Item': [hsn_sac_field],
		'Sales Invoice Item': [hsn_sac_field],
		'Purchase Order Item': [hsn_sac_field],
		'Purchase Receipt Item': [hsn_sac_field],
		'Purchase Invoice Item': [hsn_sac_field]
	}

	create_custom_fields(custom_fields)

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
