from __future__ import unicode_literals
import json
import frappe
import itertools
import erpnext
from six import iteritems
from frappe import _
from frappe.utils import get_datetime
from erpnext.hr.doctype.attendance.attendance import get_month_map
from erpnext.regional.qatar.utils import create_and_attach_file, get_salary_slip, get_total_component_amount, set_missing_fields_data
from frappe.utils import flt, round_based_on_smallest_currency_fraction, money_in_words
from erpnext.regional.doctype.salary_information_file.salary_information_file import get_company_bank_details
from erpnext.controllers.taxes_and_totals import get_itemised_tax

def update_itemised_tax_data(doc):
	if not doc.taxes: return

	itemised_tax = get_itemised_tax(doc.taxes)

	for row in doc.items:
		tax_rate = 0.0
		item_tax_rate = 0.0

		if row.item_tax_rate:
			item_tax_rate = frappe.parse_json(row.item_tax_rate)

		# First check if tax rate is present
		# If not then look up in item_wise_tax_detail
		if item_tax_rate:
			for account, rate in iteritems(item_tax_rate):
				tax_rate += rate
		elif row.item_code and itemised_tax.get(row.item_code):
			tax_rate = sum([tax.get('tax_rate', 0) for d, tax in itemised_tax.get(row.item_code).items()])

		row.tax_rate = flt(tax_rate, row.precision("tax_rate"))
		row.tax_amount = flt((row.net_amount * tax_rate) / 100, row.precision("net_amount"))
		row.total_amount = flt((row.net_amount + row.tax_amount), row.precision("total_amount"))

def get_account_currency(account):
	"""Helper function to get account currency."""
	if not account:
		return
	def generator():
		account_currency, company = frappe.get_cached_value(
			"Account",
			account,
			["account_currency","company"]
		)
		if not account_currency:
			account_currency = frappe.get_cached_value('Company',  company,  "default_currency")

		return account_currency

	return frappe.local_cache("account_currency", account, generator)

def get_tax_accounts(company):
	"""Get the list of tax accounts for a specific company."""
	tax_accounts_dict = frappe._dict()
	tax_accounts_list = frappe.get_all("UAE VAT Account",
		filters={"parent": company},
		fields=["Account"]
		)

	if not tax_accounts_list and not frappe.flags.in_test:
		frappe.throw(_('Please set Vat Accounts for Company: "{0}" in UAE VAT Settings').format(company))
	for tax_account in tax_accounts_list:
		for account, name in tax_account.items():
			tax_accounts_dict[name] = name

	return tax_accounts_dict

def update_grand_total_for_rcm(doc, method):
	"""If the Reverse Charge is Applicable subtract the tax amount from the grand total and update in the form."""
	country = frappe.get_cached_value('Company', doc.company, 'country')

	if country != 'United Arab Emirates':
		return

	if not doc.total_taxes_and_charges:
		return

	if doc.reverse_charge == 'Y':
		tax_accounts = get_tax_accounts(doc.company)

		base_vat_tax = 0
		vat_tax = 0

		for tax in doc.get('taxes'):
			if tax.category not in ("Total", "Valuation and Total"):
				continue

			if flt(tax.base_tax_amount_after_discount_amount) and tax.account_head in tax_accounts:
				base_vat_tax += tax.base_tax_amount_after_discount_amount
				vat_tax += tax.tax_amount_after_discount_amount

		doc.taxes_and_charges_added -= vat_tax
		doc.total_taxes_and_charges -= vat_tax
		doc.base_taxes_and_charges_added -= base_vat_tax
		doc.base_total_taxes_and_charges -= base_vat_tax

		update_totals(vat_tax, base_vat_tax, doc)

def update_totals(vat_tax, base_vat_tax, doc):
	"""Update the grand total values in the form."""
	doc.base_grand_total -= base_vat_tax
	doc.grand_total -= vat_tax

	if doc.meta.get_field("rounded_total"):

		if doc.is_rounded_total_disabled():
			doc.outstanding_amount = doc.grand_total

		else:
			doc.rounded_total = round_based_on_smallest_currency_fraction(doc.grand_total,
				doc.currency, doc.precision("rounded_total"))
			doc.rounding_adjustment = flt(doc.rounded_total - doc.grand_total,
				doc.precision("rounding_adjustment"))
			doc.outstanding_amount = doc.rounded_total or doc.grand_total

	doc.in_words = money_in_words(doc.grand_total, doc.currency)
	doc.base_in_words = money_in_words(doc.base_grand_total, erpnext.get_company_currency(doc.company))
	doc.set_payment_schedule()

def make_regional_gl_entries(gl_entries, doc):
	"""Hooked to make_regional_gl_entries in Purchase Invoice.It appends the region specific general ledger entries to the list of GL Entries."""
	country = frappe.get_cached_value('Company', doc.company, 'country')

	if country != 'United Arab Emirates':
		return gl_entries

	if doc.reverse_charge == 'Y':
		tax_accounts = get_tax_accounts(doc.company)
		for tax in doc.get('taxes'):
			if tax.category not in ("Total", "Valuation and Total"):
				continue
			gl_entries = make_gl_entry(tax, gl_entries, doc, tax_accounts)
	return gl_entries

