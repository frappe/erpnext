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

def get_party_tax_withholding_details(ref_doc, tax_withholding_category=None):

	pan_no = ''
	suppliers = []

	if not tax_withholding_category:
		tax_withholding_category, pan_no = frappe.db.get_value('Supplier', ref_doc.supplier, ['tax_withholding_category', 'pan'])

	if not tax_withholding_category:
		return

	if not pan_no:
		pan_no = frappe.db.get_value('Supplier', ref_doc.supplier, 'pan')

	# Get others suppliers with the same PAN No
	if pan_no:
		suppliers = [d.name for d in  frappe.get_all('Supplier', fields=['name'], filters={'pan': pan_no})]

	if not suppliers:
		suppliers.append(ref_doc.supplier)

	fy = get_fiscal_year(ref_doc.posting_date, company=ref_doc.company)
	tax_details = get_tax_withholding_details(tax_withholding_category, fy[0], ref_doc.company)
	if not tax_details:
		frappe.throw(_('Please set associated account in Tax Withholding Category {0} against Company {1}')
			.format(tax_withholding_category, ref_doc.company))

	tds_amount = get_tds_amount(suppliers, ref_doc.net_total, ref_doc.company,
		tax_details, fy,  ref_doc.posting_date, pan_no)

	tax_row = get_tax_row(tax_details, tds_amount)

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

def get_tax_row(tax_details, tds_amount):

	return {
		"category": "Total",
		"add_deduct_tax": "Deduct",
		"charge_type": "Actual",
		"account_head": tax_details.account_head,
		"description": tax_details.description,
		"tax_amount": tds_amount
	}

def get_tds_amount(suppliers, net_total, company, tax_details, fiscal_year_details, posting_date, pan_no=None):
	fiscal_year, year_start_date, year_end_date = fiscal_year_details
	tds_amount = 0
	tds_deducted = 0

	def _get_tds(amount, rate):
		if amount <= 0:
			return 0

		return amount * rate / 100

	ldc_name = frappe.db.get_value('Lower Deduction Certificate',
		{
			'pan_no': pan_no,
			'fiscal_year': fiscal_year
		}, 'name')
	ldc = ''

	if ldc_name:
		ldc = frappe.get_doc('Lower Deduction Certificate', ldc_name)

	entries = frappe.db.sql("""
			select voucher_no, credit
			from `tabGL Entry`
			where company = %s and
			party in %s and fiscal_year=%s and credit > 0
			and is_opening = 'No'
		""", (company, tuple(suppliers), fiscal_year), as_dict=1)

	vouchers = [d.voucher_no for d in entries]
	advance_vouchers = get_advance_vouchers(suppliers, fiscal_year=fiscal_year, company=company)

	tds_vouchers = vouchers + advance_vouchers

	if tds_vouchers:
		tds_deducted = frappe.db.sql("""
			SELECT sum(credit) FROM `tabGL Entry`
			WHERE
				account=%s and fiscal_year=%s and credit > 0
				and voucher_no in ({0})""". format(','.join(['%s'] * len(tds_vouchers))),
				((tax_details.account_head, fiscal_year) + tuple(tds_vouchers)))

		tds_deducted = tds_deducted[0][0] if tds_deducted and tds_deducted[0][0] else 0

	if tds_deducted:
		if ldc:
			limit_consumed = frappe.db.get_value('Purchase Invoice',
				{
					'supplier': ('in', suppliers),
					'apply_tds': 1,
					'docstatus': 1
				}, 'sum(net_total)')

		if ldc and is_valid_certificate(ldc.valid_from, ldc.valid_upto, posting_date, limit_consumed, net_total,
			ldc.certificate_limit):

			tds_amount = get_ltds_amount(net_total, limit_consumed, ldc.certificate_limit, ldc.rate, tax_details)
		else:
			tds_amount = _get_tds(net_total, tax_details.rate)
	else:
		supplier_credit_amount = frappe.get_all('Purchase Invoice',
			fields = ['sum(net_total)'],
			filters = {'name': ('in', vouchers), 'docstatus': 1, "apply_tds": 1}, as_list=1)

		supplier_credit_amount = (supplier_credit_amount[0][0]
			if supplier_credit_amount and supplier_credit_amount[0][0] else 0)

		jv_supplier_credit_amt = frappe.get_all('Journal Entry Account',
			fields = ['sum(credit_in_account_currency)'],
			filters = {
				'parent': ('in', vouchers), 'docstatus': 1,
				'party': ('in', suppliers),
				'reference_type': ('not in', ['Purchase Invoice'])
			}, as_list=1)

		supplier_credit_amount += (jv_supplier_credit_amt[0][0]
			if jv_supplier_credit_amt and jv_supplier_credit_amt[0][0] else 0)

		supplier_credit_amount += net_total

		debit_note_amount = get_debit_note_amount(suppliers, year_start_date, year_end_date)
		supplier_credit_amount -= debit_note_amount

		if ((tax_details.get('threshold', 0) and supplier_credit_amount >= tax_details.threshold)
			or (tax_details.get('cumulative_threshold', 0) and supplier_credit_amount >= tax_details.cumulative_threshold)):

			if ldc and is_valid_certificate(ldc.valid_from, ldc.valid_upto, posting_date, tds_deducted, net_total,
				ldc.certificate_limit):
				tds_amount = get_ltds_amount(supplier_credit_amount, 0, ldc.certificate_limit, ldc.rate,
					tax_details)
			else:
				tds_amount = _get_tds(supplier_credit_amount, tax_details.rate)

	return tds_amount

def get_advance_vouchers(suppliers, fiscal_year=None, company=None, from_date=None, to_date=None):
	condition = "fiscal_year=%s" % fiscal_year

	if company:
		condition += "and company =%s" % (company)
	if from_date and to_date:
		condition += "and posting_date between %s and %s" % (from_date, to_date)

	## Appending the same supplier again if length of suppliers list is 1
	## since tuple of single element list contains None, For example ('Test Supplier 1', )
	## and the below query fails
	if len(suppliers) == 1:
		suppliers.append(suppliers[0])

	return frappe.db.sql_list("""
		select distinct voucher_no
		from `tabGL Entry`
		where party in %s and %s and debit > 0
		and is_opening = 'No'
	""", (tuple(suppliers), condition)) or []

def get_debit_note_amount(suppliers, year_start_date, year_end_date, company=None):
	condition = "and 1=1"
	if company:
		condition = " and company=%s " % company

	if len(suppliers) == 1:
		suppliers.append(suppliers[0])

	return flt(frappe.db.sql("""
		select abs(sum(net_total))
		from `tabPurchase Invoice`
		where supplier in %s and is_return=1 and docstatus=1
			and posting_date between %s and %s %s
	""", (tuple(suppliers), year_start_date, year_end_date, condition)))

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
