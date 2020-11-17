from __future__ import unicode_literals
import frappe, re, json
from frappe import _
import erpnext
from frappe.utils import cstr, flt, date_diff, nowdate, round_based_on_smallest_currency_fraction, money_in_words
from erpnext.regional.india import states, state_numbers
from erpnext.controllers.taxes_and_totals import get_itemised_tax, get_itemised_taxable_amount, calculate_outstanding_amount
from erpnext.controllers.accounts_controller import get_taxes_and_charges
from erpnext.hr.utils import get_salary_assignment
from erpnext.hr.doctype.salary_structure.salary_structure import make_salary_slip
from erpnext.regional.india import number_state_mapping
from six import string_types
from erpnext.accounts.general_ledger import make_gl_entries
from erpnext.accounts.utils import get_account_currency

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
		frappe.throw(_("Invalid GSTIN! A GSTIN must have 15 characters."))

	if gst_category and gst_category == 'UIN Holders':
		p = re.compile("^[0-9]{4}[A-Z]{3}[0-9]{5}[0-9A-Z]{3}")
		if not p.match(doc.gstin):
			frappe.throw(_("Invalid GSTIN! The input you've entered doesn't match the GSTIN format for UIN Holders or Non-Resident OIDAR Service Providers"))
	else:
		p = re.compile("^[0-9]{2}[A-Z]{4}[0-9A-Z]{1}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}[1-9A-Z]{1}[0-9A-Z]{1}$")
		if not p.match(doc.gstin):
			frappe.throw(_("Invalid GSTIN! The input you've entered doesn't match the format of GSTIN."))

		validate_gstin_check_digit(doc.gstin)
		set_gst_state_and_state_number(doc)

		if doc.gst_state_number != doc.gstin[:2]:
			frappe.throw(_("Invalid GSTIN! First 2 digits of GSTIN should match with State number {0}.")
				.format(doc.gst_state_number))

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
		frappe.throw(_("""Invalid {0}! The check digit validation has failed.
			Please ensure you've typed the {0} correctly.""".format(label)))

def get_itemised_tax_breakup_header(item_doctype, tax_accounts):
	if frappe.get_meta(item_doctype).has_field('gst_hsn_code'):
		return [_("HSN/SAC"), _("Taxable Amount")] + tax_accounts
	else:
		return [_("Item"), _("Taxable Amount")] + tax_accounts

def get_itemised_tax_breakup_data(doc, account_wise=False):
	itemised_tax = get_itemised_tax(doc.taxes, with_tax_account=account_wise)

	itemised_taxable_amount = get_itemised_taxable_amount(doc.items)

	if not frappe.get_meta(doc.doctype + " Item").has_field('gst_hsn_code'):
		return itemised_tax, itemised_taxable_amount

	item_hsn_map = frappe._dict()
	for d in doc.items:
		item_hsn_map.setdefault(d.item_code or d.item_name, d.get("gst_hsn_code"))

	hsn_tax = {}
	for item, taxes in itemised_tax.items():
		hsn_code = item_hsn_map.get(item)
		hsn_tax.setdefault(hsn_code, frappe._dict())
		for tax_desc, tax_detail in taxes.items():
			key = tax_desc
			if account_wise:
				key = tax_detail.get('tax_account')
			hsn_tax[hsn_code].setdefault(key, {"tax_rate": 0, "tax_amount": 0})
			hsn_tax[hsn_code][key]["tax_rate"] = tax_detail.get("tax_rate")
			hsn_tax[hsn_code][key]["tax_amount"] += tax_detail.get("tax_amount")

	# set taxable amount
	hsn_taxable_amount = frappe._dict()
	for item in itemised_taxable_amount:
		hsn_code = item_hsn_map.get(item)
		hsn_taxable_amount.setdefault(hsn_code, 0)
		hsn_taxable_amount[hsn_code] += itemised_taxable_amount.get(item)

	return hsn_tax, hsn_taxable_amount

def set_place_of_supply(doc, method=None):
	doc.place_of_supply = get_place_of_supply(doc, doc.doctype)

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
		address = frappe.db.get_value("Address", address_name, ["gst_state", "gst_state_number"], as_dict=1)
		if address and address.gst_state and address.gst_state_number:
			return cstr(address.gst_state_number) + "-" + cstr(address.gst_state)

