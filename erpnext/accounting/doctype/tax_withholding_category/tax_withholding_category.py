# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt
from erpnext.accounting.utils import get_fiscal_year

class TaxWithholdingCategory(Document):
	pass

def get_party_tax_withholding_details(ref_doc):
	tax_withholding_category = frappe.db.get_value('Supplier', ref_doc.supplier, 'tax_withholding_category')
	if not tax_withholding_category:
		return

	fy = get_fiscal_year(ref_doc.posting_date, company=ref_doc.company)
	tax_details = get_tax_withholding_details(tax_withholding_category, fy[0], ref_doc.company)
	if not tax_details:
		frappe.throw(_('Please set associated account in Tax Withholding Category {0} against Company {1}')
			.format(tax_withholding_category, ref_doc.company))
	tds_amount = get_tds_amount(ref_doc, tax_details, fy)
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
				"description": tax_withholding.category_name
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

def get_tds_amount(ref_doc, tax_details, fiscal_year_details):
	fiscal_year, year_start_date, year_end_date = fiscal_year_details
	tds_amount = 0

	def _get_tds():
		tds_amount = 0
		if not tax_details.threshold or ref_doc.net_total >= tax_details.threshold:
			tds_amount = ref_doc.net_total * tax_details.rate / 100
		return tds_amount

	if tax_details.cumulative_threshold:
		entries = frappe.db.sql("""
			select voucher_no, credit
			from `tabGL Entry`
			where party=%s and fiscal_year=%s and credit > 0
		""", (ref_doc.supplier, fiscal_year), as_dict=1)

		supplier_credit_amount = flt(sum([d.credit for d in entries]))

		vouchers = [d.voucher_no for d in entries]
		vouchers += get_advance_vouchers(ref_doc.supplier, fiscal_year)

		tds_deducted = 0
		if vouchers:
			tds_deducted = flt(frappe.db.sql("""
				select sum(credit)
				from `tabGL Entry`
				where account=%s and fiscal_year=%s and credit > 0
					and voucher_no in ({0})
			""".format(', '.join(["'%s'" % d for d in vouchers])),
				(tax_details.account_head, fiscal_year))[0][0])

		debit_note_amount = get_debit_note_amount(ref_doc.supplier, year_start_date, year_end_date)

		total_invoiced_amount = supplier_credit_amount + tds_deducted \
			+ flt(ref_doc.net_total) - debit_note_amount
		if total_invoiced_amount >= tax_details.cumulative_threshold:
			total_applicable_tds = total_invoiced_amount * tax_details.rate / 100
			tds_amount = min(total_applicable_tds - tds_deducted, ref_doc.net_total)
		else:
			tds_amount = _get_tds()
	else:
		tds_amount = _get_tds()

	return tds_amount

def get_advance_vouchers(supplier, fiscal_year=None, company=None, from_date=None, to_date=None):
	condition = "fiscal_year=%s" % fiscal_year
	if from_date and to_date:
		condition = "company=%s and posting_date between %s and %s" % (company, from_date, to_date)

	return frappe.db.sql_list("""
		select distinct voucher_no
		from `tabGL Entry`
		where party=%s and %s and debit > 0
	""", (supplier, condition))

def get_debit_note_amount(supplier, year_start_date, year_end_date, company=None):
	condition = ""
	if company:
		condition = " and company=%s " % company

	return flt(frappe.db.sql("""
		select abs(sum(net_total))
		from `tabPurchase Invoice`
		where supplier=%s %s and is_return=1 and docstatus=1
			and posting_date between %s and %s
	""", (supplier, condition, year_start_date, year_end_date)))
