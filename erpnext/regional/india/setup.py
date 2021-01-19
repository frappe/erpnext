# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe, os, json
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.permissions import add_permission, update_permission_property
from erpnext.regional.india import states
from erpnext.accounts.utils import get_fiscal_year, FiscalYearError
from frappe.utils import today

def setup(company=None, patch=True):
	setup_company_independent_fixtures()
	if not patch:
		make_fixtures(company)

# TODO: for all countries
def setup_company_independent_fixtures():
	make_custom_fields()
	add_permissions()
	add_custom_roles_for_reports()
	frappe.enqueue('erpnext.regional.india.setup.add_hsn_sac_codes', now=frappe.flags.in_test)
	add_print_formats()

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
		'GST Itemised Sales Register', 'GST Itemised Purchase Register', 'Eway Bill'):

		if not frappe.db.get_value('Custom Role', dict(report=report_name)):
			frappe.get_doc(dict(
				doctype='Custom Role',
				report=report_name,
				roles= [
					dict(role='Accounts User'),
					dict(role='Accounts Manager')
				]
			)).insert()

	for report_name in ('Professional Tax Deductions', 'Provident Fund Deductions'):

		if not frappe.db.get_value('Custom Role', dict(report=report_name)):
			frappe.get_doc(dict(
				doctype='Custom Role',
				report=report_name,
				roles= [
					dict(role='HR User'),
					dict(role='HR Manager'),
					dict(role='Employee')
				]
			)).insert()

	for report_name in ('HSN-wise-summary of outward supplies', 'GSTR-1', 'GSTR-2'):

		if not frappe.db.get_value('Custom Role', dict(report=report_name)):
			frappe.get_doc(dict(
				doctype='Custom Role',
				report=report_name,
				roles= [
					dict(role='Accounts User'),
					dict(role='Accounts Manager'),
					dict(role='Auditor')
				]
			)).insert()

def add_permissions():
	for doctype in ('GST HSN Code', 'GST Settings', 'GSTR 3B Report', 'Lower Deduction Certificate', 'E Invoice Settings'):
		add_permission(doctype, 'All', 0)
		for role in ('Accounts Manager', 'Accounts User', 'System Manager'):
			add_permission(doctype, role, 0)
			update_permission_property(doctype, role, 0, 'write', 1)
			update_permission_property(doctype, role, 0, 'create', 1)

		if doctype == 'GST HSN Code':
			for role in ('Item Manager', 'Stock Manager'):
				add_permission(doctype, role, 0)
				update_permission_property(doctype, role, 0, 'write', 1)
				update_permission_property(doctype, role, 0, 'create', 1)

def add_print_formats():
	frappe.reload_doc("regional", "print_format", "gst_tax_invoice")
	frappe.reload_doc("accounts", "print_format", "gst_pos_invoice")
	frappe.reload_doc("accounts", "print_format", "GST E-Invoice")

	frappe.db.sql(""" update `tabPrint Format` set disabled = 0 where
		name in('GST POS Invoice', 'GST Tax Invoice', 'GST E-Invoice') """)

