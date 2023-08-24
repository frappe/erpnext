# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	columns, data = get_columns(), get_data(filters)
	return columns, data


def get_data(filters):
	data = []
	depreciation_accounts = frappe.db.sql_list(
		""" select name from tabAccount
		where ifnull(account_type, '') = 'Depreciation' """
	)

	filters_data = [
		["company", "=", filters.get("company")],
		["posting_date", ">=", filters.get("from_date")],
		["posting_date", "<=", filters.get("to_date")],
		["against_voucher_type", "=", "Asset"],
		["account", "in", depreciation_accounts],
		["is_cancelled", "=", 0],
	]

	if filters.get("asset"):
		filters_data.append(["against_voucher", "=", filters.get("asset")])

	if filters.get("asset_category"):

		assets = frappe.db.sql_list(
			"""select name from tabAsset
			where asset_category = %s and docstatus=1""",
			filters.get("asset_category"),
		)

		filters_data.append(["against_voucher", "in", assets])

	if filters.get("finance_book"):
		filters_data.append(["finance_book", "in", ["", filters.get("finance_book")]])

	gl_entries = frappe.get_all(
		"GL Entry",
		filters=filters_data,
		fields=["against_voucher", "debit_in_account_currency as debit", "voucher_no", "posting_date"],
		order_by="against_voucher, posting_date",
	)

	if not gl_entries:
		return data

	assets = [d.against_voucher for d in gl_entries]
	assets_details = get_assets_details(assets)

	for d in gl_entries:
		asset_data = assets_details.get(d.against_voucher)
		if asset_data:
			if not asset_data.get("accumulated_depreciation_amount"):
				asset_data.accumulated_depreciation_amount = d.debit
			else:
				asset_data.accumulated_depreciation_amount += d.debit

			row = frappe._dict(asset_data)
			row.update(
				{
					"depreciation_amount": d.debit,
					"depreciation_date": d.posting_date,
					"amount_after_depreciation": (
						flt(row.gross_purchase_amount) - flt(row.accumulated_depreciation_amount)
					),
					"depreciation_entry": d.voucher_no,
				}
			)

			data.append(row)

	return data


def get_assets_details(assets):
	assets_details = {}

	fields = [
		"name as asset",
		"gross_purchase_amount",
		"asset_category",
		"status",
		"depreciation_method",
		"purchase_date",
	]

	for d in frappe.get_all("Asset", fields=fields, filters={"name": ("in", assets)}):
		assets_details.setdefault(d.asset, d)

	return assets_details


def get_columns():
	return [
		{
			"label": _("Asset"),
			"fieldname": "asset",
			"fieldtype": "Link",
			"options": "Asset",
			"width": 120,
		},
		{
			"label": _("Depreciation Date"),
			"fieldname": "depreciation_date",
			"fieldtype": "Date",
			"width": 120,
		},
		{
			"label": _("Purchase Amount"),
			"fieldname": "gross_purchase_amount",
			"fieldtype": "Currency",
			"width": 120,
		},
		{
			"label": _("Depreciation Amount"),
			"fieldname": "depreciation_amount",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _("Accumulated Depreciation Amount"),
			"fieldname": "accumulated_depreciation_amount",
			"fieldtype": "Currency",
			"width": 210,
		},
		{
			"label": _("Amount After Depreciation"),
			"fieldname": "amount_after_depreciation",
			"fieldtype": "Currency",
			"width": 180,
		},
		{
			"label": _("Depreciation Entry"),
			"fieldname": "depreciation_entry",
			"fieldtype": "Link",
			"options": "Journal Entry",
			"width": 140,
		},
		{
			"label": _("Asset Category"),
			"fieldname": "asset_category",
			"fieldtype": "Link",
			"options": "Asset Category",
			"width": 120,
		},
		{"label": _("Current Status"), "fieldname": "status", "fieldtype": "Data", "width": 120},
		{
			"label": _("Depreciation Method"),
			"fieldname": "depreciation_method",
			"fieldtype": "Data",
			"width": 130,
		},
		{"label": _("Purchase Date"), "fieldname": "purchase_date", "fieldtype": "Date", "width": 120},
	]
