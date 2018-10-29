import frappe, re
from frappe import _
from frappe.utils import cstr, flt, date_diff, getdate
from erpnext.regional.india import states, state_numbers
from erpnext.controllers.taxes_and_totals import get_itemised_tax, get_itemised_taxable_amount
from erpnext.controllers.accounts_controller import get_taxes_and_charges
from erpnext.hr.utils import get_salary_assignment
from erpnext.hr.doctype.salary_structure.salary_structure import make_salary_slip

def validate_gstin_for_india(doc, method):
	if not hasattr(doc, 'gstin'):
		return

	if doc.gstin:
		doc.gstin = doc.gstin.upper()
		if doc.gstin not in ["NA", "na"]:
			p = re.compile("[0-9]{2}[a-zA-Z]{5}[0-9]{4}[a-zA-Z]{1}[1-9A-Za-z]{1}[Z]{1}[0-9a-zA-Z]{1}")
			if not p.match(doc.gstin):
				frappe.throw(_("Invalid GSTIN or Enter NA for Unregistered"))

	if not doc.gst_state:
		if doc.state in states:
			doc.gst_state = doc.state

	if doc.gst_state:
		doc.gst_state_number = state_numbers[doc.gst_state]
		if doc.gstin and doc.gstin != "NA" and doc.gst_state_number != doc.gstin[:2]:
			frappe.throw(_("First 2 digits of GSTIN should match with State number {0}")
				.format(doc.gst_state_number))

def get_itemised_tax_breakup_header(item_doctype, tax_accounts):
	if frappe.get_meta(item_doctype).has_field('gst_hsn_code'):
		return [_("HSN/SAC"), _("Taxable Amount")] + tax_accounts
	else:
		return [_("Item"), _("Taxable Amount")] + tax_accounts

def get_itemised_tax_breakup_data(doc):
	itemised_tax = get_itemised_tax(doc.taxes)

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
		for tax_account, tax_detail in taxes.items():
			hsn_tax[hsn_code].setdefault(tax_account, {"tax_rate": 0, "tax_amount": 0})
			hsn_tax[hsn_code][tax_account]["tax_rate"] = tax_detail.get("tax_rate")
			hsn_tax[hsn_code][tax_account]["tax_amount"] += tax_detail.get("tax_amount")

	# set taxable amount
	hsn_taxable_amount = frappe._dict()
	for item, taxable_amount in itemised_taxable_amount.items():
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

def get_place_of_supply(out, doctype):
	if not frappe.get_meta('Address').has_field('gst_state'): return

	if doctype in ("Sales Invoice", "Delivery Note"):
		address_name = out.shipping_address_name or out.customer_address
	elif doctype == "Purchase Invoice":
		address_name = out.shipping_address or out.supplier_address

	if address_name:
		address = frappe.db.get_value("Address", address_name, ["gst_state", "gst_state_number"], as_dict=1)
		if address and address.gst_state and address.gst_state_number:
			return cstr(address.gst_state_number) + "-" + cstr(address.gst_state)

def get_regional_address_details(out, doctype, company):
	out.place_of_supply = get_place_of_supply(out, doctype)

	if not out.place_of_supply: return

	if doctype in ("Sales Invoice", "Delivery Note"):
		master_doctype = "Sales Taxes and Charges Template"
		if not out.company_gstin:
			return
	elif doctype == "Purchase Invoice":
		master_doctype = "Purchase Taxes and Charges Template"
		if not out.supplier_gstin:
			return

	if ((doctype in ("Sales Invoice", "Delivery Note") and out.company_gstin
		and out.company_gstin[:2] != out.place_of_supply[:2]) or (doctype == "Purchase Invoice"
		and out.supplier_gstin and out.supplier_gstin[:2] != out.place_of_supply[:2])):
		default_tax = frappe.db.get_value(master_doctype, {"company": company, "is_inter_state":1, "disabled":0})
	else:
		default_tax = frappe.db.get_value(master_doctype, {"company": company, "disabled":0, "is_default": 1})

	if not default_tax:
		return
	out["taxes_and_charges"] = default_tax
	out.taxes = get_taxes_and_charges(master_doctype, default_tax)

def calculate_annual_eligible_hra_exemption(doc):
	basic_component = frappe.get_cached_value('Company',  doc.company,  "basic_component")
	hra_component = frappe.get_cached_value('Company',  doc.company,  "hra_component")
	annual_exemption, monthly_exemption, hra_amount = 0, 0, 0
	if hra_component and basic_component:
		assignment = get_salary_assignment(doc.employee, getdate())
		if assignment and frappe.db.exists("Salary Detail", {
			"parent": assignment.salary_structure,
			"salary_component": hra_component, "parentfield": "earnings"}):
			basic_amount, hra_amount = get_component_amt_from_salary_slip(doc.employee,
				assignment.salary_structure, basic_component, hra_component)
			if hra_amount:
				if doc.monthly_house_rent:
					annual_exemption = calculate_hra_exemption(assignment.salary_structure,
									basic_amount, hra_amount, doc.monthly_house_rent,
									doc.rented_in_metro_city)
					if annual_exemption > 0:
						monthly_exemption = annual_exemption / 12
					else:
						annual_exemption = 0
	return {"hra_amount": hra_amount, "annual_exemption": annual_exemption, "monthly_exemption": monthly_exemption}

def get_component_amt_from_salary_slip(employee, salary_structure, basic_component, hra_component):
	salary_slip = make_salary_slip(salary_structure, employee=employee)
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
	proofs = frappe.db.sql("""select name from `tabEmployee Tax Exemption Proof Submission`
		where docstatus=1 and employee='{0}' and payroll_period='{1}' and
		(rented_from_date between '{2}' and '{3}' or rented_to_date between
		'{2}' and '{3}')""".format(doc.employee, doc.payroll_period,
		doc.rented_from_date, doc.rented_to_date))
	if proofs:
		frappe.throw(_("House rent paid days overlap with {0}").format(proofs[0][0]))

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