def make_gl_entry(tax, gl_entries, doc, tax_accounts):
	dr_or_cr = "credit" if tax.add_deduct_tax == "Add" else "debit"
	if flt(tax.base_tax_amount_after_discount_amount)  and tax.account_head in tax_accounts:
		account_currency = get_account_currency(tax.account_head)

		gl_entries.append(doc.get_gl_dict({
				"account": tax.account_head,
				"cost_center": tax.cost_center,
				"posting_date": doc.posting_date,
				"against": doc.supplier,
				dr_or_cr: tax.base_tax_amount_after_discount_amount,
				dr_or_cr + "_in_account_currency": tax.base_tax_amount_after_discount_amount \
					if account_currency==doc.company_currency \
					else tax.tax_amount_after_discount_amount
			}, account_currency, item=tax
		))
	return gl_entries


def validate_returns(doc, method):
	"""Standard Rated expenses should not be set when Reverse Charge Applicable is set."""
	country = frappe.get_cached_value('Company', doc.company, 'country')
	if country != 'United Arab Emirates':
		return
	if doc.reverse_charge == 'Y' and  flt(doc.recoverable_standard_rated_expenses) != 0:
		frappe.throw(_(
			"Recoverable Standard Rated expenses should not be set when Reverse Charge Applicable is Y"
		))

def validate_bank_details_and_generate_csv(doc, method):
	if frappe.get_cached_value("Company", doc.company, "country") == "United Arab Emirates":
		company_bank_details = get_company_bank_details(doc.company)

	if not len(company_bank_details):
		frappe.throw(_("Please create Bank Account for Company: {0}").format(doc.company))

	company_bank_details = company_bank_details[0]

	employee_records, missing_fields_for_employees = get_employee_record_details_row(doc.month, doc.year, doc.company)
	salary_control_record = get_salary_control_record(doc, company_bank_details, len(employee_records))

	genrate_csv(doc.name, employee_records, salary_control_record)
	create_and_attach_file(doc)

	update_document = 0
	if len(employee_records) != doc.number_of_records:
		doc.missing_fields = None
		doc.number_of_records = len(employee_records)
		update_document = 1

	if doc.missing_fields != json.dumps(missing_fields_for_employees):
		doc.missing_fields = json.dumps(missing_fields_for_employees)
		if missing_fields_for_employees:
			frappe.msgprint(_("Mandatory Fields Missing for employee, Reload page to check"))
		update_document = 1

	if update_document == 1:
		doc.save()

def get_employee_record_details_row(month, year, company):
	employee_records = []
	missing_fields_for_employees= {}

	month_abbr = get_month_map()[month]
	salary_slips = get_salary_slip(month_abbr, year, company)

	if not len(salary_slips):
		frappe.throw(_("Salary Slip not found {0}, {1}").format(month, year))

	data = itertools.groupby(salary_slips, key=lambda x: (x['employee']))

	for employee, group in data:
		print(employee, group)
		group = list(group)

		employee_details = get_employee_details(employee)

		if not (employee_details.agent_id):
			missing_fields_for_employees = set_missing_fields_data(employee, "Agent Id", missing_fields_for_employees)

		if not (employee_details.bank_ac_no):
			missing_fields_for_employees = set_missing_fields_data(employee, "Bank A/c No.", missing_fields_for_employees)

		if not (employee_details.residential_id):
			missing_fields_for_employees = set_missing_fields_data(employee, "Residential Id", missing_fields_for_employees)

		fixed_components = get_fixed_salary_component()
		variable_components = get_variable_salary_component()

		fixed_compoenet_amount = get_total_component_amount(group, fixed_components)
		variable_component_amount = get_total_component_amount(group, variable_components)

		row = [
			employee_details.residential_id,
			employee_details.agent_id,
			employee_details.bank_ac_no,
			get_datetime(group[0]["start_date"]).strftime("%Y-%m-%d"),
			get_datetime(group[0]["end_date"]).strftime("%Y-%m-%d"),
			group[0]["total_working_days"],
			fixed_compoenet_amount,
			variable_component_amount,
			group[0]["leave_without_pay"]
		]
		employee_records.append(row)
	return employee_records, missing_fields_for_employees

def get_salary_control_record(doc, company_bank_details, no_of_records):
	bank_short_name = frappe.db.get_value("Bank", company_bank_details.bank, "bank_short_name")

	if not bank_short_name:
		frappe.throw(_("Enter Bank Short Name/Abbr. for Bank: {0}").format(company_bank_details.bank))

	month = get_month_map()[doc.month]

	# format: MMYYY
	salary_month_and_year = (str(month) if month>10 else "0"+str(month)) + str(doc.year)

	row = [
		doc.employer_establishment_id,
		bank_short_name,
		company_bank_details.iban,
		get_datetime(doc.creation_date).strftime("%Y-%m-%d"),
		get_datetime(doc.creation_time).strftime("%H%M"),
		salary_month_and_year,
		no_of_records,
		frappe.db.get_value("Company", doc.company, "default_currency"),
		frappe.db.get_value("Company", doc.company, "employer_reference_number") or ""
	]
	return row

def genrate_csv(name ,employee_records, salary_control_record):
	import csv
	site_path = frappe.utils.get_site_path()

	with open(site_path + '/public/files/'+name+'.csv', 'w+', newline='') as file:
		writer = csv.writer(file)

		for record in employee_records:
			record.insert(0, "EDR")
			writer.writerow(record)

		salary_control_record.insert(0, "SDR")
		writer.writerow(salary_control_record)


def get_fixed_salary_component():
	return frappe.get_all("Salary Component", filters = {"is_fixed_component": 1}, as_list=1)

def get_variable_salary_component():
	return frappe.get_all("Salary Component", filters = {"is_variable_component": 1}, as_list=1)

def get_employee_details(employee):
	return frappe.db.get_value("Employee", employee, ["residential_id", "agent_id",
		"bank_abbr", "bank_ac_no"], as_dict=1)