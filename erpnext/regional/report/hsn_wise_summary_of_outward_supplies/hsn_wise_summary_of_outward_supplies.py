# Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import json

import frappe
from frappe import _
from frappe.model.meta import get_field_precision
from frappe.utils import cstr, flt, getdate

import erpnext
from erpnext.regional.india.utils import get_gst_accounts
from erpnext.regional.report.gstr_1.gstr_1 import get_company_gstin_number


def execute(filters=None):
	return _execute(filters)


def _execute(filters=None):
	if not filters:
		filters = {}
	columns = get_columns()

	company_currency = erpnext.get_company_currency(filters.company)
	item_list = get_items(filters)
	if item_list:
		itemised_tax, tax_columns = get_tax_accounts(item_list, columns, company_currency)

	data = []
	added_item = []
	for d in item_list:
		if (d.parent, d.item_code) not in added_item:
			row = [d.gst_hsn_code, d.description, d.stock_uom, d.stock_qty, d.tax_rate]
			total_tax = 0
			for tax in tax_columns:
				item_tax = itemised_tax.get((d.parent, d.item_code), {}).get(tax, {})
				total_tax += flt(item_tax.get("tax_amount", 0))

			row += [d.base_net_amount + total_tax]
			row += [d.base_net_amount]
			for tax in tax_columns:
				item_tax = itemised_tax.get((d.parent, d.item_code), {}).get(tax, {})
				row += [item_tax.get("tax_amount", 0)]
			data.append(row)
			added_item.append((d.parent, d.item_code))
	if data:
		data = get_merged_data(columns, data)  # merge same hsn code data
	return columns, data


def get_columns():
	columns = [
		{
			"fieldname": "gst_hsn_code",
			"label": _("HSN/SAC"),
			"fieldtype": "Link",
			"options": "GST HSN Code",
			"width": 100,
		},
		{"fieldname": "description", "label": _("Description"), "fieldtype": "Data", "width": 300},
		{"fieldname": "stock_uom", "label": _("Stock UOM"), "fieldtype": "Data", "width": 100},
		{"fieldname": "stock_qty", "label": _("Stock Qty"), "fieldtype": "Float", "width": 90},
		{"fieldname": "tax_rate", "label": _("Tax Rate"), "fieldtype": "Data", "width": 90},
		{"fieldname": "total_amount", "label": _("Total Amount"), "fieldtype": "Currency", "width": 120},
		{
			"fieldname": "taxable_amount",
			"label": _("Total Taxable Amount"),
			"fieldtype": "Currency",
			"width": 170,
		},
	]

	return columns


def get_conditions(filters):
	conditions = ""

	for opts in (
		("company", " and company=%(company)s"),
		("gst_hsn_code", " and gst_hsn_code=%(gst_hsn_code)s"),
		("company_gstin", " and company_gstin=%(company_gstin)s"),
		("from_date", " and posting_date >= %(from_date)s"),
		("to_date", "and posting_date <= %(to_date)s"),
	):
		if filters.get(opts[0]):
			conditions += opts[1]

	return conditions


def get_items(filters):
	conditions = get_conditions(filters)
	match_conditions = frappe.build_match_conditions("Sales Invoice")
	if match_conditions:
		match_conditions = " and {0} ".format(match_conditions)

	items = frappe.db.sql(
		"""
		select
			`tabSales Invoice Item`.gst_hsn_code,
			`tabSales Invoice Item`.stock_uom,
			sum(`tabSales Invoice Item`.stock_qty) as stock_qty,
			sum(`tabSales Invoice Item`.base_net_amount) as base_net_amount,
			sum(`tabSales Invoice Item`.base_price_list_rate) as base_price_list_rate,
			`tabSales Invoice Item`.parent,
			`tabSales Invoice Item`.item_code,
			`tabGST HSN Code`.description,
			json_extract(`tabSales Taxes and Charges`.item_wise_tax_detail,
			concat('$."' , `tabSales Invoice Item`.item_code, '"[0]')) * count(distinct `tabSales Taxes and Charges`.name) as tax_rate
		from
			`tabSales Invoice`,
			`tabSales Invoice Item`,
			`tabGST HSN Code`,
			`tabSales Taxes and Charges`
		where
			`tabSales Invoice`.name = `tabSales Invoice Item`.parent
			and `tabSales Taxes and Charges`.parent = `tabSales Invoice`.name
			and `tabSales Invoice`.docstatus = 1
			and `tabSales Invoice Item`.gst_hsn_code is not NULL
			and `tabSales Invoice Item`.gst_hsn_code = `tabGST HSN Code`.name %s %s
		group by
			`tabSales Invoice Item`.parent,
			`tabSales Invoice Item`.item_code
		"""
		% (conditions, match_conditions),
		filters,
		as_dict=1,
	)

	return items


