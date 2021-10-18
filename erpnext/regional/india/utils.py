from __future__ import unicode_literals

import json
import re

import frappe
from frappe import _
from frappe.model.utils import get_fetch_values
from frappe.utils import cint, cstr, date_diff, flt, getdate, nowdate
from six import string_types

from erpnext.controllers.accounts_controller import get_taxes_and_charges
from erpnext.controllers.taxes_and_totals import get_itemised_tax, get_itemised_taxable_amount
from erpnext.hr.utils import get_salary_assignment
from erpnext.payroll.doctype.salary_structure.salary_structure import make_salary_slip
from erpnext.regional.india import number_state_mapping, state_numbers, states

GST_INVOICE_NUMBER_FORMAT = re.compile(r"^[a-zA-Z0-9\-/]+$")   #alphanumeric and - /
GSTIN_FORMAT = re.compile("^[0-9]{2}[A-Z]{4}[0-9A-Z]{1}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}[1-9A-Z]{1}[0-9A-Z]{1}$")
GSTIN_UIN_FORMAT = re.compile("^[0-9]{4}[A-Z]{3}[0-9]{5}[0-9A-Z]{3}")
PAN_NUMBER_FORMAT = re.compile("[A-Z]{5}[0-9]{4}[A-Z]{1}")


def validate_gstin_for_india(doc, method):
	if hasattr(doc, 'gst_state') and doc.gst_state:
		doc.gst_state_number = state_numbers[doc.gst_state]
	if not hasattr(doc, 'gstin') or not doc.gstin:
		return

	gst_category = []

	if len(doc.links):
		link_doctype = doc.links[0].get("link_doctype")
		link_name = doc.links[0].get("link_name")

		if link_doctype in ["Customer", "Supplier"]:
			gst_category = frappe.db.get_value(link_doctype, {'name': link_name}, ['gst_category'])

	doc.gstin = doc.gstin.upper().strip()
	if not doc.gstin or doc.gstin == 'NA':
		return

	if len(doc.gstin) != 15:
		frappe.throw(_("A GSTIN must have 15 characters."), title=_("Invalid GSTIN"))

	if gst_category and gst_category == 'UIN Holders':
		if not GSTIN_UIN_FORMAT.match(doc.gstin):
			frappe.throw(_("The input you've entered doesn't match the GSTIN format for UIN Holders or Non-Resident OIDAR Service Providers"),
				title=_("Invalid GSTIN"))
	else:
		if not GSTIN_FORMAT.match(doc.gstin):
			frappe.throw(_("The input you've entered doesn't match the format of GSTIN."), title=_("Invalid GSTIN"))

		validate_gstin_check_digit(doc.gstin)
		set_gst_state_and_state_number(doc)

		if not doc.gst_state:
			frappe.throw(_("Please enter GST state"), title=_("Invalid State"))

		if doc.gst_state_number != doc.gstin[:2]:
			frappe.throw(_("First 2 digits of GSTIN should match with State number {0}.")
				.format(doc.gst_state_number), title=_("Invalid GSTIN"))

def validate_pan_for_india(doc, method):
	if doc.get('country') != 'India' or not doc.pan:
		return

	if not PAN_NUMBER_FORMAT.match(doc.pan):
		frappe.throw(_("Invalid PAN No. The input you've entered doesn't match the format of PAN."))

def validate_tax_category(doc, method):
	if doc.get('gst_state') and frappe.db.get_value('Tax Category', {'gst_state': doc.gst_state, 'is_inter_state': doc.is_inter_state}):
		if doc.is_inter_state:
			frappe.throw(_("Inter State tax category for GST State {0} already exists").format(doc.gst_state))
		else:
			frappe.throw(_("Intra State tax category for GST State {0} already exists").format(doc.gst_state))

def update_gst_category(doc, method):
	for link in doc.links:
		if link.link_doctype in ['Customer', 'Supplier']:
			if doc.get('gstin'):
				frappe.db.sql("""
					UPDATE `tab{0}` SET gst_category = %s WHERE name = %s AND gst_category = 'Unregistered'
				""".format(link.link_doctype), ("Registered Regular", link.link_name)) #nosec

def set_gst_state_and_state_number(doc):
	if not doc.gst_state:
		if not doc.state:
			return
		state = doc.state.lower()
		states_lowercase = {s.lower():s for s in states}
		if state in states_lowercase:
			doc.gst_state = states_lowercase[state]
		else:
			return

	doc.gst_state_number = state_numbers[doc.gst_state]