@frappe.whitelist()
def get_regional_address_details(party_details, doctype, company, return_taxes=None):

	if isinstance(party_details, string_types):
		party_details = json.loads(party_details)
		party_details = frappe._dict(party_details)

	party_details.place_of_supply = get_place_of_supply(party_details, doctype)
	if doctype in ("Sales Invoice", "Delivery Note", "Sales Order"):
		master_doctype = "Sales Taxes and Charges Template"

		get_tax_template_for_sez(party_details, master_doctype, company, 'Customer')
		get_tax_template_based_on_category(master_doctype, company, party_details)

		if party_details.get('taxes_and_charges') and return_taxes:
			return party_details

		if not party_details.company_gstin:
			return

	elif doctype in ("Purchase Invoice", "Purchase Order", "Purchase Receipt"):
		master_doctype = "Purchase Taxes and Charges Template"

		get_tax_template_for_sez(party_details, master_doctype, company, 'Supplier')
		get_tax_template_based_on_category(master_doctype, company, party_details)

		if party_details.get('taxes_and_charges') and return_taxes:
			return party_details

		if not party_details.supplier_gstin:
			return

	if not party_details.place_of_supply: return

	if not party_details.company_gstin: return

	if ((doctype in ("Sales Invoice", "Delivery Note", "Sales Order") and party_details.company_gstin
		and party_details.company_gstin[:2] != party_details.place_of_supply[:2]) or (doctype in ("Purchase Invoice",
		"Purchase Order", "Purchase Receipt") and party_details.supplier_gstin and party_details.supplier_gstin[:2] != party_details.place_of_supply[:2])):
		default_tax = get_tax_template(master_doctype, company, 1, party_details.company_gstin[:2])
	else:
		default_tax = get_tax_template(master_doctype, company, 0, party_details.company_gstin[:2])

	if not default_tax:
		return
	party_details["taxes_and_charges"] = default_tax
	party_details.taxes = get_taxes_and_charges(master_doctype, default_tax)

	if return_taxes:
		return party_details

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

def get_tax_template_for_sez(party_details, master_doctype, company, party_type):

	gst_details = frappe.db.get_value(party_type, {'name': party_details.get(frappe.scrub(party_type))},
			['gst_category', 'export_type'], as_dict=1)

	if gst_details:
		if gst_details.gst_category == 'SEZ' and gst_details.export_type == 'With Payment of Tax':
			default_tax = frappe.db.get_value(master_doctype, {"company": company, "is_inter_state":1, "disabled":0,
				"gst_state": number_state_mapping[party_details.company_gstin[:2]]})

			party_details["taxes_and_charges"] = default_tax
			party_details.taxes = get_taxes_and_charges(master_doctype, default_tax)


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
	if dt != 'Sales Invoice':
		frappe.throw(_('e-Way Bill JSON can only be generated from Sales Invoice'))

	ewaybills = []
	for doc_name in dn:
		doc = frappe.get_doc(dt, doc_name)

		validate_sales_invoice(doc)

		data = frappe._dict({
			"transporterId": "",
			"TotNonAdvolVal": 0,
		})

		data.userGstin = data.fromGstin = doc.company_gstin
		data.supplyType = 'O'

		if doc.gst_category in ['Registered Regular', 'SEZ']:
			data.subSupplyType = 1
		elif doc.gst_category in ['Overseas', 'Deemed Export']:
			data.subSupplyType = 3
		else:
			frappe.throw(_('Unsupported GST Category for e-Way Bill JSON generation'))

		data.docType = 'INV'
		data.docDate = frappe.utils.formatdate(doc.posting_date, 'dd/mm/yyyy')

		company_address = frappe.get_doc('Address', doc.company_address)
		billing_address = frappe.get_doc('Address', doc.customer_address)

		shipping_address = frappe.get_doc('Address', doc.shipping_address_name)

		data = get_address_details(data, doc, company_address, billing_address)

		data.itemList = []
		data.totalValue = doc.total

		data = get_item_list(data, doc)

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
		'version': '1.0.1118',
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
			filename_prefix = re.sub('[^\w_.)( -]', '', docname)

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

def get_address_details(data, doc, company_address, billing_address):
	data.fromPincode = validate_pincode(company_address.pincode, 'Company Address')
	data.fromStateCode = data.actualFromStateCode = validate_state_code(
		company_address.gst_state_number, 'Company Address')

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

	return data

def get_item_list(data, doc):
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
	hsn_wise_charges, hsn_taxable_amount = get_itemised_tax_breakup_data(doc, account_wise=True)
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