def get_tax_accounts(
	item_list,
	columns,
	company_currency,
	doctype="Sales Invoice",
	tax_doctype="Sales Taxes and Charges",
):
	item_row_map = {}
	tax_columns = []
	invoice_item_row = {}
	itemised_tax = {}
	conditions = ""

	tax_amount_precision = (
		get_field_precision(
			frappe.get_meta(tax_doctype).get_field("tax_amount"), currency=company_currency
		)
		or 2
	)

	for d in item_list:
		invoice_item_row.setdefault(d.parent, []).append(d)
		item_row_map.setdefault(d.parent, {}).setdefault(d.item_code or d.item_name, []).append(d)

	tax_details = frappe.db.sql(
		"""
		select
			parent, account_head, item_wise_tax_detail,
			base_tax_amount_after_discount_amount
		from `tab%s`
		where
			parenttype = %s and docstatus = 1
			and (description is not null and description != '')
			and parent in (%s)
			%s
		order by description
	"""
		% (tax_doctype, "%s", ", ".join(["%s"] * len(invoice_item_row)), conditions),
		tuple([doctype] + list(invoice_item_row)),
	)

	for parent, account_head, item_wise_tax_detail, tax_amount in tax_details:

		if account_head not in tax_columns and tax_amount:
			# as description is text editor earlier and markup can break the column convention in reports
			tax_columns.append(account_head)

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
							itemised_tax.setdefault((parent, item_code), {})[account_head] = frappe._dict(
								{"tax_amount": flt(item_tax_amount, tax_amount_precision)}
							)
			except ValueError:
				continue

	tax_columns.sort()
	for account_head in tax_columns:
		columns.append(
			{
				"label": account_head,
				"fieldname": frappe.scrub(account_head),
				"fieldtype": "Float",
				"width": 110,
			}
		)

	return itemised_tax, tax_columns


def get_merged_data(columns, data):
	merged_hsn_dict = {}  # to group same hsn under one key and perform row addition
	result = []

	for row in data:
		key = row[0] + "-" + row[2] + "-" + str(row[4])
		merged_hsn_dict.setdefault(key, {})
		for i, d in enumerate(columns):
			if d["fieldtype"] not in ("Int", "Float", "Currency"):
				merged_hsn_dict[key][d["fieldname"]] = row[i]
			else:
				if merged_hsn_dict.get(key, {}).get(d["fieldname"], ""):
					merged_hsn_dict[key][d["fieldname"]] += row[i]
				else:
					merged_hsn_dict[key][d["fieldname"]] = row[i]

	for key, value in merged_hsn_dict.items():
		result.append(value)

	return result


@frappe.whitelist()
def get_json(filters, report_name, data):
	filters = json.loads(filters)
	report_data = json.loads(data)
	gstin = filters.get("company_gstin") or get_company_gstin_number(filters["company"])

	if not filters.get("from_date") or not filters.get("to_date"):
		frappe.throw(_("Please enter From Date and To Date to generate JSON"))

	fp = "%02d%s" % (getdate(filters["to_date"]).month, getdate(filters["to_date"]).year)

	gst_json = {"version": "GST3.0.3", "hash": "hash", "gstin": gstin, "fp": fp}

	gst_json["hsn"] = {"data": get_hsn_wise_json_data(filters, report_data)}

	return {"report_name": report_name, "data": gst_json}


@frappe.whitelist()
def download_json_file():
	"""download json content in a file"""
	data = frappe._dict(frappe.local.form_dict)
	frappe.response["filename"] = frappe.scrub("{0}".format(data["report_name"])) + ".json"
	frappe.response["filecontent"] = data["data"]
	frappe.response["content_type"] = "application/json"
	frappe.response["type"] = "download"


def get_hsn_wise_json_data(filters, report_data):

	filters = frappe._dict(filters)
	gst_accounts = get_gst_accounts(filters.company)
	data = []
	count = 1

	for hsn in report_data:
		row = {
			"num": count,
			"hsn_sc": hsn.get("gst_hsn_code"),
			"desc": hsn.get("description"),
			"uqc": hsn.get("stock_uom").upper(),
			"qty": hsn.get("stock_qty"),
			"rt": flt(hsn.get("tax_rate"), 2),
			"txval": flt(hsn.get("taxable_amount", 2)),
			"iamt": 0.0,
			"camt": 0.0,
			"samt": 0.0,
			"csamt": 0.0,
		}

		for account in gst_accounts.get("igst_account"):
			row["iamt"] += flt(hsn.get(frappe.scrub(cstr(account)), 0.0), 2)

		for account in gst_accounts.get("cgst_account"):
			row["camt"] += flt(hsn.get(frappe.scrub(cstr(account)), 0.0), 2)

		for account in gst_accounts.get("sgst_account"):
			row["samt"] += flt(hsn.get(frappe.scrub(cstr(account)), 0.0), 2)

		for account in gst_accounts.get("cess_account"):
			row["csamt"] += flt(hsn.get(frappe.scrub(cstr(account)), 0.0), 2)

		data.append(row)
		count += 1

	return data
