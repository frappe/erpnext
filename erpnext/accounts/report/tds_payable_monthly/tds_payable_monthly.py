# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _


def execute(filters=None):
	validate_filters(filters)
	tds_docs, tds_accounts, tax_category_map = get_tds_docs(filters)

	columns = get_columns(filters)

	res = get_result(filters, tds_docs, tds_accounts, tax_category_map)
	return columns, res

def validate_filters(filters):
	''' Validate if dates are properly set '''
	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date"))

def get_result(filters, tds_docs, tds_accounts, tax_category_map):
	supplier_map = get_supplier_pan_map()
	tax_rate_map = get_tax_rate_map(filters)
	gle_map = get_gle_map(filters, tds_docs)

	out = []
	for name, details in gle_map.items():
		tds_deducted, total_amount_credited = 0, 0
		tax_withholding_category = tax_category_map.get(name)
		rate = tax_rate_map.get(tax_withholding_category)

		for entry in details:
			supplier = entry.party or entry.against
			posting_date = entry.posting_date
			voucher_type = entry.voucher_type

			if entry.account in tds_accounts:
				tds_deducted += (entry.credit - entry.debit)

			total_amount_credited += (entry.credit - entry.debit)

		if rate and tds_deducted:
			row = {
				'pan' if frappe.db.has_column('Supplier', 'pan') else 'tax_id': supplier_map.get(supplier).pan,
				'supplier': supplier_map.get(supplier).name
			}

			if filters.naming_series == 'Naming Series':
				row.update({'supplier_name': supplier_map.get(supplier).supplier_name})

			row.update({
				'section_code': tax_withholding_category,
				'entity_type': supplier_map.get(supplier).supplier_type,
				'tds_rate': rate,
				'total_amount_credited': total_amount_credited,
				'tds_deducted': tds_deducted,
				'transaction_date': posting_date,
				'transaction_type': voucher_type,
				'ref_no': name
			})

			out.append(row)

	return out

def get_supplier_pan_map():
	supplier_map = frappe._dict()
	suppliers = frappe.db.get_all('Supplier', fields=['name', 'pan', 'supplier_type', 'supplier_name'])

	for d in suppliers:
		supplier_map[d.name] = d

	return supplier_map

def get_gle_map(filters, documents):
	# create gle_map of the form
	# {"purchase_invoice": list of dict of all gle created for this invoice}
	gle_map = {}

	gle = frappe.db.get_all('GL Entry',
		{
			"voucher_no": ["in", documents],
			"credit": (">", 0)
		},
		["credit", "debit", "account", "voucher_no", "posting_date", "voucher_type", "against", "party"],
	)

	for d in gle:
		if not d.voucher_no in gle_map:
			gle_map[d.voucher_no] = [d]
		else:
			gle_map[d.voucher_no].append(d)

	return gle_map

def get_columns(filters):
	pan = "pan" if frappe.db.has_column("Supplier", "pan") else "tax_id"
	columns = [
		{
			"label": _(frappe.unscrub(pan)),
			"fieldname": pan,
			"fieldtype": "Data",
			"width": 90
		},
		{
			"label": _("Supplier"),
			"options": "Supplier",
			"fieldname": "supplier",
			"fieldtype": "Link",
			"width": 180
		}]

	if filters.naming_series == 'Naming Series':
		columns.append({
			"label": _("Supplier Name"),
			"fieldname": "supplier_name",
			"fieldtype": "Data",
			"width": 180
		})

	columns.extend([
		{
			"label": _("Section Code"),
			"options": "Tax Withholding Category",
			"fieldname": "section_code",
			"fieldtype": "Link",
			"width": 180
		},
		{
			"label": _("Entity Type"),
			"fieldname": "entity_type",
			"fieldtype": "Data",
			"width": 180
		},
		{
			"label": _("TDS Rate %"),
			"fieldname": "tds_rate",
			"fieldtype": "Percent",
			"width": 90
		},
		{
			"label": _("Total Amount Credited"),
			"fieldname": "total_amount_credited",
			"fieldtype": "Float",
			"width": 90
		},
		{
			"label": _("Amount of TDS Deducted"),
			"fieldname": "tds_deducted",
			"fieldtype": "Float",
			"width": 90
		},
		{
			"label": _("Date of Transaction"),
			"fieldname": "transaction_date",
			"fieldtype": "Date",
			"width": 90
		},
		{
			"label": _("Transaction Type"),
			"fieldname": "transaction_type",
			"width": 90
		},
		{
			"label": _("Reference No."),
			"fieldname": "ref_no",
			"fieldtype": "Dynamic Link",
			"options": "transaction_type",
			"width": 90
		}
	])

	return columns

def get_tds_docs(filters):
	tds_documents = []
	purchase_invoices = []
	payment_entries = []
	journal_entries = []
	tax_category_map = {}

	tds_accounts = frappe.get_all("Tax Withholding Account", {'company': filters.get('company')},
		pluck="account")

	query_filters = {
		"credit": ('>', 0),
		"account": ("in", tds_accounts),
		"posting_date": ("between", [filters.get("from_date"), filters.get("to_date")]),
		"is_cancelled": 0
	}

	if filters.get('supplier'):
		query_filters.update({'against': filters.get('supplier')})

	tds_docs = frappe.get_all("GL Entry", query_filters, ["voucher_no", "voucher_type", "against", "party"])

	for d in tds_docs:
		if d.voucher_type == "Purchase Invoice":
			purchase_invoices.append(d.voucher_no)
		elif d.voucher_type == "Payment Entry":
			payment_entries.append(d.voucher_no)
		elif d.voucher_type == "Journal Entry":
			journal_entries.append(d.voucher_no)

		tds_documents.append(d.voucher_no)

	if purchase_invoices:
		get_tax_category_map(purchase_invoices, 'Purchase Invoice', tax_category_map)

	if payment_entries:
		get_tax_category_map(payment_entries, 'Payment Entry', tax_category_map)

	if journal_entries:
		get_tax_category_map(journal_entries, 'Journal Entry', tax_category_map)

	return tds_documents, tds_accounts, tax_category_map

def get_tax_category_map(vouchers, doctype, tax_category_map):
	tax_category_map.update(frappe._dict(frappe.get_all(doctype,
		filters = {'name': ('in', vouchers)}, fields=['name', 'tax_withholding_category'], as_list=1)))

def get_tax_rate_map(filters):
	rate_map = frappe.get_all('Tax Withholding Rate', filters={
		'from_date': ('<=', filters.get('from_date')),
		'to_date': ('>=', filters.get('to_date'))
	}, fields=['parent', 'tax_withholding_rate'], as_list=1)

	return frappe._dict(rate_map)