def make_custom_fields(update=True):
	hsn_sac_field = dict(fieldname='gst_hsn_code', label='HSN/SAC',
		fieldtype='Data', fetch_from='item_code.gst_hsn_code', insert_after='description',
		allow_on_submit=1, print_hide=1, fetch_if_empty=1)
	nil_rated_exempt = dict(fieldname='is_nil_exempt', label='Is Nil Rated or Exempted',
		fieldtype='Check', fetch_from='item_code.is_nil_exempt', insert_after='gst_hsn_code',
		print_hide=1)
	is_non_gst = dict(fieldname='is_non_gst', label='Is Non GST',
		fieldtype='Check', fetch_from='item_code.is_non_gst', insert_after='is_nil_exempt',
		print_hide=1)

	purchase_invoice_gst_category = [
		dict(fieldname='gst_section', label='GST Details', fieldtype='Section Break',
			insert_after='language', print_hide=1, collapsible=1),
		dict(fieldname='gst_category', label='GST Category',
			fieldtype='Select', insert_after='gst_section', print_hide=1,
			options='\nRegistered Regular\nRegistered Composition\nUnregistered\nSEZ\nOverseas\nUIN Holders',
			fetch_from='supplier.gst_category', fetch_if_empty=1),
		dict(fieldname='export_type', label='Export Type',
			fieldtype='Select', insert_after='gst_category', print_hide=1,
			depends_on='eval:in_list(["SEZ", "Overseas"], doc.gst_category)',
			options='\nWith Payment of Tax\nWithout Payment of Tax', fetch_from='supplier.export_type',
			fetch_if_empty=1),
	]

	sales_invoice_gst_category = [
		dict(fieldname='gst_section', label='GST Details', fieldtype='Section Break',
			insert_after='language', print_hide=1, collapsible=1),
		dict(fieldname='gst_category', label='GST Category',
			fieldtype='Select', insert_after='gst_section', print_hide=1,
			options='\nRegistered Regular\nRegistered Composition\nUnregistered\nSEZ\nOverseas\nConsumer\nDeemed Export\nUIN Holders',
			fetch_from='customer.gst_category', fetch_if_empty=1),
		dict(fieldname='export_type', label='Export Type',
			fieldtype='Select', insert_after='gst_category', print_hide=1,
			depends_on='eval:in_list(["SEZ", "Overseas", "Deemed Export"], doc.gst_category)',
			options='\nWith Payment of Tax\nWithout Payment of Tax', fetch_from='customer.export_type',
			fetch_if_empty=1),
	]

	invoice_gst_fields = [
		dict(fieldname='invoice_copy', label='Invoice Copy',
			fieldtype='Select', insert_after='export_type', print_hide=1, allow_on_submit=1,
			options='Original for Recipient\nDuplicate for Transporter\nDuplicate for Supplier\nTriplicate for Supplier'),
		dict(fieldname='reverse_charge', label='Reverse Charge',
			fieldtype='Select', insert_after='invoice_copy', print_hide=1,
			options='Y\nN', default='N'),
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
				fetch_from='supplier_address.gstin', print_hide=1, read_only=1),
			dict(fieldname='company_gstin', label='Company GSTIN',
				fieldtype='Data', insert_after='shipping_address_display',
				fetch_from='shipping_address.gstin', print_hide=1, read_only=1),
			dict(fieldname='place_of_supply', label='Place of Supply',
				fieldtype='Data', insert_after='shipping_address',
				print_hide=1, read_only=1),
		]

	purchase_invoice_itc_fields = [
			dict(fieldname='eligibility_for_itc', label='Eligibility For ITC',
				fieldtype='Select', insert_after='reason_for_issuing_document', print_hide=1,
				options='Input Service Distributor\nImport Of Service\nImport Of Capital Goods\nIneligible\nAll Other ITC', default="All Other ITC"),
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
				fieldtype='Data', insert_after='customer_address', read_only=1,
				fetch_from='customer_address.gstin', print_hide=1),
			dict(fieldname='customer_gstin', label='Customer GSTIN',
				fieldtype='Data', insert_after='shipping_address_name',
				fetch_from='shipping_address_name.gstin', print_hide=1),
			dict(fieldname='place_of_supply', label='Place of Supply',
				fieldtype='Data', insert_after='customer_gstin',
				print_hide=1, read_only=1),
			dict(fieldname='company_gstin', label='Company GSTIN',
				fieldtype='Data', insert_after='company_address',
				fetch_from='company_address.gstin', print_hide=1, read_only=1),
		]

	sales_invoice_shipping_fields = [
			dict(fieldname='port_code', label='Port Code',
				fieldtype='Data', insert_after='reason_for_issuing_document', print_hide=1,
				depends_on="eval:doc.gst_category=='Overseas' "),
			dict(fieldname='shipping_bill_number', label=' Shipping Bill Number',
				fieldtype='Data', insert_after='port_code', print_hide=1,
				depends_on="eval:doc.gst_category=='Overseas' "),
			dict(fieldname='shipping_bill_date', label='Shipping Bill Date',
				fieldtype='Date', insert_after='shipping_bill_number', print_hide=1,
				depends_on="eval:doc.gst_category=='Overseas' "),
		]

	inter_state_gst_field = [
		dict(fieldname='is_inter_state', label='Is Inter State',
			fieldtype='Check', insert_after='disabled', print_hide=1),
		dict(fieldname='tax_category_column_break', fieldtype='Column Break',
			insert_after='is_inter_state'),
		dict(fieldname='gst_state', label='Source State', fieldtype='Select',
			options='\n'.join(states), insert_after='company')
	]

	ewaybill_fields = [
		{
			'fieldname': 'distance',
			'label': 'Distance (in km)',
			'fieldtype': 'Float',
			'insert_after': 'vehicle_no',
			'print_hide': 1
		},
		{
			'fieldname': 'gst_transporter_id',
			'label': 'GST Transporter ID',
			'fieldtype': 'Data',
			'insert_after': 'transporter',
			'fetch_from': 'transporter.gst_transporter_id',
			'print_hide': 1,
			'translatable': 0
		},
		{
			'fieldname': 'mode_of_transport',
			'label': 'Mode of Transport',
			'fieldtype': 'Select',
			'options': '\nRoad\nAir\nRail\nShip',
			'default': 'Road',
			'insert_after': 'transporter_name',
			'print_hide': 1,
			'translatable': 0
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
			'label': 'E-Way Bill No.',
			'fieldtype': 'Data',
			'depends_on': 'eval:(doc.docstatus === 1)',
			'allow_on_submit': 1,
			'insert_after': 'customer_name_in_arabic',
			'translatable': 0,
    	}
	]

	si_ewaybill_fields = [
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
			'fieldname': 'gst_transporter_id',
			'label': 'GST Transporter ID',
			'fieldtype': 'Data',
			'insert_after': 'transporter',
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
			'fieldname': 'transporter_name',
			'label': 'Transporter Name',
			'fieldtype': 'Data',
			'insert_after': 'transporter_col_break',
			'fetch_from': 'transporter.name',
			'read_only': 1,
			'print_hide': 1,
			'translatable': 0
		},
		{
			'fieldname': 'mode_of_transport',
			'label': 'Mode of Transport',
			'fieldtype': 'Select',
			'options': '\nRoad\nAir\nRail\nShip',
			'insert_after': 'transporter_name',
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
			'label': 'E-Way Bill No.',
			'fieldtype': 'Data',
			'depends_on': 'eval:((doc.docstatus === 1 || doc.ewaybill) && doc.eway_bill_cancelled === 0)',
			'allow_on_submit': 1,
			'insert_after': 'tax_id',
			'translatable': 0
		}
	]

	si_einvoice_fields = [
		dict(fieldname='irn', label='IRN', fieldtype='Data', read_only=1, insert_after='customer', no_copy=1, print_hide=1,
			depends_on='eval:in_list(["Registered Regular", "SEZ", "Overseas", "Deemed Export"], doc.gst_category) && doc.irn_cancelled === 0'),
		
		dict(fieldname='ack_no', label='Ack. No.', fieldtype='Data', read_only=1, hidden=1, insert_after='irn', no_copy=1, print_hide=1),
		
		dict(fieldname='ack_date', label='Ack. Date', fieldtype='Data', read_only=1, hidden=1, insert_after='ack_no', no_copy=1, print_hide=1),

		dict(fieldname='irn_cancelled', label='IRN Cancelled', fieldtype='Check', no_copy=1, print_hide=1,
			depends_on='eval:(doc.irn_cancelled === 1)', read_only=1, allow_on_submit=1, insert_after='customer'),

		dict(fieldname='eway_bill_cancelled', label='E-Way Bill Cancelled', fieldtype='Check', no_copy=1, print_hide=1,
			depends_on='eval:(doc.eway_bill_cancelled === 1)', read_only=1, allow_on_submit=1, insert_after='customer'),

		dict(fieldname='signed_einvoice', fieldtype='Code', options='JSON', hidden=1, no_copy=1, print_hide=1, read_only=1),

		dict(fieldname='signed_qr_code', fieldtype='Code', options='JSON', hidden=1, no_copy=1, print_hide=1, read_only=1),

		dict(fieldname='qrcode_image', label='QRCode', fieldtype='Attach Image', hidden=1, no_copy=1, print_hide=1, read_only=1)
	]

	custom_fields = {
		'Address': [
			dict(fieldname='gstin', label='Party GSTIN', fieldtype='Data',
				insert_after='fax'),
			dict(fieldname='gst_state', label='GST State', fieldtype='Select',
				options='\n'.join(states), insert_after='gstin'),
			dict(fieldname='gst_state_number', label='GST State Number',
				fieldtype='Data', insert_after='gst_state', read_only=1),
		],
		'Purchase Invoice': purchase_invoice_gst_category + invoice_gst_fields + purchase_invoice_itc_fields + purchase_invoice_gst_fields,
		'Purchase Order': purchase_invoice_gst_fields,
		'Purchase Receipt': purchase_invoice_gst_fields,
		'Sales Invoice': sales_invoice_gst_category + invoice_gst_fields + sales_invoice_shipping_fields + sales_invoice_gst_fields + si_ewaybill_fields + si_einvoice_fields,
		'Delivery Note': sales_invoice_gst_fields + ewaybill_fields + sales_invoice_shipping_fields,
		'Sales Order': sales_invoice_gst_fields,
		'Tax Category': inter_state_gst_field,
		'Item': [
			dict(fieldname='gst_hsn_code', label='HSN/SAC',
				fieldtype='Link', options='GST HSN Code', insert_after='item_group'),
			dict(fieldname='is_nil_exempt', label='Is Nil Rated or Exempted',
				fieldtype='Check', insert_after='gst_hsn_code'),
			dict(fieldname='is_non_gst', label='Is Non GST ',
				fieldtype='Check', insert_after='is_nil_exempt')
		],
		'Quotation Item': [hsn_sac_field, nil_rated_exempt, is_non_gst],
		'Supplier Quotation Item': [hsn_sac_field, nil_rated_exempt, is_non_gst],
		'Sales Order Item': [hsn_sac_field, nil_rated_exempt, is_non_gst],
		'Delivery Note Item': [hsn_sac_field, nil_rated_exempt, is_non_gst],
		'Sales Invoice Item': [hsn_sac_field, nil_rated_exempt, is_non_gst],
		'Purchase Order Item': [hsn_sac_field, nil_rated_exempt, is_non_gst],
		'Purchase Receipt Item': [hsn_sac_field, nil_rated_exempt, is_non_gst],
		'Purchase Invoice Item': [hsn_sac_field, nil_rated_exempt, is_non_gst],
		'Material Request Item': [hsn_sac_field, nil_rated_exempt, is_non_gst],
		'Salary Component': [
			dict(fieldname=  'component_type',
				label= 'Component Type',
				fieldtype=  'Select',
				insert_after= 'description',
				options= "\nProvident Fund\nAdditional Provident Fund\nProvident Fund Loan\nProfessional Tax",
				depends_on = 'eval:doc.type == "Deduction"'
			)
		],
		'Employee': [
			dict(fieldname='ifsc_code',
				label='IFSC Code',
				fieldtype='Data',
				insert_after='bank_ac_no',
				print_hide=1,
				depends_on='eval:doc.salary_mode == "Bank"'
				),
			dict(
				fieldname =  'pan_number',
				label = 'PAN Number',
				fieldtype = 'Data',
				insert_after = 'payroll_cost_center',
				print_hide = 1
			),
			dict(
				fieldname =  'micr_code',
				label = 'MICR Code',
				fieldtype = 'Data',
				insert_after = 'ifsc_code',
				print_hide = 1,
				depends_on='eval:doc.salary_mode == "Bank"'
			),
			dict(
				fieldname = 'provident_fund_account',
				label = 'Provident Fund Account',
				fieldtype = 'Data',
				insert_after = 'pan_number'
			)

		],
		'Company': [
			dict(fieldname='hra_section', label='HRA Settings',
				fieldtype='Section Break', insert_after='asset_received_but_not_billed', collapsible=1),
			dict(fieldname='basic_component', label='Basic Component',
				fieldtype='Link', options='Salary Component', insert_after='hra_section'),
			dict(fieldname='hra_component', label='HRA Component',
				fieldtype='Link', options='Salary Component', insert_after='basic_component'),
			dict(fieldname='arrear_component', label='Arrear Component',
				fieldtype='Link', options='Salary Component', insert_after='hra_component'),
		],
		'Employee Tax Exemption Declaration':[
			dict(fieldname='hra_section', label='HRA Exemption',
				fieldtype='Section Break', insert_after='declarations'),
			dict(fieldname='monthly_house_rent', label='Monthly House Rent',
				fieldtype='Currency', insert_after='hra_section'),
			dict(fieldname='rented_in_metro_city', label='Rented in Metro City',
				fieldtype='Check', insert_after='monthly_house_rent', depends_on='monthly_house_rent'),
			dict(fieldname='salary_structure_hra', label='HRA as per Salary Structure',
				fieldtype='Currency', insert_after='rented_in_metro_city', read_only=1, depends_on='monthly_house_rent'),
			dict(fieldname='hra_column_break', fieldtype='Column Break',
				insert_after='salary_structure_hra', depends_on='monthly_house_rent'),
			dict(fieldname='annual_hra_exemption', label='Annual HRA Exemption',
				fieldtype='Currency', insert_after='hra_column_break', read_only=1, depends_on='monthly_house_rent'),
			dict(fieldname='monthly_hra_exemption', label='Monthly HRA Exemption',
				fieldtype='Currency', insert_after='annual_hra_exemption', read_only=1, depends_on='monthly_house_rent')
		],
		'Employee Tax Exemption Proof Submission': [
			dict(fieldname='hra_section', label='HRA Exemption',
				fieldtype='Section Break', insert_after='tax_exemption_proofs'),
			dict(fieldname='house_rent_payment_amount', label='House Rent Payment Amount',
				fieldtype='Currency', insert_after='hra_section'),
			dict(fieldname='rented_in_metro_city', label='Rented in Metro City',
				fieldtype='Check', insert_after='house_rent_payment_amount', depends_on='house_rent_payment_amount'),
			dict(fieldname='rented_from_date', label='Rented From Date',
				fieldtype='Date', insert_after='rented_in_metro_city', depends_on='house_rent_payment_amount'),
			dict(fieldname='rented_to_date', label='Rented To Date',
				fieldtype='Date', insert_after='rented_from_date', depends_on='house_rent_payment_amount'),
			dict(fieldname='hra_column_break', fieldtype='Column Break',
				insert_after='rented_to_date', depends_on='house_rent_payment_amount'),
			dict(fieldname='monthly_house_rent', label='Monthly House Rent',
				fieldtype='Currency', insert_after='hra_column_break', read_only=1, depends_on='house_rent_payment_amount'),
			dict(fieldname='monthly_hra_exemption', label='Monthly Eligible Amount',
				fieldtype='Currency', insert_after='monthly_house_rent', read_only=1, depends_on='house_rent_payment_amount'),
			dict(fieldname='total_eligible_hra_exemption', label='Total Eligible HRA Exemption',
				fieldtype='Currency', insert_after='monthly_hra_exemption', read_only=1, depends_on='house_rent_payment_amount')
		],
		'Supplier': [
			{
				'fieldname': 'gst_transporter_id',
				'label': 'GST Transporter ID',
				'fieldtype': 'Data',
				'insert_after': 'supplier_type',
				'depends_on': 'eval:doc.is_transporter'
			},
			{
				'fieldname': 'gst_category',
				'label': 'GST Category',
				'fieldtype': 'Select',
				'insert_after': 'gst_transporter_id',
				'options': 'Registered Regular\nRegistered Composition\nUnregistered\nSEZ\nOverseas\nUIN Holders',
				'default': 'Unregistered'
			},
			{
				'fieldname': 'export_type',
				'label': 'Export Type',
				'fieldtype': 'Select',
				'insert_after': 'gst_category',
				'default': 'Without Payment of Tax',
				'depends_on':'eval:in_list(["SEZ", "Overseas"], doc.gst_category)',
				'options': '\nWith Payment of Tax\nWithout Payment of Tax'
			}
		],
		'Customer': [
			{
				'fieldname': 'gst_category',
				'label': 'GST Category',
				'fieldtype': 'Select',
				'insert_after': 'customer_type',
				'options': 'Registered Regular\nRegistered Composition\nUnregistered\nSEZ\nOverseas\nConsumer\nDeemed Export\nUIN Holders',
				'default': 'Unregistered'
			},
			{
				'fieldname': 'export_type',
				'label': 'Export Type',
				'fieldtype': 'Select',
				'insert_after': 'gst_category',
				'default': 'Without Payment of Tax',
				'depends_on':'eval:in_list(["SEZ", "Overseas", "Deemed Export"], doc.gst_category)',
				'options': '\nWith Payment of Tax\nWithout Payment of Tax'
			}
		],
		"Member": [
			{
				'fieldname': 'pan_number',
				'label': 'PAN Details',
				'fieldtype': 'Data',
				'insert_after': 'email'
			}
		]
	}
	create_custom_fields(custom_fields, update=update)

