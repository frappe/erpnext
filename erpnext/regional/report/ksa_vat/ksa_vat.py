# Copyright (c) 2021, Havenir Solutions, Wahni Green Technologies and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.query_builder.functions import Sum
from frappe.utils import flt, get_url_to_list


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
			"width": 300,
		},
		{
			"fieldname": "amount",
			"label": _("Amount (SAR)"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 150,
		},
		{
			"fieldname": "adjustment_amount",
			"label": _("Adjustment (SAR)"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 150,
		},
		{
			"fieldname": "vat_amount",
			"label": _("VAT Amount (SAR)"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 150,
		},
		{
			"fieldname": "currency",
			"label": _("Currency"),
			"fieldtype": "Currency",
			"width": 150,
			"hidden": 1
		},
	]

def get_data(filters):
	data = []

	# Validate if vat settings exist
	company = filters.get('company')
	company_currency = frappe.get_cached_value('Company', company, "default_currency")
	if frappe.db.exists('KSA VAT Setting', company) is None:
		url = get_url_to_list('KSA VAT Setting')
		frappe.msgprint(_('Create <a href="{}">KSA VAT Setting</a> for this company').format(url))
		return data

	settings = frappe.get_doc('KSA VAT Setting', company)

	# Sales Heading
	data.append({
		"title": 'VAT on Sales',
		"amount": '',
		"adjustment_amount": '',
		"vat_amount": '',
		"currency": company_currency
	})
	gt_tax_amt, gt_adj_amt, gt_tax = get_tax_data(data, settings.ksa_vat_sales_accounts,
		filters, 'Sales Invoice', company_currency)

	gt_tax_amt, gt_adj_amt = get_zero_rated_total(data, "Sales Invoice",
		filters, gt_tax_amt, gt_adj_amt, company_currency)
	gt_tax_amt, gt_adj_amt = get_exempt_total(data, "Sales Invoice",
		filters, gt_tax_amt, gt_adj_amt, company_currency)

	data.append({
		"title": _("Grand Total"),
		"amount": gt_tax_amt,
		"adjustment_amount": gt_adj_amt,
		"vat_amount": gt_tax,
		"currency": company_currency
	})

	# Blank Line
	data.append({
		"title": '',
		"amount": '',
		"adjustment_amount": '',
		"vat_amount": '',
		"currency": company_currency
	})

	# Purchase Heading
	data.append({
		"title": 'VAT on Purchases',
		"amount": '',
		"adjustment_amount": '',
		"vat_amount": '',
		"currency": company_currency
	})
	gt_tax_amt, gt_adj_amt, gt_tax = get_tax_data(data, settings.ksa_vat_purchase_accounts,
		filters, 'Purchase Invoice', company_currency)

	gt_tax_amt, gt_adj_amt = get_zero_rated_total(data, "Purchase Invoice",
		filters, gt_tax_amt, gt_adj_amt, company_currency)
	gt_tax_amt, gt_adj_amt = get_exempt_total(data, "Purchase Invoice",
		filters, gt_tax_amt, gt_adj_amt, company_currency)

	data.append({
		"title": _("Grand Total"),
		"amount": gt_tax_amt,
		"adjustment_amount": gt_adj_amt,
		"vat_amount": gt_tax,
		"currency": company_currency
	})

	return data

def get_tax_data(data, settings, filters, doctype, company_currency):
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
	doc = frappe.qb.DocType(doctype)
	stac = frappe.qb.DocType('Sales Taxes and Charges')
	invoices = frappe.qb.from_(doc).inner_join(stac).on(stac.parent == doc.name)
	invoices = invoices.select(
		stac.account_head,
		stac.base_tax_amount,
		stac.item_wise_tax_detail,
		doc.is_return
	)
	invoices = invoices.where(doc.docstatus == 1).where(doc.company == filters.get("company"))
	invoices = invoices.where(doc.posting_date >= filters.get("from_date"))
	invoices = invoices.where(doc.posting_date <= filters.get("to_date")).run(as_dict=True)

	for inv in invoices:
		acc = inv["account_head"]
		if tax_details.get(acc):
			tax_details[acc]["total_tax"] += inv["base_tax_amount"]
			# 'item_wise_tax_detail': '{"Item Code":[Tax Rate, Tax Amount]}'
			item_wise = json.loads(inv["item_wise_tax_detail"])
			if not inv["is_return"]:
				for x in item_wise:
					if item_wise[x][1] > 0.0:
						tax_details[acc]["taxable_amount"] += item_wise[x][1]*100/item_wise[x][0]
			else:
				for x in item_wise:
					if item_wise[x][1] > 0.0:
						tax_details[acc]["adjustment_amount"] += item_wise[x][1]*100/item_wise[x][0]

	gt_tax_amt, gt_adj_amt, gt_tax = 0, 0, 0
	for account in tax_details.keys():
		data.append({
			"title": _(tax_details[account]["title"]),
			"amount": tax_details[account]["taxable_amount"],
			"adjustment_amount": tax_details[account]["adjustment_amount"],
			"vat_amount": tax_details[account]["total_tax"],
			"currency": company_currency
		})
		gt_tax_amt += tax_details[account]["taxable_amount"]
		gt_adj_amt += tax_details[account]["adjustment_amount"]
		gt_tax += tax_details[account]["total_tax"]

	return gt_tax_amt, gt_adj_amt, gt_tax

def get_zero_rated_total(data, doctype, filters, gt_tax_amt, gt_adj_amt, company_currency):
	doc = frappe.qb.DocType(doctype)
	child = frappe.qb.DocType(f"{doctype} Item")
	amount = frappe.qb.from_(child).inner_join(doc).on(child.parent == doc.name)\
		.select(Sum(child.base_amount)).where(doc.docstatus == 1)\
		.where(doc.company == filters.get("company"))\
		.where(doc.posting_date >= filters.get("from_date"))\
		.where(doc.posting_date <= filters.get("to_date"))\
		.where(child.is_zero_rated == 1).groupby(doc.is_return)\
		.orderby(doc.is_return).run()

	title = "Zero rated domestic sales" if doctype == "Sales Invoice" \
		else "Zero rated purchases"
	gt_tax_amt += flt(amount[0][0] if len(amount) > 0 else 0)
	gt_adj_amt += flt(amount[1][0] if len(amount) > 1 else 0)

	data.append({
		"title": _(title),
		"amount": flt(amount[0][0] if len(amount) > 0 else 0),
		"adjustment_amount": flt(amount[1][0] if len(amount) > 1 else 0),
		"vat_amount": 0.00,
		"currency": company_currency
	})

	return gt_tax_amt, gt_adj_amt

def get_exempt_total(data, doctype, filters, gt_tax_amt, gt_adj_amt, company_currency):
	doc = frappe.qb.DocType(doctype)
	child = frappe.qb.DocType(f"{doctype} Item")
	amount = frappe.qb.from_(child).inner_join(doc).on(child.parent == doc.name)\
		.select(Sum(child.base_amount)).where(doc.docstatus == 1)\
		.where(doc.company == filters.get("company"))\
		.where(doc.posting_date >= filters.get("from_date"))\
		.where(doc.posting_date <= filters.get("to_date"))\
		.where(child.is_exempt == 1).groupby(doc.is_return)\
		.orderby(doc.is_return).run()

	title = "Exempted sales" if doctype == "Sales Invoice" else "Exempted purchases"
	gt_tax_amt += flt(amount[0][0] if len(amount) > 0 else 0)
	gt_adj_amt += flt(amount[1][0] if len(amount) > 1 else 0)

	data.append({
		"title": _(title),
		"amount": flt(amount[0][0] if len(amount) > 0 else 0),
		"adjustment_amount": flt(amount[1][0] if len(amount) > 1 else 0),
		"vat_amount": 0.00,
		"currency": company_currency
	})

	return gt_tax_amt, gt_adj_amt
