# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, json
from frappe import _

def execute(filters=None):
	columns, data = get_columns(filters), get_data(filters)
	return columns, data

def get_columns(filters):
	return [
		"GSTIN/UIN of Recipient::150",
		"Receiver Name::120",
		"Invoice Number:Link/Sales Invoice:120",
		"Invoice date:Date:120",
		"Invoice Value:Currency:120",
		"Place of Supply::120",
		"Reverse Charge::120",
		"Invoice Type::120",
		"E-Commerce GSTIN::120",
		"Rate:Int:80",
		"Taxable Value:Currency:120",
		"Cess Amount:Currency:120"
	]
	
def get_data(filters):
	gst_accounts = get_gst_accounts(filters)
	invoices = get_invoice_data(filters)
	invoice_items = get_invoice_items(invoices)
	items_based_on_tax_rate, invoice_cess = get_items_based_on_tax_rate(invoices.keys(), gst_accounts)

	data = []
	for inv, items_based_on_rate in items_based_on_tax_rate.items():
		invoice_details = invoices.get(inv)
		for rate, items in items_based_on_rate.items():
			row = [
				invoice_details.customer_gstin,
				invoice_details.customer_name,
				inv,
				invoice_details.posting_date,
				invoice_details.base_rounded_total or invoice_details.base_grand_total,
				invoice_details.place_of_supply,
				invoice_details.reverse_charge,
				invoice_details.invoice_type,
				invoice_details.ecommerce_gstin,
				rate,
				sum([net_amount for item_code, net_amount in invoice_items.get(inv).items()
					if item_code in items]),
				invoice_cess.get(inv)
			]
			data.append(row)

	return data

def get_gst_accounts(filters):
	gst_accounts = frappe._dict()
	gst_settings_accounts = frappe.get_list("GST Account",
		filters={"parent": "GST Settings", "company": filters.company},
		fields=["cgst_account", "sgst_account", "igst_account", "cess_account"])

	if not gst_settings_accounts:
		frappe.throw(_("Please set GST Accounts in GST Settings"))

	for d in gst_settings_accounts:
		for acc, val in d.items():
			gst_accounts.setdefault(acc, []).append(val)

	return gst_accounts

def get_invoice_data(filters):
	invoices = frappe._dict()
	conditions = get_conditions(filters)
	match_conditions = frappe.build_match_conditions("Sales Invoice")

	if match_conditions:
		match_conditions = " and {0} ".format(match_conditions)

	invoice_data = frappe.db.sql("""
		select
			`tabSales Invoice`.name,
			`tabSales Invoice`.customer_name,
			`tabSales Invoice`.posting_date,
			`tabSales Invoice`.base_grand_total,
			`tabSales Invoice`.base_rounded_total,
			`tabSales Invoice`.customer_gstin,
			`tabSales Invoice`.place_of_supply,
			`tabSales Invoice`.ecommerce_gstin,
			`tabSales Invoice`.reverse_charge,
			`tabSales Invoice`.invoice_type
		from `tabSales Invoice`
		where `tabSales Invoice`.docstatus = 1 %s %s
		order by `tabSales Invoice`.posting_date desc
		""" % (conditions, match_conditions), filters, as_dict=1)

	for d in invoice_data:
		invoices.setdefault(d.name, d)
	return invoices

def get_conditions(filters):
	conditions = ""

	for opts in (("company", " and company=%(company)s"),
		("from_date", " and `tabSales Invoice`.posting_date>=%(from_date)s"),
		("to_date", " and `tabSales Invoice`.posting_date<=%(to_date)s")):
			if filters.get(opts[0]):
				conditions += opts[1]

	return conditions

def get_invoice_items(invoices):
	invoice_items = frappe._dict()
	items = frappe.db.sql("""
		select item_code, parent, base_net_amount
		from `tabSales Invoice Item`
		where parent in (%s)
	""" % (', '.join(['%s']*len(invoices))), tuple(invoices), as_dict=1)

	for d in items:
		invoice_items.setdefault(d.parent, {}).setdefault(d.item_code, d.base_net_amount)
	return invoice_items
	
def get_items_based_on_tax_rate(invoices, gst_accounts):
	tax_details = frappe.db.sql("""
		select
			parent, account_head, item_wise_tax_detail, base_tax_amount_after_discount_amount
		from `tabSales Taxes and Charges`
		where
			parenttype = 'Sales Invoice' and docstatus = 1
			and parent in (%s)
			and tax_amount_after_discount_amount > 0
		order by account_head
	""" % (', '.join(['%s']*len(invoices))), tuple(invoices))

	items_based_on_tax_rate = {}
	invoice_cess = frappe._dict()

	for parent, account, item_wise_tax_detail, tax_amount in tax_details:
		if account in gst_accounts.cess_account:
			invoice_cess.setdefault(parent, tax_amount)
		else:
			if item_wise_tax_detail:
				try:
					item_wise_tax_detail = json.loads(item_wise_tax_detail)
					cgst_or_sgst = False
					if account in gst_accounts.cgst_account or account in gst_accounts.sgst_account:
						cgst_or_sgst = True

					for item_code, tax_amounts in item_wise_tax_detail.items():
						tax_rate = tax_amounts[0]
						if cgst_or_sgst:
							tax_rate *= 2

						rate_based_dict = items_based_on_tax_rate.setdefault(parent, {}).setdefault(tax_rate, [])
						if item_code not in rate_based_dict:
							rate_based_dict.append(item_code)

				except ValueError:
					continue
	return items_based_on_tax_rate, invoice_cess