def validate_gstin_check_digit(gstin, label='GSTIN'):
	''' Function to validate the check digit of the GSTIN.'''
	factor = 1
	total = 0
	code_point_chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
	mod = len(code_point_chars)
	input_chars = gstin[:-1]
	for char in input_chars:
		digit = factor * code_point_chars.find(char)
		digit = (digit // mod) + (digit % mod)
		total += digit
		factor = 2 if factor == 1 else 1
	if gstin[-1] != code_point_chars[((mod - (total % mod)) % mod)]:
		frappe.throw(_("""Invalid {0}! The check digit validation has failed. Please ensure you've typed the {0} correctly.""").format(label))

def get_itemised_tax_breakup_header(item_doctype, tax_accounts):
	hsn_wise_in_gst_settings = frappe.db.get_single_value('GST Settings','hsn_wise_tax_breakup')
	if frappe.get_meta(item_doctype).has_field('gst_hsn_code') and hsn_wise_in_gst_settings:
		return [_("HSN/SAC"), _("Taxable Amount")] + tax_accounts
	else:
		return [_("Item"), _("Taxable Amount")] + tax_accounts

def get_itemised_tax_breakup_data(doc, account_wise=False, hsn_wise=False):
	itemised_tax = get_itemised_tax(doc.taxes, with_tax_account=account_wise)

	itemised_taxable_amount = get_itemised_taxable_amount(doc.items)

	if not frappe.get_meta(doc.doctype + " Item").has_field('gst_hsn_code'):
		return itemised_tax, itemised_taxable_amount

	hsn_wise_in_gst_settings = frappe.db.get_single_value('GST Settings','hsn_wise_tax_breakup')

	tax_breakup_hsn_wise = hsn_wise or hsn_wise_in_gst_settings
	if tax_breakup_hsn_wise:
		item_hsn_map = frappe._dict()
		for d in doc.items:
			item_hsn_map.setdefault(d.item_code or d.item_name, d.get("gst_hsn_code"))

	hsn_tax = {}
	for item, taxes in itemised_tax.items():
		item_or_hsn = item if not tax_breakup_hsn_wise else item_hsn_map.get(item)
		hsn_tax.setdefault(item_or_hsn, frappe._dict())
		for tax_desc, tax_detail in taxes.items():
			key = tax_desc
			if account_wise:
				key = tax_detail.get('tax_account')
			hsn_tax[item_or_hsn].setdefault(key, {"tax_rate": 0, "tax_amount": 0})
			hsn_tax[item_or_hsn][key]["tax_rate"] = tax_detail.get("tax_rate")
			hsn_tax[item_or_hsn][key]["tax_amount"] += tax_detail.get("tax_amount")

	# set taxable amount
	hsn_taxable_amount = frappe._dict()
	for item in itemised_taxable_amount:
		item_or_hsn = item if not tax_breakup_hsn_wise else item_hsn_map.get(item)
		hsn_taxable_amount.setdefault(item_or_hsn, 0)
		hsn_taxable_amount[item_or_hsn] += itemised_taxable_amount.get(item)

	return hsn_tax, hsn_taxable_amount

def set_place_of_supply(doc, method=None):
	doc.place_of_supply = get_place_of_supply(doc, doc.doctype)

def validate_document_name(doc, method=None):
	"""Validate GST invoice number requirements."""

	country = frappe.get_cached_value("Company", doc.company, "country")

	# Date was chosen as start of next FY to avoid irritating current users.
	if country != "India" or getdate(doc.posting_date) < getdate("2021-04-01"):
		return

	if len(doc.name) > 16:
		frappe.throw(_("Maximum length of document number should be 16 characters as per GST rules. Please change the naming series."))

	if not GST_INVOICE_NUMBER_FORMAT.match(doc.name):
		frappe.throw(_("Document name should only contain alphanumeric values, dash(-) and slash(/) characters as per GST rules. Please change the naming series."))

# don't remove this function it is used in tests
def test_method():
	'''test function'''
	return 'overridden'

def get_place_of_supply(party_details, doctype):
	if not frappe.get_meta('Address').has_field('gst_state'): return

	if doctype in ("Sales Invoice", "Delivery Note", "Sales Order"):
		address_name = party_details.customer_address or party_details.shipping_address_name
	elif doctype in ("Purchase Invoice", "Purchase Order", "Purchase Receipt"):
		address_name = party_details.shipping_address or party_details.supplier_address

	if address_name:
		address = frappe.db.get_value("Address", address_name, ["gst_state", "gst_state_number", "gstin"], as_dict=1)
		if address and address.gst_state and address.gst_state_number:
			party_details.gstin = address.gstin
			return cstr(address.gst_state_number) + "-" + cstr(address.gst_state)

@frappe.whitelist()
def get_regional_address_details(party_details, doctype, company):
	if isinstance(party_details, string_types):
		party_details = json.loads(party_details)
		party_details = frappe._dict(party_details)

	update_party_details(party_details, doctype)

	party_details.place_of_supply = get_place_of_supply(party_details, doctype)

	if is_internal_transfer(party_details, doctype):
		party_details.taxes_and_charges = ''
		party_details.taxes = []
		return party_details

	if doctype in ("Sales Invoice", "Delivery Note", "Sales Order"):
		master_doctype = "Sales Taxes and Charges Template"
		get_tax_template_based_on_category(master_doctype, company, party_details)

		if party_details.get('taxes_and_charges'):
			return party_details

		if not party_details.company_gstin:
			return party_details

	elif doctype in ("Purchase Invoice", "Purchase Order", "Purchase Receipt"):
		master_doctype = "Purchase Taxes and Charges Template"
		get_tax_template_based_on_category(master_doctype, company, party_details)

		if party_details.get('taxes_and_charges'):
			return party_details

		if not party_details.supplier_gstin:
			return party_details

	if not party_details.place_of_supply: return party_details

	if not party_details.company_gstin: return party_details

	if ((doctype in ("Sales Invoice", "Delivery Note", "Sales Order") and party_details.company_gstin
		and party_details.company_gstin[:2] != party_details.place_of_supply[:2]) or (doctype in ("Purchase Invoice",
		"Purchase Order", "Purchase Receipt") and party_details.supplier_gstin and party_details.supplier_gstin[:2] != party_details.place_of_supply[:2])):
		default_tax = get_tax_template(master_doctype, company, 1, party_details.company_gstin[:2])
	else:
		default_tax = get_tax_template(master_doctype, company, 0, party_details.company_gstin[:2])

	if not default_tax:
		return party_details
	party_details["taxes_and_charges"] = default_tax
	party_details.taxes = get_taxes_and_charges(master_doctype, default_tax)

	return party_details

def update_party_details(party_details, doctype):
	for address_field in ['shipping_address', 'company_address', 'supplier_address', 'shipping_address_name', 'customer_address']:
		if party_details.get(address_field):
			party_details.update(get_fetch_values(doctype, address_field, party_details.get(address_field)))

def is_internal_transfer(party_details, doctype):
	if doctype in ("Sales Invoice", "Delivery Note", "Sales Order"):
		destination_gstin = party_details.company_gstin
	elif doctype in ("Purchase Invoice", "Purchase Order", "Purchase Receipt"):
		destination_gstin = party_details.supplier_gstin

	if not destination_gstin or party_details.gstin:
		return False

	if party_details.gstin == destination_gstin:
		return True
	else:
		False

def get_tax_template_based_on_category(master_doctype, company, party_details):
	if not party_details.get('tax_category'):
		return

	default_tax = frappe.db.get_value(master_doctype, {'company': company, 'tax_category': party_details.get('tax_category')},
		'name')

	if default_tax:
		party_details["taxes_and_charges"] = default_tax
		party_details.taxes = get_taxes_and_charges(master_doctype, default_tax)

def get_tax_template(master_doctype, company, is_inter_state, state_code):
	tax_categories = frappe.get_all('Tax Category', fields = ['name', 'is_inter_state', 'gst_state'],
		filters = {'is_inter_state': is_inter_state})

	default_tax = ''

	for tax_category in tax_categories:
		if tax_category.gst_state == number_state_mapping[state_code] or \
	 		(not default_tax and not tax_category.gst_state):
			default_tax = frappe.db.get_value(master_doctype,
				{'company': company, 'disabled': 0, 'tax_category': tax_category.name}, 'name')
	return default_tax

def calculate_annual_eligible_hra_exemption(doc):
	basic_component, hra_component = frappe.db.get_value('Company',  doc.company,  ["basic_component", "hra_component"])
	if not (basic_component and hra_component):
		frappe.throw(_("Please mention Basic and HRA component in Company"))
	annual_exemption, monthly_exemption, hra_amount = 0, 0, 0
	if hra_component and basic_component:
		assignment = get_salary_assignment(doc.employee, nowdate())
		if assignment:
			hra_component_exists = frappe.db.exists("Salary Detail", {
				"parent": assignment.salary_structure,
				"salary_component": hra_component,
				"parentfield": "earnings",
				"parenttype": "Salary Structure"
			})

			if hra_component_exists:
				basic_amount, hra_amount = get_component_amt_from_salary_slip(doc.employee,
					assignment.salary_structure, basic_component, hra_component)
				if hra_amount:
					if doc.monthly_house_rent:
						annual_exemption = calculate_hra_exemption(assignment.salary_structure,
							basic_amount, hra_amount, doc.monthly_house_rent, doc.rented_in_metro_city)
						if annual_exemption > 0:
							monthly_exemption = annual_exemption / 12
						else:
							annual_exemption = 0

		elif doc.docstatus == 1:
			frappe.throw(_("Salary Structure must be submitted before submission of Tax Ememption Declaration"))

	return frappe._dict({
		"hra_amount": hra_amount,
		"annual_exemption": annual_exemption,
		"monthly_exemption": monthly_exemption
	})

def get_component_amt_from_salary_slip(employee, salary_structure, basic_component, hra_component):
	salary_slip = make_salary_slip(salary_structure, employee=employee, for_preview=1, ignore_permissions=True)
	basic_amt, hra_amt = 0, 0
	for earning in salary_slip.earnings:
		if earning.salary_component == basic_component:
			basic_amt = earning.amount
		elif earning.salary_component == hra_component:
			hra_amt = earning.amount
		if basic_amt and hra_amt:
			return basic_amt, hra_amt
	return basic_amt, hra_amt

def calculate_hra_exemption(salary_structure, basic, monthly_hra, monthly_house_rent, rented_in_metro_city):
	# TODO make this configurable
	exemptions = []
	frequency = frappe.get_value("Salary Structure", salary_structure, "payroll_frequency")
	# case 1: The actual amount allotted by the employer as the HRA.
	exemptions.append(get_annual_component_pay(frequency, monthly_hra))

	actual_annual_rent = monthly_house_rent * 12
	annual_basic = get_annual_component_pay(frequency, basic)

	# case 2: Actual rent paid less 10% of the basic salary.
	exemptions.append(flt(actual_annual_rent) - flt(annual_basic * 0.1))
	# case 3: 50% of the basic salary, if the employee is staying in a metro city (40% for a non-metro city).
	exemptions.append(annual_basic * 0.5 if rented_in_metro_city else annual_basic * 0.4)
	# return minimum of 3 cases
	return min(exemptions)

def get_annual_component_pay(frequency, amount):
	if frequency == "Daily":
		return amount * 365
	elif frequency == "Weekly":
		return amount * 52
	elif frequency == "Fortnightly":
		return amount * 26
	elif frequency == "Monthly":
		return amount * 12
	elif frequency == "Bimonthly":
		return amount * 6

def validate_house_rent_dates(doc):
	if not doc.rented_to_date or not doc.rented_from_date:
		frappe.throw(_("House rented dates required for exemption calculation"))

	if date_diff(doc.rented_to_date, doc.rented_from_date) < 14:
		frappe.throw(_("House rented dates should be atleast 15 days apart"))

	proofs = frappe.db.sql("""
		select name
		from `tabEmployee Tax Exemption Proof Submission`
		where
			docstatus=1 and employee=%(employee)s and payroll_period=%(payroll_period)s
			and (rented_from_date between %(from_date)s and %(to_date)s or rented_to_date between %(from_date)s and %(to_date)s)
	""", {
		"employee": doc.employee,
		"payroll_period": doc.payroll_period,
		"from_date": doc.rented_from_date,
		"to_date": doc.rented_to_date
	})

	if proofs:
		frappe.throw(_("House rent paid days overlapping with {0}").format(proofs[0][0]))

def calculate_hra_exemption_for_period(doc):
	monthly_rent, eligible_hra = 0, 0
	if doc.house_rent_payment_amount:
		validate_house_rent_dates(doc)
		# TODO receive rented months or validate dates are start and end of months?
		# Calc monthly rent, round to nearest .5
		factor = flt(date_diff(doc.rented_to_date, doc.rented_from_date) + 1)/30
		factor = round(factor * 2)/2
		monthly_rent = doc.house_rent_payment_amount / factor
		# update field used by calculate_annual_eligible_hra_exemption
		doc.monthly_house_rent = monthly_rent
		exemptions = calculate_annual_eligible_hra_exemption(doc)

		if exemptions["monthly_exemption"]:
			# calc total exemption amount
			eligible_hra = exemptions["monthly_exemption"] * factor
		exemptions["monthly_house_rent"] = monthly_rent
		exemptions["total_eligible_hra_exemption"] = eligible_hra
		return exemptions

def get_ewb_data(dt, dn):

	ewaybills = []
	for doc_name in dn:
		doc = frappe.get_doc(dt, doc_name)

		validate_doc(doc)

		data = frappe._dict({
			"transporterId": "",
			"TotNonAdvolVal": 0,
		})

		data.userGstin = data.fromGstin = doc.company_gstin
		data.supplyType = 'O'

		if dt == 'Delivery Note':
			data.subSupplyType = 1
		elif doc.gst_category in ['Registered Regular', 'SEZ']:
			data.subSupplyType = 1
		elif doc.gst_category in ['Overseas', 'Deemed Export']:
			data.subSupplyType = 3
		else:
			frappe.throw(_('Unsupported GST Category for E-Way Bill JSON generation'))

		data.docType = 'INV'
		data.docDate = frappe.utils.formatdate(doc.posting_date, 'dd/mm/yyyy')

		company_address = frappe.get_doc('Address', doc.company_address)
		billing_address = frappe.get_doc('Address', doc.customer_address)

		#added dispatch address
		dispatch_address = frappe.get_doc('Address', doc.dispatch_address_name) if doc.dispatch_address_name else company_address
		shipping_address = frappe.get_doc('Address', doc.shipping_address_name)

		data = get_address_details(data, doc, company_address, billing_address, dispatch_address)

		data.itemList = []
		data.totalValue = doc.total

		data = get_item_list(data, doc, hsn_wise=True)

		disable_rounded = frappe.db.get_single_value('Global Defaults', 'disable_rounded_total')
		data.totInvValue = doc.grand_total if disable_rounded else doc.rounded_total

		data = get_transport_details(data, doc)

		fields = {
			"/. -": {
				'docNo': doc.name,
				'fromTrdName': doc.company,
				'toTrdName': doc.customer_name,
				'transDocNo': doc.lr_no,
			},
			"@#/,&. -": {
				'fromAddr1': company_address.address_line1,
				'fromAddr2': company_address.address_line2,
				'fromPlace': company_address.city,
				'toAddr1': shipping_address.address_line1,
				'toAddr2': shipping_address.address_line2,
				'toPlace': shipping_address.city,
				'transporterName': doc.transporter_name
			}
		}

		for allowed_chars, field_map in fields.items():
			for key, value in field_map.items():
				if not value:
					data[key] = ''
				else:
					data[key] = re.sub(r'[^\w' + allowed_chars + ']', '', value)

		ewaybills.append(data)

	data = {
		'version': '1.0.0421',
		'billLists': ewaybills
	}

	return data

@frappe.whitelist()
def generate_ewb_json(dt, dn):
	dn = json.loads(dn)
	return get_ewb_data(dt, dn)

@frappe.whitelist()
def download_ewb_json():
	data = json.loads(frappe.local.form_dict.data)
	frappe.local.response.filecontent = json.dumps(data, indent=4, sort_keys=True)
	frappe.local.response.type = 'download'

	filename_prefix = 'Bulk'
	docname = frappe.local.form_dict.docname
	if docname:
		if docname.startswith('['):
			docname = json.loads(docname)
			if len(docname) == 1:
				docname = docname[0]

		if not isinstance(docname, list):
			# removes characters not allowed in a filename (https://stackoverflow.com/a/38766141/4767738)
			filename_prefix = re.sub(r'[^\w_.)( -]', '', docname)

	frappe.local.response.filename = '{0}_e-WayBill_Data_{1}.json'.format(filename_prefix, frappe.utils.random_string(5))

@frappe.whitelist()
def get_gstins_for_company(company):
	company_gstins =[]
	if company:
		company_gstins = frappe.db.sql("""select
			distinct `tabAddress`.gstin
		from
			`tabAddress`, `tabDynamic Link`
		where
			`tabDynamic Link`.parent = `tabAddress`.name and
			`tabDynamic Link`.parenttype = 'Address' and
			`tabDynamic Link`.link_doctype = 'Company' and
			`tabDynamic Link`.link_name = %(company)s""", {"company": company})
	return company_gstins

def get_address_details(data, doc, company_address, billing_address, dispatch_address):
	data.fromPincode = validate_pincode(company_address.pincode, 'Company Address')
	data.fromStateCode = validate_state_code(company_address.gst_state_number, 'Company Address')
	data.actualFromStateCode = validate_state_code(dispatch_address.gst_state_number, 'Dispatch Address')

	if not doc.billing_address_gstin or len(doc.billing_address_gstin) < 15:
		data.toGstin = 'URP'
		set_gst_state_and_state_number(billing_address)
	else:
		data.toGstin = doc.billing_address_gstin

	data.toPincode = validate_pincode(billing_address.pincode, 'Customer Address')
	data.toStateCode = validate_state_code(billing_address.gst_state_number, 'Customer Address')

	if doc.customer_address != doc.shipping_address_name:
		data.transType = 2
		shipping_address = frappe.get_doc('Address', doc.shipping_address_name)
		set_gst_state_and_state_number(shipping_address)
		data.toPincode = validate_pincode(shipping_address.pincode, 'Shipping Address')
		data.actualToStateCode = validate_state_code(shipping_address.gst_state_number, 'Shipping Address')
	else:
		data.transType = 1
		data.actualToStateCode = data.toStateCode
		shipping_address = billing_address

	if doc.gst_category == 'SEZ':
		data.toStateCode = 99

	return data

def get_item_list(data, doc, hsn_wise=False):
	for attr in ['cgstValue', 'sgstValue', 'igstValue', 'cessValue', 'OthValue']:
		data[attr] = 0

	gst_accounts = get_gst_accounts(doc.company, account_wise=True)
	tax_map = {
		'sgst_account': ['sgstRate', 'sgstValue'],
		'cgst_account': ['cgstRate', 'cgstValue'],
		'igst_account': ['igstRate', 'igstValue'],
		'cess_account': ['cessRate', 'cessValue']
	}
	item_data_attrs = ['sgstRate', 'cgstRate', 'igstRate', 'cessRate', 'cessNonAdvol']
	hsn_wise_charges, hsn_taxable_amount = get_itemised_tax_breakup_data(doc, account_wise=True, hsn_wise=hsn_wise)
	for hsn_code, taxable_amount in hsn_taxable_amount.items():
		item_data = frappe._dict()
		if not hsn_code:
			frappe.throw(_('GST HSN Code does not exist for one or more items'))
		item_data.hsnCode = int(hsn_code)
		item_data.taxableAmount = taxable_amount
		item_data.qtyUnit = ""
		for attr in item_data_attrs:
			item_data[attr] = 0

		for account, tax_detail in hsn_wise_charges.get(hsn_code, {}).items():
			account_type = gst_accounts.get(account, '')
			for tax_acc, attrs in tax_map.items():
				if account_type == tax_acc:
					item_data[attrs[0]] = tax_detail.get('tax_rate')
					data[attrs[1]] += tax_detail.get('tax_amount')
					break
			else:
				data.OthValue += tax_detail.get('tax_amount')

		data.itemList.append(item_data)

		# Tax amounts rounded to 2 decimals to avoid exceeding max character limit
		for attr in ['sgstValue', 'cgstValue', 'igstValue', 'cessValue']:
			data[attr] = flt(data[attr], 2)

	return data

def validate_doc(doc):
	if doc.docstatus != 1:
		frappe.throw(_('E-Way Bill JSON can only be generated from submitted document'))

	if doc.is_return:
		frappe.throw(_('E-Way Bill JSON cannot be generated for Sales Return as of now'))

	if doc.ewaybill:
		frappe.throw(_('e-Way Bill already exists for this document'))

	reqd_fields = ['company_gstin', 'company_address', 'customer_address',
		'shipping_address_name', 'mode_of_transport', 'distance']

	for fieldname in reqd_fields:
		if not doc.get(fieldname):
			frappe.throw(_('{} is required to generate E-Way Bill JSON').format(
				doc.meta.get_label(fieldname)
			))

	if len(doc.company_gstin) < 15:
		frappe.throw(_('You must be a registered supplier to generate e-Way Bill'))

def get_transport_details(data, doc):
	if doc.distance > 4000:
		frappe.throw(_('Distance cannot be greater than 4000 kms'))

	data.transDistance = int(round(doc.distance))

	transport_modes = {
		'Road': 1,
		'Rail': 2,
		'Air': 3,
		'Ship': 4
	}

	vehicle_types = {
		'Regular': 'R',
		'Over Dimensional Cargo (ODC)': 'O'
	}

	data.transMode = transport_modes.get(doc.mode_of_transport)

	if doc.mode_of_transport == 'Road':
		if not doc.gst_transporter_id and not doc.vehicle_no:
			frappe.throw(_('Either GST Transporter ID or Vehicle No is required if Mode of Transport is Road'))
		if doc.vehicle_no:
			data.vehicleNo = doc.vehicle_no.replace(' ', '')
		if not doc.gst_vehicle_type:
			frappe.throw(_('Vehicle Type is required if Mode of Transport is Road'))
		else:
			data.vehicleType = vehicle_types.get(doc.gst_vehicle_type)
	else:
		if not doc.lr_no or not doc.lr_date:
			frappe.throw(_('Transport Receipt No and Date are mandatory for your chosen Mode of Transport'))

	if doc.lr_no:
		data.transDocNo = doc.lr_no

	if doc.lr_date:
		data.transDocDate = frappe.utils.formatdate(doc.lr_date, 'dd/mm/yyyy')

	if doc.gst_transporter_id:
		if doc.gst_transporter_id[0:2] != "88":
			validate_gstin_check_digit(doc.gst_transporter_id, label='GST Transporter ID')
		data.transporterId = doc.gst_transporter_id

	return data


def validate_pincode(pincode, address):
	pin_not_found = "Pin Code doesn't exist for {}"
	incorrect_pin = "Pin Code for {} is incorrecty formatted. It must be 6 digits (without spaces)"

	if not pincode:
		frappe.throw(_(pin_not_found.format(address)))

	pincode = pincode.replace(' ', '')
	if not pincode.isdigit() or len(pincode) != 6:
		frappe.throw(_(incorrect_pin.format(address)))
	else:
		return int(pincode)

def validate_state_code(state_code, address):
	no_state_code = "GST State Code not found for {0}. Please set GST State in {0}"
	if not state_code:
		frappe.throw(_(no_state_code.format(address)))
	else:
		return int(state_code)

@frappe.whitelist()
def get_gst_accounts(company=None, account_wise=False, only_reverse_charge=0, only_non_reverse_charge=0):
	filters={"parent": "GST Settings"}

	if company:
		filters.update({'company': company})
	if only_reverse_charge:
		filters.update({'is_reverse_charge_account': 1})
	elif only_non_reverse_charge:
		filters.update({'is_reverse_charge_account': 0})

	gst_accounts = frappe._dict()
	gst_settings_accounts = frappe.get_all("GST Account",
		filters=filters,
		fields=["cgst_account", "sgst_account", "igst_account", "cess_account"])

	if not gst_settings_accounts and not frappe.flags.in_test and not frappe.flags.in_migrate:
		frappe.throw(_("Please set GST Accounts in GST Settings"))

	for d in gst_settings_accounts:
		for acc, val in d.items():
			if not account_wise:
				gst_accounts.setdefault(acc, []).append(val)
			elif val:
				gst_accounts[val] = acc

	return gst_accounts

def validate_reverse_charge_transaction(doc, method):
	country = frappe.get_cached_value('Company', doc.company, 'country')

	if country != 'India':
		return

	base_gst_tax = 0
	base_reverse_charge_booked = 0

	if doc.reverse_charge == 'Y':
		gst_accounts = get_gst_accounts(doc.company, only_reverse_charge=1)
		reverse_charge_accounts = gst_accounts.get('cgst_account') + gst_accounts.get('sgst_account') \
			+ gst_accounts.get('igst_account')

		gst_accounts = get_gst_accounts(doc.company, only_non_reverse_charge=1)
		non_reverse_charge_accounts = gst_accounts.get('cgst_account') + gst_accounts.get('sgst_account') \
			+ gst_accounts.get('igst_account')

		for tax in doc.get('taxes'):
			if tax.account_head in non_reverse_charge_accounts:
				if tax.add_deduct_tax == 'Add':
					base_gst_tax += tax.base_tax_amount_after_discount_amount
				else:
					base_gst_tax += tax.base_tax_amount_after_discount_amount
			elif tax.account_head in reverse_charge_accounts:
				if tax.add_deduct_tax == 'Add':
					base_reverse_charge_booked += tax.base_tax_amount_after_discount_amount
				else:
					base_reverse_charge_booked += tax.base_tax_amount_after_discount_amount

		if base_gst_tax != base_reverse_charge_booked:
			msg = _("Booked reverse charge is not equal to applied tax amount")
			msg += "<br>"
			msg += _("Please refer {gst_document_link} to learn more about how to setup and create reverse charge invoice").format(
				gst_document_link='<a href="https://docs.erpnext.com/docs/user/manual/en/regional/india/gst-setup">GST Documentation</a>')

			frappe.throw(msg)

def update_itc_availed_fields(doc, method):
	country = frappe.get_cached_value('Company', doc.company, 'country')

	if country != 'India':
		return

	# Initialize values
	doc.itc_integrated_tax = doc.itc_state_tax = doc.itc_central_tax = doc.itc_cess_amount = 0
	gst_accounts = get_gst_accounts(doc.company, only_non_reverse_charge=1)

	for tax in doc.get('taxes'):
		if tax.account_head in gst_accounts.get('igst_account', []):
			doc.itc_integrated_tax += flt(tax.base_tax_amount_after_discount_amount)
		if tax.account_head in gst_accounts.get('sgst_account', []):
			doc.itc_state_tax += flt(tax.base_tax_amount_after_discount_amount)
		if tax.account_head in gst_accounts.get('cgst_account', []):
			doc.itc_central_tax += flt(tax.base_tax_amount_after_discount_amount)
		if tax.account_head in gst_accounts.get('cess_account', []):
			doc.itc_cess_amount += flt(tax.base_tax_amount_after_discount_amount)

def update_place_of_supply(doc, method):
	country = frappe.get_cached_value('Company', doc.company, 'country')
	if country != 'India':
		return

	address = frappe.db.get_value("Address", doc.get('customer_address'), ["gst_state", "gst_state_number"], as_dict=1)
	if address and address.gst_state and address.gst_state_number:
		doc.place_of_supply = cstr(address.gst_state_number) + "-" + cstr(address.gst_state)

@frappe.whitelist()
def get_regional_round_off_accounts(company, account_list):
	country = frappe.get_cached_value('Company', company, 'country')

	if country != 'India':
		return

	if isinstance(account_list, string_types):
		account_list = json.loads(account_list)

	if not frappe.db.get_single_value('GST Settings', 'round_off_gst_values'):
		return

	gst_accounts = get_gst_accounts(company)

	gst_account_list = []
	for account in ['cgst_account', 'sgst_account', 'igst_account']:
		if account in gst_accounts:
			gst_account_list += gst_accounts.get(account)

	account_list.extend(gst_account_list)

	return account_list

def update_taxable_values(doc, method):
	country = frappe.get_cached_value('Company', doc.company, 'country')

	if country != 'India':
		return

	gst_accounts = get_gst_accounts(doc.company)

	# Only considering sgst account to avoid inflating taxable value
	gst_account_list = gst_accounts.get('sgst_account', []) + gst_accounts.get('sgst_account', []) \
		+ gst_accounts.get('igst_account', [])

	additional_taxes = 0
	total_charges = 0
	item_count = 0
	considered_rows = []

	for tax in doc.get('taxes'):
		prev_row_id = cint(tax.row_id) - 1
		if tax.account_head in gst_account_list and prev_row_id not in considered_rows:
			if tax.charge_type == 'On Previous Row Amount':
				additional_taxes += doc.get('taxes')[prev_row_id].tax_amount_after_discount_amount
				considered_rows.append(prev_row_id)
			if tax.charge_type == 'On Previous Row Total':
				additional_taxes += doc.get('taxes')[prev_row_id].base_total - doc.base_net_total
				considered_rows.append(prev_row_id)

	for item in doc.get('items'):
		proportionate_value = item.base_net_amount if doc.base_net_total else item.qty
		total_value = doc.base_net_total if doc.base_net_total else doc.total_qty

		applicable_charges = flt(flt(proportionate_value * (flt(additional_taxes) / flt(total_value)),
			item.precision('taxable_value')))
		item.taxable_value = applicable_charges + proportionate_value
		total_charges += applicable_charges
		item_count += 1

	if total_charges != additional_taxes:
		diff = additional_taxes - total_charges
		doc.get('items')[item_count - 1].taxable_value += diff

def get_depreciation_amount(asset, depreciable_value, row):
	depreciation_left = flt(row.total_number_of_depreciations) - flt(asset.number_of_depreciations_booked)

	if row.depreciation_method in ("Straight Line", "Manual"):
		# if the Depreciation Schedule is being prepared for the first time
		if not asset.flags.increase_in_asset_life:
			depreciation_amount = (flt(row.value_after_depreciation) -
				flt(row.expected_value_after_useful_life)) / depreciation_left

		# if the Depreciation Schedule is being modified after Asset Repair
		else:
			depreciation_amount = (flt(row.value_after_depreciation) -
				flt(row.expected_value_after_useful_life)) / (date_diff(asset.to_date, asset.available_for_use_date) / 365)

	else:
		rate_of_depreciation = row.rate_of_depreciation
		# if its the first depreciation
		if depreciable_value == asset.gross_purchase_amount:
			if row.finance_book and frappe.db.get_value('Finance Book', row.finance_book, 'for_income_tax'):
				# as per IT act, if the asset is purchased in the 2nd half of fiscal year, then rate is divided by 2
				diff = date_diff(row.depreciation_start_date, asset.available_for_use_date)
				if diff <= 180:
					rate_of_depreciation = rate_of_depreciation / 2
					frappe.msgprint(
						_('As per IT Act, the rate of depreciation for the first depreciation entry is reduced by 50%.'))

		depreciation_amount = flt(depreciable_value * (flt(rate_of_depreciation) / 100))

	return depreciation_amount

def set_item_tax_from_hsn_code(item):
	if not item.taxes and item.gst_hsn_code:
		hsn_doc = frappe.get_doc("GST HSN Code", item.gst_hsn_code)

		for tax in hsn_doc.taxes:
			item.append('taxes', {
				'item_tax_template': tax.item_tax_template,
				'tax_category': tax.tax_category,
				'valid_from': tax.valid_from
			})

def delete_gst_settings_for_company(doc, method):
	if doc.country != 'India':
		return

	gst_settings = frappe.get_doc("GST Settings")
	records_to_delete = []

	for d in reversed(gst_settings.get('gst_accounts')):
		if d.company == doc.name:
			records_to_delete.append(d)

	for d in records_to_delete:
		gst_settings.remove(d)

	gst_settings.save()
