# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate
from erpnext.accounts.utils import get_fiscal_year

class TaxWithholdingCategory(Document):
	pass

def get_party_details(ref_doc):
	party_type, party = '', ''

	if ref_doc.doctype == 'Sales Invoice':
		party_type = 'Customer'
		party = ref_doc.customer
	else:
		party_type = 'Supplier'
		party = ref_doc.supplier
	
	return party_type, party

def get_party_tax_withholding_details(ref_doc, tax_withholding_category=None):
	pan_no = ''
	parties = []
	party_type, party = get_party_details(ref_doc)

	if not tax_withholding_category:
		tax_withholding_category, pan_no = frappe.db.get_value(party_type, party, ['tax_withholding_category', 'pan'])

	if not tax_withholding_category:
		return

	# if tax_withholding_category passed as an argument but not pan_no
	if not pan_no:
		pan_no = frappe.db.get_value(party_type, party, 'pan')

	# Get others suppliers with the same PAN No
	if pan_no:
		parties = frappe.get_all(party_type, filters={ 'pan': pan_no }, pluck='name')

	if not parties:
		parties.append(party)

	fiscal_year = get_fiscal_year(ref_doc.posting_date, company=ref_doc.company)
	tax_details = get_tax_withholding_details(tax_withholding_category, fiscal_year[0], ref_doc.company)

	if not tax_details:
		frappe.throw(_('Please set associated account in Tax Withholding Category {0} against Company {1}')
			.format(tax_withholding_category, ref_doc.company))

	tax_amount = get_tax_amount(
		party_type, parties,
		ref_doc, tax_details,
		fiscal_year, pan_no
	)

	tax_row = get_tax_row(tax_details, tax_amount)

	return tax_row

def get_tax_withholding_details(tax_withholding_category, fiscal_year, company):
	tax_withholding = frappe.get_doc("Tax Withholding Category", tax_withholding_category)

	tax_rate_detail = get_tax_withholding_rates(tax_withholding, fiscal_year)

	for account_detail in tax_withholding.accounts:
		if company == account_detail.company:
			return frappe._dict({
				"account_head": account_detail.account,
				"rate": tax_rate_detail.tax_withholding_rate,
				"threshold": tax_rate_detail.single_threshold,
				"cumulative_threshold": tax_rate_detail.cumulative_threshold,
				"description": tax_withholding.category_name if tax_withholding.category_name else tax_withholding_category
			})

def get_tax_withholding_rates(tax_withholding, fiscal_year):
	# returns the row that matches with the fiscal year from posting date
	for rate in tax_withholding.rates:
		if rate.fiscal_year == fiscal_year:
			return rate

	frappe.throw(_("No Tax Withholding data found for the current Fiscal Year."))

def get_tax_row(tax_details, tax_amount):
	return {
		"category": "Total",
		"add_deduct_tax": "Deduct",
		"charge_type": "Actual",
		"account_head": tax_details.account_head,
		"description": tax_details.description,
		"tax_amount": tax_amount
	}

def get_lower_deduction_certificate(fiscal_year, pan_no):
	ldc_name = frappe.db.get_value('Lower Deduction Certificate', { 'pan_no': pan_no, 'fiscal_year': fiscal_year }, 'name')
	if ldc_name:
		return frappe.get_doc('Lower Deduction Certificate', ldc_name)

def get_tax_amount(party_type, parties, ref_doc, tax_details, fiscal_year_details, pan_no=None):
	fiscal_year = fiscal_year_details[0]

	vouchers = get_invoice_vouchers(parties, fiscal_year, ref_doc.company, party_type=party_type) or [""]
	advance_vouchers = get_advance_vouchers(parties, fiscal_year, ref_doc.company, party_type=party_type)
	tax_vouchers = vouchers + advance_vouchers

	tax_deducted = 0
	dr_or_cr = 'credit' if party_type == 'Supplier' else 'debit'
	if tax_vouchers:
		filters = {
			dr_or_cr: ['>', 0],
			'account': tax_details.account_head,
			'fiscal_year': fiscal_year,
			'voucher_no': ['in', tax_vouchers],
			'is_cancelled': 0
		}
		field = "sum({})".format(dr_or_cr)

		tax_deducted = frappe.db.get_value('GL Entry', filters, field) or 0.0

	tax_amount = 0
	if party_type == 'Supplier':
		net_total = ref_doc.net_total
		posting_date = ref_doc.posting_date
		ldc = get_lower_deduction_certificate(fiscal_year, pan_no)

		if tax_deducted:
			if ldc:
				tax_amount = get_tds_amount_from_ldc(ldc, parties, fiscal_year, pan_no, tax_details, posting_date, net_total)
			else:
				tax_amount = net_total * tax_details.rate / 100 if net_total > 0 else 0
		else:
			tax_amount = get_tds_amount(
				ldc, parties, ref_doc, tax_details,
				fiscal_year_details, vouchers
			)

	return tax_amount