def validate_sales_invoice(doc):
	if doc.docstatus != 1:
		frappe.throw(_('e-Way Bill JSON can only be generated from submitted document'))

	if doc.is_return:
		frappe.throw(_('e-Way Bill JSON cannot be generated for Sales Return as of now'))

	if doc.ewaybill:
		frappe.throw(_('e-Way Bill already exists for this document'))

	reqd_fields = ['company_gstin', 'company_address', 'customer_address',
		'shipping_address_name', 'mode_of_transport', 'distance']

	for fieldname in reqd_fields:
		if not doc.get(fieldname):
			frappe.throw(_('{} is required to generate e-Way Bill JSON'.format(
				doc.meta.get_label(fieldname)
			)))

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
def get_gst_accounts(company, account_wise=False):
	gst_accounts = frappe._dict()
	gst_settings_accounts = frappe.get_all("GST Account",
		filters={"parent": "GST Settings", "company": company},
		fields=["cgst_account", "sgst_account", "igst_account", "cess_account"])

	if not gst_settings_accounts and not frappe.flags.in_test:
		frappe.throw(_("Please set GST Accounts in GST Settings"))

	for d in gst_settings_accounts:
		for acc, val in d.items():
			if not account_wise:
				gst_accounts.setdefault(acc, []).append(val)
			elif val:
				gst_accounts[val] = acc

	return gst_accounts

def update_grand_total_for_rcm(doc, method):
	country = frappe.get_cached_value('Company', doc.company, 'country')

	if country != 'India':
		return

	if not doc.total_taxes_and_charges:
		return

	if doc.reverse_charge == 'Y':
		gst_accounts = get_gst_accounts(doc.company)
		gst_account_list = gst_accounts.get('cgst_account') + gst_accounts.get('sgst_account') \
			+ gst_accounts.get('igst_account')

		base_gst_tax = 0
		gst_tax = 0

		for tax in doc.get('taxes'):
			if tax.category not in ("Total", "Valuation and Total"):
				continue

			if flt(tax.base_tax_amount_after_discount_amount) and tax.account_head in gst_account_list:
				base_gst_tax += tax.base_tax_amount_after_discount_amount
				gst_tax += tax.tax_amount_after_discount_amount

		doc.taxes_and_charges_added -= gst_tax
		doc.total_taxes_and_charges -= gst_tax
		doc.base_taxes_and_charges_added -= base_gst_tax
		doc.base_total_taxes_and_charges -= base_gst_tax

		update_totals(gst_tax, base_gst_tax, doc)

def update_totals(gst_tax, base_gst_tax, doc):
	doc.base_grand_total -= base_gst_tax
	doc.grand_total -= gst_tax

	if doc.meta.get_field("rounded_total"):
		if not doc.is_rounded_total_disabled():
			doc.rounded_total = round_based_on_smallest_currency_fraction(doc.grand_total,
				doc.currency, doc.precision("rounded_total"))

			doc.rounding_adjustment += flt(doc.rounded_total - doc.grand_total,
				doc.precision("rounding_adjustment"))

		calculate_outstanding_amount(doc)

	doc.in_words = money_in_words(doc.grand_total, doc.currency)
	doc.base_in_words = money_in_words(doc.base_grand_total, erpnext.get_company_currency(doc.company))
	doc.set_payment_schedule()

def make_regional_gl_entries(gl_entries, doc):
	country = frappe.get_cached_value('Company', doc.company, 'country')

	if country != 'India':
		return gl_entries

	if doc.reverse_charge == 'Y':
		gst_accounts = get_gst_accounts(doc.company)
		gst_account_list = gst_accounts.get('cgst_account') + gst_accounts.get('sgst_account') \
			+ gst_accounts.get('igst_account')

		for tax in doc.get('taxes'):
			if tax.category not in ("Total", "Valuation and Total"):
				continue

			dr_or_cr = "credit" if tax.add_deduct_tax == "Add" else "debit"
			if flt(tax.base_tax_amount_after_discount_amount) and tax.account_head in gst_account_list:
				account_currency = get_account_currency(tax.account_head)

				gl_entries.append(doc.get_gl_dict(
					{
						"account": tax.account_head,
						"cost_center": tax.cost_center,
						"posting_date": doc.posting_date,
						"against": doc.supplier,
						dr_or_cr: tax.base_tax_amount_after_discount_amount,
						dr_or_cr + "_in_account_currency": tax.base_tax_amount_after_discount_amount \
							if account_currency==doc.company_currency \
							else tax.tax_amount_after_discount_amount
					}, account_currency, item=tax)
				)

	return gl_entries