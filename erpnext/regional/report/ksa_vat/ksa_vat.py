# Copyright (c) 2021, Havenir Solutions, Wahni Green Technologies and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.utils import get_url_to_list

from erpnext.controllers.taxes_and_totals import get_itemised_tax, get_itemised_taxable_amount


def execute(filters=None):
	columns = columns = get_columns()
	data = get_data(filters)
	return columns, data

def get_columns():
	return [
		{
			"fieldname": "title",
			"label": _("Title"),
			"fieldtype": "Data",
			"width": 300
		},
		{
			"fieldname": "amount",
			"label": _("Amount (SAR)"),
			"fieldtype": "Currency",
			"width": 150,
		},
		{
			"fieldname": "adjustment_amount",
			"label": _("Adjustment (SAR)"),
			"fieldtype": "Currency",
			"width": 150,
		},
		{
			"fieldname": "vat_amount",
			"label": _("VAT Amount (SAR)"),
			"fieldtype": "Currency",
			"width": 150,
		}
	]

def get_data(filters):
	data = []

	# Validate if vat settings exist
	company = filters.get('company')
	if frappe.db.exists('KSA VAT Setting', company) is None:
		url = get_url_to_list('KSA VAT Setting')
		frappe.msgprint(_('Create <a href="{}">KSA VAT Setting</a> for this company').format(url))
		return data

	settings = frappe.get_doc('KSA VAT Setting', company)

	# Sales Heading
	data.append({"title": 'VAT on Sales', "amount": '', "adjustment_amount": '', "vat_amount": ''})
	get_tax_data(data, settings.ksa_vat_sales_accounts, filters, 'Sales Invoice')

	# Blank Line
	data.append({"title": '', "amount": '', "adjustment_amount": '', "vat_amount": ''})

	# Purchase Heading
	data.append({"title": 'VAT on Purchases', "amount": '', "adjustment_amount": '', "vat_amount": ''})
	get_tax_data(data, settings.ksa_vat_purchase_accounts, filters, 'Purchase Invoice')

	return data

def get_tax_data(data, settings, filters, doctype):
	# Initiate variables
	tax_details = {}
	for d in settings:
		tax_details[d.account] = {
			"title": d.title,
			"taxable_amount": 0.00,
			"adjustment_amount": 0.00,
			"total_tax": 0.00
		}

	# Fetch All Invoices
	invoices = frappe.get_all(doctype, filters ={
		'company': filters.get('company'),
		'docstatus': 1,
		'posting_date': ['between', [filters.get('from_date'), filters.get('to_date')]]
	})

	for inv in invoices:
		invoice = frappe.get_doc(doctype, inv)
		if not invoice.taxes:
			continue
		itemised_tax = get_itemised_tax(invoice.taxes, True)
		itemised_taxable_amount = get_itemised_taxable_amount(invoice.items)

		for item in itemised_taxable_amount.keys():
			# Summing up total tax
			item_itemised_tax = itemised_tax.get(item)
			for item_tax in item_itemised_tax.keys():
				acc = item_itemised_tax[item_tax]['tax_account']
				if tax_details.get(acc):
					tax_details[acc]["total_tax"] += item_itemised_tax[item_tax]['tax_amount']
					# Summing up total taxable amount
					if not invoice.is_return:
						tax_details[acc]["taxable_amount"] += itemised_taxable_amount[item]
					else:
						tax_details[acc]["adjustment_amount"] += itemised_taxable_amount[item]

	grand_total_taxable_amount, grand_total_adjustment_amount, grand_total_tax = 0, 0, 0
	for account in tax_details.keys():
		data.append({
			"title": _(tax_details[account]["title"]),
			"amount": tax_details[account]["taxable_amount"],
			"adjustment_amount": tax_details[account]["adjustment_amount"],
			"vat_amount": tax_details[account]["total_tax"]
		})
		grand_total_taxable_amount += tax_details[account]["taxable_amount"]
		grand_total_adjustment_amount += tax_details[account]["adjustment_amount"]
		grand_total_tax += tax_details[account]["total_tax"]

	data.append({
		"title": _("Grand Total"),
		"amount": grand_total_taxable_amount,
		"adjustment_amount": grand_total_adjustment_amount,
		"vat_amount": grand_total_tax
	})