def get_invoice_vouchers(parties, fiscal_year, company, party_type='Supplier'):
	dr_or_cr = 'credit' if party_type == 'Supplier' else 'debit'

	filters = {
		dr_or_cr: ['>', 0],
		'company': company,
		'party_type': party_type,
		'party': ['in', parties],
		'fiscal_year': fiscal_year,
		'is_opening': 'No',
		'is_cancelled': 0
	}

	return frappe.get_all('GL Entry', filters=filters, distinct=1, pluck="voucher_no")

def get_advance_vouchers(parties, fiscal_year=None, company=None, from_date=None, to_date=None, party_type='Supplier'):
	# for advance vouchers, debit and credit is reversed
	dr_or_cr = 'debit' if party_type == 'Supplier' else 'credit'

	filters = {
		dr_or_cr: ['>', 0],
		'party_type': party_type,
		'party': ['in', parties],
		'is_opening': 'No',
		'is_cancelled': 0
	}

	if fiscal_year:
		filters['fiscal_year'] = fiscal_year
	if company:
		filters['company'] = company
	if from_date and to_date:
		filters['posting_date'] = ['between', (from_date, to_date)]

	return frappe.get_all('GL Entry', filters=filters, distinct=1, pluck='voucher_no')

def get_tds_amount(ldc, parties, ref_doc, tax_details, fiscal_year_details, vouchers):
	tds_amount = 0

	supp_credit_amt = frappe.db.get_value('Purchase Invoice', {
		'name': ('in', vouchers), 'docstatus': 1, 'apply_tds': 1
	}, 'sum(net_total)') or 0.0

	supp_jv_credit_amt = frappe.db.get_value('Journal Entry Account', {
		'parent': ('in', vouchers), 'docstatus': 1,
		'party': ('in', parties), 'reference_type': ('!=', 'Purchase Invoice')
	}, 'sum(credit_in_account_currency)') or 0.0

	supp_credit_amt += supp_jv_credit_amt
	supp_credit_amt += ref_doc.net_total

	debit_note_amount = get_debit_note_amount(parties, fiscal_year_details, ref_doc.company)
	supp_credit_amt -= debit_note_amount

	threshold = tax_details.get('threshold', 0)
	cumulative_threshold = tax_details.get('cumulative_threshold', 0)

	if ((threshold and supp_credit_amt >= threshold) or (cumulative_threshold and supp_credit_amt >= cumulative_threshold)):
		if ldc and is_valid_certificate(
			ldc.valid_from, ldc.valid_upto,
			ref_doc.posting_date, tax_deducted,
			net_total, ldc.certificate_limit
		):
			tds_amount = get_ltds_amount(supp_credit_amt, 0, ldc.certificate_limit, ldc.rate, tax_details)
		else:
			tds_amount = supp_credit_amt * tax_details.rate / 100 if supp_credit_amt > 0 else 0

	return tds_amount

def get_tds_amount_from_ldc(ldc, parties, fiscal_year, pan_no, tax_details, posting_date, net_total):
	tds_amount = 0
	limit_consumed = frappe.db.get_value('Purchase Invoice', {
		'supplier': ('in', parties),
		'apply_tds': 1,
		'docstatus': 1
	}, 'sum(net_total)')

	if is_valid_certificate(
		ldc.valid_from, ldc.valid_upto,
		posting_date, limit_consumed,
		net_total, ldc.certificate_limit
	):
		tds_amount = get_ltds_amount(net_total, limit_consumed, ldc.certificate_limit, ldc.rate, tax_details)
	
	return tds_amount

def get_debit_note_amount(suppliers, fiscal_year_details, company=None):
	_, year_start_date, year_end_date = fiscal_year_details

	filters = {
		'supplier': ['in', suppliers],
		'is_return': 1,
		'docstatus': 1,
		'posting_date': ['between', (year_start_date, year_end_date)]
	}
	fields = ['abs(sum(net_total)) as net_total']

	if company:
		filters['company'] = company

	return frappe.get_all('Purchase Invoice', filters, fields)[0].get('net_total') or 0.0

def get_ltds_amount(current_amount, deducted_amount, certificate_limit, rate, tax_details):
	if current_amount < (certificate_limit - deducted_amount):
		return current_amount * rate/100
	else:
		ltds_amount = (certificate_limit - deducted_amount)
		tds_amount = current_amount - ltds_amount

		return ltds_amount * rate/100 + tds_amount * tax_details.rate/100

def is_valid_certificate(valid_from, valid_upto, posting_date, deducted_amount, current_amount, certificate_limit):
	valid = False

	if ((getdate(valid_from) <= getdate(posting_date) <= getdate(valid_upto)) and
			certificate_limit > deducted_amount):
		valid = True

	return valid