def make_fixtures(company=None):
	docs = []
	company = company.name if company else frappe.db.get_value("Global Defaults", None, "default_company")

	set_salary_components(docs)
	set_tds_account(docs, company)

	for d in docs:
		try:
			doc = frappe.get_doc(d)
			doc.flags.ignore_permissions = True
			doc.insert()
		except frappe.NameError:
			frappe.clear_messages()
		except frappe.DuplicateEntryError:
			frappe.clear_messages()

	# create records for Tax Withholding Category
	set_tax_withholding_category(company)

def set_salary_components(docs):
	docs.extend([
		{'doctype': 'Salary Component', 'salary_component': 'Professional Tax',
			'description': 'Professional Tax', 'type': 'Deduction', 'exempted_from_income_tax': 1},
		{'doctype': 'Salary Component', 'salary_component': 'Provident Fund',
			'description': 'Provident fund', 'type': 'Deduction', 'is_tax_applicable': 1},
		{'doctype': 'Salary Component', 'salary_component': 'House Rent Allowance',
			'description': 'House Rent Allowance', 'type': 'Earning', 'is_tax_applicable': 1},
		{'doctype': 'Salary Component', 'salary_component': 'Basic',
			'description': 'Basic', 'type': 'Earning', 'is_tax_applicable': 1},
		{'doctype': 'Salary Component', 'salary_component': 'Arrear',
			'description': 'Arrear', 'type': 'Earning', 'is_tax_applicable': 1},
		{'doctype': 'Salary Component', 'salary_component': 'Leave Encashment',
			'description': 'Leave Encashment', 'type': 'Earning', 'is_tax_applicable': 1}
	])

