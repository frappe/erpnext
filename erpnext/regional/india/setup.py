# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe, os, json
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.permissions import add_permission
from erpnext.regional.india import states
from erpnext.accounts.utils import get_fiscal_year
from frappe.utils import today

def setup(company=None, patch=True):
	make_custom_fields()
	add_permissions()
	add_custom_roles_for_reports()
	frappe.enqueue('erpnext.regional.india.setup.add_hsn_sac_codes', now=frappe.flags.in_test)
	add_print_formats()
	if not patch:
		update_address_template()
		make_fixtures(company)

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

def add_permissions():
	for doctype in ('GST HSN Code', 'GST Settings'):
		add_permission(doctype, 'All', 0)

def add_print_formats():
	frappe.reload_doc("regional", "print_format", "gst_tax_invoice")
	frappe.reload_doc("accounts", "print_format", "gst_pos_invoice")

	frappe.db.sql(""" update `tabPrint Format` set disabled = 0 where
		name in('GST POS Invoice', 'GST Tax Invoice') """)

def make_custom_fields(update=True):
	hsn_sac_field = dict(fieldname='gst_hsn_code', label='HSN/SAC',
		fieldtype='Data', fetch_from='item_code.gst_hsn_code', insert_after='description',
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
				fetch_from='supplier_address.gstin', print_hide=1),
			dict(fieldname='company_gstin', label='Company GSTIN',
				fieldtype='Data', insert_after='shipping_address_display',
				fetch_from='shipping_address.gstin', print_hide=1),
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
				fetch_from='customer_address.gstin', print_hide=1),
			dict(fieldname='customer_gstin', label='Customer GSTIN',
				fieldtype='Data', insert_after='shipping_address_name',
				fetch_from='shipping_address_name.gstin', print_hide=1),
			dict(fieldname='place_of_supply', label='Place of Supply',
				fieldtype='Data', insert_after='customer_gstin',
				print_hide=1, read_only=0),
			dict(fieldname='company_gstin', label='Company GSTIN',
				fieldtype='Data', insert_after='company_address',
				fetch_from='company_address.gstin', print_hide=1),
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

	inter_state_gst_field = [
		dict(fieldname='is_inter_state', label='Is Inter State',
			fieldtype='Check', insert_after='disabled', print_hide=1)
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
			'insert_after': 'transporter_name',
			'fetch_from': 'transporter.gst_transporter_id',
			'print_hide': 1
		},
		{
			'fieldname': 'mode_of_transport',
			'label': 'Mode of Transport',
			'fieldtype': 'Select',
			'options': '\nRoad\nAir\nRail\nShip',
			'default': 'Road',
			'insert_after': 'lr_date',
			'print_hide': 1
		},
		{
			'fieldname': 'gst_vehicle_type',
			'label': 'GST Vehicle Type',
			'fieldtype': 'Select',
			'options': '\nRegular\nOver Dimensional Cargo (ODC)',
			'default': 'Regular',
			'depends_on': 'eval:(doc.mode_of_transport === "Road")',
			'insert_after': 'mode_of_transport',
			'print_hide': 1
		}
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
		'Purchase Invoice': invoice_gst_fields + purchase_invoice_gst_fields,
		'Sales Invoice': invoice_gst_fields + sales_invoice_gst_fields,
		'Delivery Note': sales_invoice_gst_fields + ewaybill_fields,
		'Sales Taxes and Charges Template': inter_state_gst_field,
		'Purchase Taxes and Charges Template': inter_state_gst_field,
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
		'Purchase Invoice Item': [hsn_sac_field],
		'Employee': [
			dict(fieldname='ifsc_code', label='IFSC Code',
				fieldtype='Data', insert_after='bank_ac_no', print_hide=1,
				depends_on='eval:doc.salary_mode == "Bank"')
		],
		'Company': [
			dict(fieldname='hra_section', label='HRA Settings',
				fieldtype='Section Break', insert_after='asset_received_but_not_billed'),
			dict(fieldname='basic_component', label='Basic Component',
				fieldtype='Link', options='Salary Component', insert_after='hra_section'),
			dict(fieldname='hra_component', label='HRA Component',
				fieldtype='Link', options='Salary Component', insert_after='basic_component'),
			dict(fieldname='arrear_component', label='Arrear Component',
				fieldtype='Link', options='Salary Component', insert_after='hra_component')
		],
		'Employee Tax Exemption Declaration':[
			dict(fieldname='hra_section', label='HRA Exemption',
				fieldtype='Section Break', insert_after='declarations'),
			dict(fieldname='salary_structure_hra', label='HRA as per Salary Structure',
				fieldtype='Currency', insert_after='hra_section', read_only=1),
			dict(fieldname='monthly_house_rent', label='Monthly House Rent',
				fieldtype='Currency', insert_after='salary_structure_hra'),
			dict(fieldname='rented_in_metro_city', label='Rented in Metro City',
				fieldtype='Check', insert_after='monthly_house_rent'),
			dict(fieldname='hra_column_break', fieldtype='Column Break',
				insert_after='rented_in_metro_city'),
			dict(fieldname='annual_hra_exemption', label='Annual HRA Exemption',
				fieldtype='Currency', insert_after='hra_column_break', read_only=1),
			dict(fieldname='monthly_hra_exemption', label='Monthly HRA Exemption',
				fieldtype='Currency', insert_after='annual_hra_exemption', read_only=1)
		],
		'Employee Tax Exemption Proof Submission': [
			dict(fieldname='hra_section', label='HRA Exemption',
				fieldtype='Section Break', insert_after='tax_exemption_proofs'),
			dict(fieldname='house_rent_payment_amount', label='House Rent Payment Amount',
				fieldtype='Currency', insert_after='hra_section'),
			dict(fieldname='rented_in_metro_city', label='Rented in Metro City',
				fieldtype='Check', insert_after='house_rent_payment_amount'),
			dict(fieldname='rented_from_date', label='Rented From Date',
				fieldtype='Date', insert_after='rented_in_metro_city'),
			dict(fieldname='rented_to_date', label='Rented To Date',
				fieldtype='Date', insert_after='rented_from_date'),
			dict(fieldname='hra_column_break', fieldtype='Column Break',
				insert_after='rented_to_date'),
			dict(fieldname='monthly_house_rent', label='Monthly House Rent',
				fieldtype='Currency', insert_after='hra_column_break', read_only=1),
			dict(fieldname='monthly_hra_exemption', label='Monthly Eligible Amount',
				fieldtype='Currency', insert_after='monthly_house_rent', read_only=1),
			dict(fieldname='total_eligible_hra_exemption', label='Total Eligible HRA Exemption',
				fieldtype='Currency', insert_after='monthly_hra_exemption', read_only=1)
		],
		'Supplier': [
			{
				'fieldname': 'gst_transporter_id',
				'label': 'GST Transporter ID',
				'fieldtype': 'Data',
				'insert_after': 'supplier_type',
				'depends_on': 'eval:doc.is_transporter'
			}
		]
	}

	create_custom_fields(custom_fields, ignore_validate = frappe.flags.in_patch, update=update)

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
			pass
		except frappe.DuplicateEntryError:
			pass

	# create records for Tax Withholding Category
	set_tax_withholding_category(company)

