# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt
from erpnext.accounts.utils import get_fiscal_year

class TaxWithholdingCategory(Document):
	pass
tax_data = []
def get_party_tax_withholding_details(ref_doc):
#	tax_withholding_category = frappe.db.get_value('Supplier', ref_doc.supplier, 'tax_withholding_category')
	tax_withholding_category = ""
	tax_row = []
	tax_withholding_category_item = get_unique_tax_withholding_category(ref_doc.items)
	for key, value in tax_withholding_category_item.iteritems():
		tax_withholding_category = value.tax_withholding_category
		net_amount = value.net_amount
		if not tax_withholding_category:
			return
		fy = get_fiscal_year(ref_doc.posting_date, company=ref_doc.company)
		tax_details = get_tax_withholding_details(tax_withholding_category, fy[0], ref_doc.company)
		if not tax_details:
			frappe.throw(_('Please set associated account in Tax Withholding Category {0} against Company {1}')
				.format(tax_withholding_category, ref_doc.company))
		tds_amount = get_tds_amount(tax_withholding_category,net_amount,ref_doc, tax_details, fy)
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
				"description": tax_withholding.category_name,
				"tax_rule_start_date":tax_rate_detail.tax_rule_start_date,
				"tax_rule_end_date": tax_rate_detail.tax_rule_end_date,
				"name":tax_withholding.name
			})

def get_tax_withholding_rates(tax_withholding, fiscal_year):
	# returns the row that matches with the fiscal year from posting date
	for rate in tax_withholding.rates:
		if rate.fiscal_year == fiscal_year:
			return rate

	frappe.throw(_("No Tax Withholding data found for the current Fiscal Year."))

def get_tax_row(tax_details, tds_amount):
	tax_withhold_list = []
	tax_withhold_list={
		"category": "Total",
		"add_deduct_tax": "Deduct",
		"charge_type": "Actual",
		"account_head": tax_details.account_head,
		"description": tax_details.description,
		"tax_amount": tds_amount,
		"name":tax_details.name
	}
	
	tax_data.append(tax_withhold_list)
	return tax_data

def get_tds_amount(tax_withholding_category,net_amount,ref_doc, tax_details, fiscal_year_details):
	fiscal_year, year_start_date, year_end_date = fiscal_year_details
	tds_amount = 0
	tds_deducted = 0

	def _get_tds(amount):
		if amount <= 0:
			return 0

		return amount * tax_details.rate / 100

	entries = frappe.db.sql("""
			select voucher_no, credit
			from `tabGL Entry`
			where party=%s and fiscal_year=%s and credit > 0
		""", (ref_doc.supplier, fiscal_year), as_dict=1)

	vouchers = [d.voucher_no for d in entries]
	advance_vouchers = get_advance_vouchers(ref_doc.supplier, fiscal_year)
	tds_vouchers = vouchers + advance_vouchers
	if tds_vouchers:
		tds_deducted = frappe.db.sql("""
			SELECT sum(gl.credit) FROM `tabGL Entry` gl, `tabPurchase Invoice` p, `tabPurchase Invoice Item` pi
			WHERE
				p.name = gl.voucher_no and p.name = pi.parent and 
				pi.tax_withholding_category = '"""+tax_withholding_category+"""'
				and gl.account=%s and gl.fiscal_year=%s and gl.credit > 0
				and gl.voucher_no in ({0})""". format(','.join(['%s'] * len(tds_vouchers))),
				((tax_details.account_head, fiscal_year) + tuple(tds_vouchers)))
		
		tds_deducted = tds_deducted[0][0] if tds_deducted and tds_deducted[0][0] else 0

	if tds_deducted:
		
		tds_amount = _get_tds(net_amount)
			
	else:
		
		supplier_credit_amount = frappe.get_all('Purchase Invoice Item',
			fields = ['sum(net_amount)'],
			filters = {'parent': ('in', vouchers),'tax_withholding_category':tax_withholding_category, 'docstatus': 1}, as_list=1)
		supplier_credit_amount = (supplier_credit_amount[0][0]
			if supplier_credit_amount and supplier_credit_amount[0][0] else 0)

		jv_supplier_credit_amt = frappe.get_all('Journal Entry Account',
			fields = ['sum(credit_in_account_currency)'],
			filters = {
				'parent': ('in', vouchers), 'docstatus': 1,
				'party': ref_doc.supplier,
				'reference_type': ('not in', ['Purchase Invoice'])
			}, as_list=1)
		supplier_credit_amount += (jv_supplier_credit_amt[0][0]
			if jv_supplier_credit_amt and jv_supplier_credit_amt[0][0] else 0)
		supplier_credit_amount += net_amount
		debit_note_amount = get_debit_note_amount(tax_withholding_category,ref_doc.supplier, year_start_date, year_end_date)
		supplier_credit_amount -= debit_note_amount	
		if ((tax_details.get('threshold', 0) and supplier_credit_amount >= tax_details.threshold)
			or (tax_details.get('cumulative_threshold', 0) and supplier_credit_amount >= tax_details.cumulative_threshold)):
			tds_amount = _get_tds(supplier_credit_amount)

	return tds_amount

def get_advance_vouchers(supplier, fiscal_year=None, company=None, from_date=None, to_date=None):
	condition = "fiscal_year=%s" % fiscal_year
	if from_date and to_date:
		condition = "company=%s and posting_date between %s and %s" % (company, from_date, to_date)

	return frappe.db.sql_list("""
		select distinct voucher_no
		from `tabGL Entry`
		where party=%s and %s and debit > 0
	""", (supplier, condition)) or []

def get_debit_note_amount(tax_withholding_category,supplier, year_start_date, year_end_date, company=None):
	condition = ""
	if company:
		condition = " and p.company=%s " % company

	return flt(frappe.db.sql("""
		select abs(sum(pi.net_amount))
		from `tabPurchase Invoice` p, `tabPurchase Invoice Item` pi
		where p.name = pi.parent and pi.tax_withholding_category = %s and p.supplier=%s %s and p.is_return=1 and p.docstatus=1
			and p.posting_date between %s and %s
	""", (tax_withholding_category,supplier, condition, year_start_date, year_end_date)))
	
def get_unique_tax_withholding_category(purchase_invoice_item):
	taxWithholding_map = {}
	for item in purchase_invoice_item:
		tax_withholding_category = item.tax_withholding_category
		if tax_withholding_category is not None:
			net_amount = item.net_amount
			key = tax_withholding_category
			if key in taxWithholding_map:
				item_entry = taxWithholding_map[key]
				amount_temp = item_entry["net_amount"]
				item_entry["net_amount"] = (amount_temp) + (net_amount)
			else:
				taxWithholding_map[key] = frappe._dict({
						"tax_withholding_category": tax_withholding_category, 
						"net_amount": net_amount
						})
	return taxWithholding_map