def set_tax_withholding_category(company):
	accounts = []
	fiscal_year = None
	abbr = frappe.get_value("Company", company, "abbr")
	tds_account = frappe.get_value("Account", 'TDS Payable - {0}'.format(abbr), 'name')

	if company and tds_account:
		accounts = [dict(company=company, account=tds_account)]

	try:
		fiscal_year = get_fiscal_year(today(), verbose=0, company=company)[0]
	except FiscalYearError:
		pass

	docs = get_tds_details(accounts, fiscal_year)
	
	for d in docs:
		try:
			doc = frappe.get_doc(d)
			doc.flags.ignore_permissions = True
			doc.flags.ignore_mandatory = True
			doc.insert()
		except frappe.DuplicateEntryError:
			doc = frappe.get_doc("Tax Withholding Category", d.get("name"))

			if accounts:
				doc.append("accounts", accounts[0])

			if fiscal_year:
				# if fiscal year don't match with any of the already entered data, append rate row
				fy_exist = [k for k in doc.get('rates') if k.get('fiscal_year')==fiscal_year]
				if not fy_exist:
					doc.append("rates", d.get('rates')[0])
					
			doc.flags.ignore_permissions = True
			doc.flags.ignore_mandatory = True
			doc.save()

def set_tds_account(docs, company):
	abbr = frappe.get_value("Company", company, "abbr")
	parent_account = frappe.db.get_value("Account", filters = {"account_name": "Duties and Taxes", "company": company})
	if parent_account:
		docs.extend([
			{
				"doctype": "Account",
				"account_name": "TDS Payable",
				"account_type": "Tax",
				"parent_account": parent_account,
				"company": company
			}
		])