def set_salary_components(docs):
	docs.extend([
		{'doctype': 'Salary Component', 'salary_component': 'Professional Tax', 'description': 'Professional Tax', 'type': 'Deduction'},
		{'doctype': 'Salary Component', 'salary_component': 'Provident Fund', 'description': 'Provident fund', 'type': 'Deduction'},
		{'doctype': 'Salary Component', 'salary_component': 'House Rent Allowance', 'description': 'House Rent Allowance', 'type': 'Earning'},
		{'doctype': 'Salary Component', 'salary_component': 'Basic', 'description': 'Basic', 'type': 'Earning'},
		{'doctype': 'Salary Component', 'salary_component': 'Arrear', 'description': 'Arrear', 'type': 'Earning'},
		{'doctype': 'Salary Component', 'salary_component': 'Leave Encashment', 'description': 'Leave Encashment', 'type': 'Earning'}
	])

def set_tax_withholding_category(company):
	accounts = []
	abbr = frappe.get_value("Company", company, "abbr")
	tds_account = frappe.get_value("Account", 'TDS Payable - {0}'.format(abbr), 'name')

	if company and tds_account:
		accounts = [dict(company=company, account=tds_account)]

	fiscal_year = get_fiscal_year(today(), company=accounts[0].get('company'))[0]
	docs = get_tds_details(accounts, fiscal_year)

	for d in docs:
		try:
			doc = frappe.get_doc(d)
			doc.flags.ignore_permissions = True
			doc.insert()
		except frappe.DuplicateEntryError:
			doc = frappe.get_doc("Tax Withholding Category", d.get("name"))
			doc.append("accounts", accounts[0])

			# if fiscal year don't match with any of the already entered data, append rate row
			fy_exist = [k for k in doc.get('rates') if k.get('fiscal_year')==fiscal_year]
			if not fy_exist:
				doc.append("rates", d.get('rates')[0])

			doc.save()

def set_tds_account(docs, company):
	abbr = frappe.get_value("Company", company, "abbr")
	docs.extend([
		{
			"doctype": "Account", "account_name": "TDS Payable", "account_type": "Tax",
			"parent_account": "Duties and Taxes - {0}".format(abbr), "company": company
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
