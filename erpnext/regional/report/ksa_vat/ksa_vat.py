# Copyright (c) 2021, Havenir Solutions, Wahni Green Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, get_url_to_list

import json

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
	gt_tax_amt, gt_adj_amt, gt_tax = get_tax_data(data, settings.ksa_vat_sales_accounts, filters, 'Sales Invoice')

	gt_tax_amt, gt_adj_amt = get_zero_rated_total(data, "Sales Invoice", filters, gt_tax_amt, gt_adj_amt)
	gt_tax_amt, gt_adj_amt = get_exempt_total(data, "Sales Invoice", filters, gt_tax_amt, gt_adj_amt)

	data.append({
		"title": _("Grand Total"),
		"amount": gt_tax_amt,
		"adjustment_amount": gt_adj_amt,
		"vat_amount": gt_tax
	})

	# Blank Line
	data.append({"title": '', "amount": '', "adjustment_amount": '', "vat_amount": ''})

	# Purchase Heading
	data.append({"title": 'VAT on Purchases', "amount": '', "adjustment_amount": '', "vat_amount": ''})
	gt_tax_amt, gt_adj_amt, gt_tax = get_tax_data(data, settings.ksa_vat_purchase_accounts, filters, 'Purchase Invoice')

	gt_tax_amt, gt_adj_amt = get_zero_rated_total(data, "Purchase Invoice", filters, gt_tax_amt, gt_adj_amt)
	gt_tax_amt, gt_adj_amt = get_exempt_total(data, "Purchase Invoice", filters, gt_tax_amt, gt_adj_amt)

	data.append({
		"title": _("Grand Total"),
		"amount": gt_tax_amt,
		"adjustment_amount": gt_adj_amt,
		"vat_amount": gt_tax
	})

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
	conditions = get_conditions(filters)
	invoices = frappe.db.sql(f"""
		SELECT
			j.account_head, j.base_tax_amount, j.base_total,
			j.item_wise_tax_detail, s.is_return
		FROM
			`tab{doctype}` s
			INNER JOIN `tabSales Taxes and Charges` j
			ON j.parent = s.name
		WHERE
			s.docstatus = 1
			{conditions};
	""", filters, as_dict=1)

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
			"vat_amount": tax_details[account]["total_tax"]
		})
		gt_tax_amt += tax_details[account]["taxable_amount"]
		gt_adj_amt += tax_details[account]["adjustment_amount"]
		gt_tax += tax_details[account]["total_tax"]

	return gt_tax_amt, gt_adj_amt, gt_tax

def get_zero_rated_total(data, doctype, filters, gt_tax_amt, gt_adj_amt):
	conditions = get_conditions(filters)
	amount = frappe.db.sql(f"""
		SELECT
			sum(i.base_amount) as total
		FROM
			`tab{doctype} Item` i inner join `tab{doctype}` s
		ON
			i.parent = s.name
		WHERE
			s.docstatus = 1 and i.is_zero_rated = 1
			{conditions}
		GROUP BY
			s.is_return
		ORDER BY
			s.is_return
	""", filters)

	title = "Zero rated domestic sales" if doctype == "Sales Invoice" \
		else "Zero rated purchases"
	gt_tax_amt += flt(amount[0][0] if len(amount) > 0 else 0)
	gt_adj_amt += flt(amount[1][0] if len(amount) > 1 else 0)

	data.append({
		"title": _(title),
		"amount": flt(amount[0][0] if len(amount) > 0 else 0),
		"adjustment_amount": flt(amount[1][0] if len(amount) > 1 else 0),
		"vat_amount": 0.00
	})

	return gt_tax_amt, gt_adj_amt

def get_exempt_total(data, doctype, filters, gt_tax_amt, gt_adj_amt):
	conditions = get_conditions(filters)
	amount = frappe.db.sql(f"""
		SELECT
			sum(i.base_amount) as total
		FROM
			`tab{doctype} Item` i inner join `tab{doctype}` s
		ON
			i.parent = s.name
		WHERE
			s.docstatus = 1 and i.is_exempt = 1
			{conditions}
		GROUP BY
			s.is_return
		ORDER BY
			s.is_return
	""", filters)

	title = "Exempted sales" if doctype == "Sales Invoice" else "Exempted purchases"
	gt_tax_amt += flt(amount[0][0] if len(amount) > 0 else 0)
	gt_adj_amt += flt(amount[1][0] if len(amount) > 1 else 0)

	data.append({
		"title": _(title),
		"amount": flt(amount[0][0] if len(amount) > 0 else 0),
		"adjustment_amount": flt(amount[1][0] if len(amount) > 1 else 0),
		"vat_amount": 0.00
	})

	return gt_tax_amt, gt_adj_amt

def get_conditions(filters):
	conditions = ""
	for opts in (("company", " AND company=%(company)s"),
		("from_date", " AND posting_date>=%(from_date)s"),
		("to_date", " AND posting_date<=%(to_date)s")):
		if filters.get(opts[0]):
			conditions += opts[1]
	return conditions
