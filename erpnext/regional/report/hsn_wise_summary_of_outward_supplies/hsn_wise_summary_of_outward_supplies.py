# Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe import _
from frappe.utils import flt
from frappe.model.meta import get_field_precision
from frappe.utils.xlsxutils import handle_html

def execute(filters=None):
	return _execute(filters)

def _execute(filters=None):
	if not filters: filters = {}
	columns = get_columns()

	company_currency = erpnext.get_company_currency(filters.company)
	item_list = get_items(filters)
	if item_list:
		itemised_tax, tax_columns = get_tax_accounts(item_list, columns, company_currency)

	data = []
	for d in item_list:
		row = [d.gst_hsn_code, d.description, d.stock_uom, d.stock_qty]
		total_tax = 0
		for tax in tax_columns:
			item_tax = itemised_tax.get(d.name, {}).get(tax, {})
			total_tax += flt(item_tax.get("tax_amount"))

		row += [d.base_net_amount + total_tax]
		row += [d.base_net_amount]

		for tax in tax_columns:
			item_tax = itemised_tax.get(d.name, {}).get(tax, {})
			row += [item_tax.get("tax_amount", 0)]

		data.append(row)
	if data:
		data = get_merged_data(columns, data) # merge same hsn code data
	return columns, data

def get_columns():
	columns = [
		{
			"fieldname": "gst_hsn_code",
			"label": _("HSN/SAC"),
			"fieldtype": "Link",
			"options": "GST HSN Code",
			"width": 100
		},
		{
			"fieldname": "description",
			"label": _("Description"),
			"fieldtype": "Data",
			"width": 300
		},
		{
			"fieldname": "stock_uom",
			"label": _("Stock UOM"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "stock_qty",
			"label": _("Stock Qty"),
			"fieldtype": "Float",
			"width": 90
		},
		{
			"fieldname": "total_amount",
			"label": _("Total Amount"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "taxable_amount",
			"label": _("Total Taxable Amount"),
			"fieldtype": "Currency",
			"width": 170
		}
	]

	return columns

def get_conditions(filters):
	conditions = ""

	for opts in (("company", " and company=%(company)s"),
		("gst_hsn_code", " and gst_hsn_code=%(gst_hsn_code)s")):
			if filters.get(opts[0]):
				conditions += opts[1]

	return conditions

def get_items(filters):
	conditions = get_conditions(filters)
	match_conditions = frappe.build_match_conditions("Sales Invoice")
	if match_conditions:
		match_conditions = " and {0} ".format(match_conditions)


	return frappe.db.sql("""
		select
			`tabSales Invoice Item`.name, `tabSales Invoice Item`.base_price_list_rate,
			`tabSales Invoice Item`.gst_hsn_code, `tabSales Invoice Item`.stock_qty,
			`tabSales Invoice Item`.stock_uom, `tabSales Invoice Item`.base_net_amount,
			`tabSales Invoice Item`.parent, `tabSales Invoice Item`.item_code,
			`tabGST HSN Code`.description
		from `tabSales Invoice`, `tabSales Invoice Item`, `tabGST HSN Code`
		where `tabSales Invoice`.name = `tabSales Invoice Item`.parent
			and `tabSales Invoice`.docstatus = 1
			and `tabSales Invoice Item`.gst_hsn_code is not NULL
			and `tabSales Invoice Item`.gst_hsn_code = `tabGST HSN Code`.name %s %s

		""" % (conditions, match_conditions), filters, as_dict=1)


def get_tax_accounts(item_list, columns, company_currency,
		doctype="Sales Invoice", tax_doctype="Sales Taxes and Charges"):
	import json
	item_row_map = {}
	tax_columns = []
	invoice_item_row = {}
	itemised_tax = {}
	conditions = ""

	tax_amount_precision = get_field_precision(frappe.get_meta(tax_doctype).get_field("tax_amount"),
		currency=company_currency) or 2

	for d in item_list:
		invoice_item_row.setdefault(d.parent, []).append(d)
		item_row_map.setdefault(d.parent, {}).setdefault(d.item_code or d.item_name, []).append(d)

	tax_details = frappe.db.sql("""
		select
			parent, description, item_wise_tax_detail,
			base_tax_amount_after_discount_amount
		from `tab%s`
		where
			parenttype = %s and docstatus = 1
			and (description is not null and description != '')
			and parent in (%s)
			%s
		order by description
	""" % (tax_doctype, '%s', ', '.join(['%s']*len(invoice_item_row)), conditions),
		tuple([doctype] + list(invoice_item_row)))

	for parent, description, item_wise_tax_detail, tax_amount in tax_details:
		description = handle_html(description)
		if description not in tax_columns and tax_amount:
			# as description is text editor earlier and markup can break the column convention in reports
			tax_columns.append(description)

		if item_wise_tax_detail:
			try:
				item_wise_tax_detail = json.loads(item_wise_tax_detail)

				for item_code, tax_data in item_wise_tax_detail.items():
					if not frappe.db.get_value("Item", item_code, "gst_hsn_code"):
						continue
					itemised_tax.setdefault(item_code, frappe._dict())
					if isinstance(tax_data, list):
						tax_amount = tax_data[1]
					else:
						tax_amount = 0

					for d in item_row_map.get(parent, {}).get(item_code, []):
						item_tax_amount = tax_amount
						if item_tax_amount:
							itemised_tax.setdefault(d.name, {})[description] = frappe._dict({
								"tax_amount": flt(item_tax_amount, tax_amount_precision)
							})
			except ValueError:
				continue

	tax_columns.sort()
	for desc in tax_columns:
		columns.append(desc + " Amount:Currency/currency:160")

	# columns += ["Total Amount:Currency/currency:110"]
	return itemised_tax, tax_columns

def get_merged_data(columns, data):
	merged_hsn_dict = {} # to group same hsn under one key and perform row addition
	add_column_index = [] # store index of columns that needs to be added
	tax_col = len(get_columns())
	fields_to_merge = ["stock_qty", "total_amount", "taxable_amount"] # columns for which index needs to be found

	for i,d in enumerate(columns):
		# check if fieldname in to_merge list and ignore tax-columns
		if i < tax_col and d["fieldname"] in fields_to_merge:
			add_column_index.append(i)

	for row in data:
		if merged_hsn_dict.has_key(row[0]):
			to_add_row = merged_hsn_dict.get(row[0])

			# add columns from the add_column_index table
			for k in add_column_index:
				to_add_row[k] += row[k]

			# add tax columns
			for k in range(len(columns)):
				if tax_col <= k < len(columns):
					to_add_row[k] += row[k]

			# update hsn dict with the newly added data
			merged_hsn_dict[row[0]] = to_add_row
		else:
			merged_hsn_dict[row[0]] = row

	# extract data rows to be displayed in report
	data = [merged_hsn_dict[d] for d in merged_hsn_dict]

	return data