def get_tds_details(accounts, fiscal_year):
	# bootstrap default tax withholding sections
	return [
		dict(name="TDS - 194C - Company",
			category_name="Payment to Contractors (Single / Aggregate)",
			doctype="Tax Withholding Category", accounts=accounts,
			rates=[{"fiscal_year": fiscal_year, "tax_withholding_rate": 2,
			"single_threshold": 30000, "cumulative_threshold": 100000}]),
		dict(name="TDS - 194C - Individual",
			category_name="Payment to Contractors (Single / Aggregate)",
			doctype="Tax Withholding Category", accounts=accounts,
			rates=[{"fiscal_year": fiscal_year, "tax_withholding_rate": 1,
			"single_threshold": 30000, "cumulative_threshold": 100000}]),
		dict(name="TDS - 194C - No PAN / Invalid PAN",
			category_name="Payment to Contractors (Single / Aggregate)",
			doctype="Tax Withholding Category", accounts=accounts,
			rates=[{"fiscal_year": fiscal_year, "tax_withholding_rate": 20,
			"single_threshold": 30000, "cumulative_threshold": 100000}]),
		dict(name="TDS - 194D - Company",
			category_name="Insurance Commission",
			doctype="Tax Withholding Category", accounts=accounts,
			rates=[{"fiscal_year": fiscal_year, "tax_withholding_rate": 5,
			"single_threshold": 15000, "cumulative_threshold": 0}]),
		dict(name="TDS - 194D - Company Assessee",
			category_name="Insurance Commission",
			doctype="Tax Withholding Category", accounts=accounts,
			rates=[{"fiscal_year": fiscal_year, "tax_withholding_rate": 10,
			"single_threshold": 15000, "cumulative_threshold": 0}]),
		dict(name="TDS - 194D - Individual",
			category_name="Insurance Commission",
			doctype="Tax Withholding Category", accounts=accounts,
			rates=[{"fiscal_year": fiscal_year, "tax_withholding_rate": 5,
			"single_threshold": 15000, "cumulative_threshold": 0}]),
		dict(name="TDS - 194D - No PAN / Invalid PAN",
			category_name="Insurance Commission",
			doctype="Tax Withholding Category", accounts=accounts,
			rates=[{"fiscal_year": fiscal_year, "tax_withholding_rate": 20,
			"single_threshold": 15000, "cumulative_threshold": 0}]),
		dict(name="TDS - 194DA - Company",
			category_name="Non-exempt payments made under a life insurance policy",
			doctype="Tax Withholding Category", accounts=accounts,
			rates=[{"fiscal_year": fiscal_year, "tax_withholding_rate": 1,
			"single_threshold": 100000, "cumulative_threshold": 0}]),
		dict(name="TDS - 194DA - Individual",
			category_name="Non-exempt payments made under a life insurance policy",
			doctype="Tax Withholding Category", accounts=accounts,
			rates=[{"fiscal_year": fiscal_year, "tax_withholding_rate": 1,
			"single_threshold": 100000, "cumulative_threshold": 0}]),
		dict(name="TDS - 194DA - No PAN / Invalid PAN",
			category_name="Non-exempt payments made under a life insurance policy",
			doctype="Tax Withholding Category", accounts=accounts,
			rates=[{"fiscal_year": fiscal_year, "tax_withholding_rate": 20,
			"single_threshold": 100000, "cumulative_threshold": 0}]),
		dict(name="TDS - 194H - Company",
			category_name="Commission / Brokerage",
			doctype="Tax Withholding Category", accounts=accounts,
			rates=[{"fiscal_year": fiscal_year, "tax_withholding_rate": 5,
			"single_threshold": 15000, "cumulative_threshold": 0}]),
		dict(name="TDS - 194H - Individual",
			category_name="Commission / Brokerage",
			doctype="Tax Withholding Category", accounts=accounts,
			rates=[{"fiscal_year": fiscal_year, "tax_withholding_rate": 5,
			"single_threshold": 15000, "cumulative_threshold": 0}]),
		dict(name="TDS - 194H - No PAN / Invalid PAN",
			category_name="Commission / Brokerage",
			doctype="Tax Withholding Category", accounts=accounts,
			rates=[{"fiscal_year": fiscal_year, "tax_withholding_rate": 20,
			"single_threshold": 15000, "cumulative_threshold": 0}]),
		dict(name="TDS - 194I - Rent - Company",
			category_name="Rent",
			doctype="Tax Withholding Category", accounts=accounts,
			rates=[{"fiscal_year": fiscal_year, "tax_withholding_rate": 10,
			"single_threshold": 180000, "cumulative_threshold": 0}]),
		dict(name="TDS - 194I - Rent - Individual",
			category_name="Rent",
			doctype="Tax Withholding Category", accounts=accounts,
			rates=[{"fiscal_year": fiscal_year, "tax_withholding_rate": 10,
			"single_threshold": 180000, "cumulative_threshold": 0}]),
		dict(name="TDS - 194I - Rent - No PAN / Invalid PAN",
			category_name="Rent",
			doctype="Tax Withholding Category", accounts=accounts,
			rates=[{"fiscal_year": fiscal_year, "tax_withholding_rate": 20,
			"single_threshold": 180000, "cumulative_threshold": 0}]),
		dict(name="TDS - 194I - Rent/Machinery - Company",
			category_name="Rent-Plant / Machinery",
			doctype="Tax Withholding Category", accounts=accounts,
			rates=[{"fiscal_year": fiscal_year, "tax_withholding_rate": 2,
			"single_threshold": 180000, "cumulative_threshold": 0}]),
		dict(name="TDS - 194I - Rent/Machinery - Individual",
			category_name="Rent-Plant / Machinery",
			doctype="Tax Withholding Category", accounts=accounts,
			rates=[{"fiscal_year": fiscal_year, "tax_withholding_rate": 2,
			"single_threshold": 180000, "cumulative_threshold": 0}]),
		dict(name="TDS - 194I - Rent/Machinery - No PAN / Invalid PAN",
			category_name="Rent-Plant / Machinery",
			doctype="Tax Withholding Category", accounts=accounts,
			rates=[{"fiscal_year": fiscal_year, "tax_withholding_rate": 20,
			"single_threshold": 180000, "cumulative_threshold": 0}]),
		dict(name="TDS - 194J - Professional Fees - Company",
			category_name="Professional Fees",
			doctype="Tax Withholding Category", accounts=accounts,
			rates=[{"fiscal_year": fiscal_year, "tax_withholding_rate": 10,
			"single_threshold": 30000, "cumulative_threshold": 0}]),
		dict(name="TDS - 194J - Professional Fees - Individual",
			category_name="Professional Fees",
			doctype="Tax Withholding Category", accounts=accounts,
			rates=[{"fiscal_year": fiscal_year, "tax_withholding_rate": 10,
			"single_threshold": 30000, "cumulative_threshold": 0}]),
		dict(name="TDS - 194J - Professional Fees - No PAN / Invalid PAN",
			category_name="Professional Fees",
			doctype="Tax Withholding Category", accounts=accounts,
			rates=[{"fiscal_year": fiscal_year, "tax_withholding_rate": 20,
			"single_threshold": 30000, "cumulative_threshold": 0}]),
		dict(name="TDS - 194J - Director Fees - Company",
			category_name="Director Fees",
			doctype="Tax Withholding Category", accounts=accounts,
			rates=[{"fiscal_year": fiscal_year, "tax_withholding_rate": 10,
			"single_threshold": 0, "cumulative_threshold": 0}]),
		dict(name="TDS - 194J - Director Fees - Individual",
			category_name="Director Fees",
			doctype="Tax Withholding Category", accounts=accounts,
			rates=[{"fiscal_year": fiscal_year, "tax_withholding_rate": 10,
			"single_threshold": 0, "cumulative_threshold": 0}]),
		dict(name="TDS - 194J - Director Fees - No PAN / Invalid PAN",
			category_name="Director Fees",
			doctype="Tax Withholding Category", accounts=accounts,
			rates=[{"fiscal_year": fiscal_year, "tax_withholding_rate": 20,
			"single_threshold": 0, "cumulative_threshold": 0}]),
		dict(name="TDS - 194 - Dividends - Company",
			category_name="Dividends",
			doctype="Tax Withholding Category", accounts=accounts,
			rates=[{"fiscal_year": fiscal_year, "tax_withholding_rate": 10,
			"single_threshold": 2500, "cumulative_threshold": 0}]),
		dict(name="TDS - 194 - Dividends - Individual",
			category_name="Dividends",
			doctype="Tax Withholding Category", accounts=accounts,
			rates=[{"fiscal_year": fiscal_year, "tax_withholding_rate": 10,
			"single_threshold": 2500, "cumulative_threshold": 0}]),
		dict(name="TDS - 194 - Dividends - No PAN / Invalid PAN",
			category_name="Dividends",
			doctype="Tax Withholding Category", accounts=accounts,
			rates=[{"fiscal_year": fiscal_year, "tax_withholding_rate": 20,
			"single_threshold": 2500, "cumulative_threshold": 0}])
	]