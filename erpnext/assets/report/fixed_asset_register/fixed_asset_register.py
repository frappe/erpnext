# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from itertools import chain

import frappe
from frappe import _
from frappe.query_builder.functions import IfNull, Sum
from frappe.utils import add_months, cstr, flt, formatdate, getdate, nowdate, today

from erpnext.accounts.report.financial_statements import (
	get_fiscal_year_data,
	get_period_list,
	validate_fiscal_year,
)
from erpnext.accounts.utils import get_fiscal_year
from erpnext.assets.doctype.asset.asset import get_asset_value_after_depreciation


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = get_columns(filters)
	data = get_data(filters)
	chart = (
		prepare_chart_data(data, filters)
		if filters.get("group_by") not in ("Asset Category", "Location")
		else {}
	)

	return columns, data, None, chart


def get_conditions(filters):
	conditions = {"docstatus": 1}
	status = filters.status
	date_field = frappe.scrub(filters.date_based_on or "Purchase Date")

	if filters.get("company"):
		conditions["company"] = filters.company

	if filters.filter_based_on == "Date Range":
		if not filters.from_date and not filters.to_date:
			filters.from_date = add_months(nowdate(), -12)
			filters.to_date = nowdate()

		conditions[date_field] = ["between", [filters.from_date, filters.to_date]]
	elif filters.filter_based_on == "Fiscal Year":
		if not filters.from_fiscal_year and not filters.to_fiscal_year:
			default_fiscal_year = get_fiscal_year(today())[0]
			filters.from_fiscal_year = default_fiscal_year
			filters.to_fiscal_year = default_fiscal_year

		fiscal_year = get_fiscal_year_data(filters.from_fiscal_year, filters.to_fiscal_year)
		validate_fiscal_year(fiscal_year, filters.from_fiscal_year, filters.to_fiscal_year)
		filters.year_start_date = getdate(fiscal_year.year_start_date)
		filters.year_end_date = getdate(fiscal_year.year_end_date)

		conditions[date_field] = ["between", [filters.year_start_date, filters.year_end_date]]

	if filters.get("only_existing_assets"):
		conditions["is_existing_asset"] = filters.get("only_existing_assets")
	if filters.get("asset_category"):
		conditions["asset_category"] = filters.get("asset_category")
	if filters.get("cost_center"):
		conditions["cost_center"] = filters.get("cost_center")

	if status:
		# In Store assets are those that are not sold or scrapped or capitalized
		operand = "not in"
		if status not in "In Location":
			operand = "in"

		conditions["status"] = (operand, ["Sold", "Scrapped", "Capitalized"])

	return conditions


def get_data(filters):
	data = []

	conditions = get_conditions(filters)
	pr_supplier_map = get_purchase_receipt_supplier_map()
	pi_supplier_map = get_purchase_invoice_supplier_map()

	assets_linked_to_fb = get_assets_linked_to_fb(filters)

	company_fb = frappe.get_cached_value("Company", filters.company, "default_finance_book")

	if filters.include_default_book_assets and company_fb:
		finance_book = company_fb
	elif filters.finance_book:
		finance_book = filters.finance_book
	else:
		finance_book = None

	depreciation_amount_map = get_asset_depreciation_amount_map(filters, finance_book)

	group_by = frappe.scrub(filters.get("group_by"))

	if group_by in ("asset_category", "location"):
		data = get_group_by_data(group_by, conditions, assets_linked_to_fb, depreciation_amount_map)
		return data

	fields = [
		"name as asset_id",
		"asset_name",
		"status",
		"department",
		"company",
		"cost_center",
		"calculate_depreciation",
		"purchase_receipt",
		"asset_category",
		"purchase_date",
		"gross_purchase_amount",
		"location",
		"available_for_use_date",
		"purchase_invoice",
		"opening_accumulated_depreciation",
	]
	assets_record = frappe.db.get_all("Asset", filters=conditions, fields=fields)

	for asset in assets_record:
		if assets_linked_to_fb and asset.calculate_depreciation and asset.asset_id not in assets_linked_to_fb:
			continue

		depreciation_amount = depreciation_amount_map.get(asset.asset_id) or 0.0
		asset_value = (
			asset.gross_purchase_amount - asset.opening_accumulated_depreciation - depreciation_amount
		)

		row = {
			"asset_id": asset.asset_id,
			"asset_name": asset.asset_name,
			"status": asset.status,
			"department": asset.department,
			"cost_center": asset.cost_center,
			"vendor_name": pr_supplier_map.get(asset.purchase_receipt)
			or pi_supplier_map.get(asset.purchase_invoice),
			"gross_purchase_amount": asset.gross_purchase_amount,
			"opening_accumulated_depreciation": asset.opening_accumulated_depreciation,
			"depreciated_amount": depreciation_amount,
			"available_for_use_date": asset.available_for_use_date,
			"location": asset.location,
			"asset_category": asset.asset_category,
			"purchase_date": asset.purchase_date,
			"asset_value": asset_value,
			"company": asset.company,
		}
		data.append(row)

	return data


def prepare_chart_data(data, filters):
	if not data:
		return
	labels_values_map = {}
	if filters.filter_based_on not in ("Date Range", "Fiscal Year"):
		filters_filter_based_on = "Date Range"
		date_field = "purchase_date"
		filtered_data = [d for d in data if d.get(date_field)]
		filters_from_date = min(filtered_data, key=lambda a: a.get(date_field)).get(date_field)
		filters_to_date = max(filtered_data, key=lambda a: a.get(date_field)).get(date_field)
	else:
		filters_filter_based_on = filters.filter_based_on
		date_field = frappe.scrub(filters.date_based_on)
		filters_from_date = filters.from_date
		filters_to_date = filters.to_date

	period_list = get_period_list(
		filters.from_fiscal_year,
		filters.to_fiscal_year,
		filters_from_date,
		filters_to_date,
		filters_filter_based_on,
		"Monthly",
		company=filters.company,
		ignore_fiscal_year=True,
	)

	for d in period_list:
		labels_values_map.setdefault(
			d.get("label"), frappe._dict({"asset_value": 0, "depreciated_amount": 0})
		)

	for d in data:
		if d.get(date_field):
			date = d.get(date_field)
			belongs_to_month = formatdate(date, "MMM YYYY")

			labels_values_map[belongs_to_month].asset_value += d.get("asset_value")
			labels_values_map[belongs_to_month].depreciated_amount += d.get("depreciated_amount")

	return {
		"data": {
			"labels": labels_values_map.keys(),
			"datasets": [
				{
					"name": _("Asset Value"),
					"values": [flt(d.get("asset_value"), 2) for d in labels_values_map.values()],
				},
				{
					"name": _("Depreciatied Amount"),
					"values": [flt(d.get("depreciated_amount"), 2) for d in labels_values_map.values()],
				},
			],
		},
		"type": "bar",
		"barOptions": {"stacked": 1},
	}


def get_assets_linked_to_fb(filters):
	afb = frappe.qb.DocType("Asset Finance Book")

	query = frappe.qb.from_(afb).select(
		afb.parent,
	)

	if filters.include_default_book_assets:
		company_fb = frappe.get_cached_value("Company", filters.company, "default_finance_book")

		if filters.finance_book and company_fb and cstr(filters.finance_book) != cstr(company_fb):
			frappe.throw(_("To use a different finance book, please uncheck 'Include Default FB Assets'"))

		query = query.where(
			(afb.finance_book.isin([cstr(filters.finance_book), cstr(company_fb), ""]))
			| (afb.finance_book.isnull())
		)
	else:
		query = query.where(
			(afb.finance_book.isin([cstr(filters.finance_book), ""])) | (afb.finance_book.isnull())
		)

	assets_linked_to_fb = list(chain(*query.run(as_list=1)))

	return assets_linked_to_fb


def get_asset_depreciation_amount_map(filters, finance_book):
	start_date = filters.from_date if filters.filter_based_on == "Date Range" else filters.year_start_date
	end_date = filters.to_date if filters.filter_based_on == "Date Range" else filters.year_end_date

	asset = frappe.qb.DocType("Asset")
	gle = frappe.qb.DocType("GL Entry")
	aca = frappe.qb.DocType("Asset Category Account")
	company = frappe.qb.DocType("Company")

	query = (
		frappe.qb.from_(gle)
		.join(asset)
		.on(gle.against_voucher == asset.name)
		.join(aca)
		.on((aca.parent == asset.asset_category) & (aca.company_name == asset.company))
		.join(company)
		.on(company.name == asset.company)
		.select(asset.name.as_("asset"), Sum(gle.debit).as_("depreciation_amount"))
		.where(gle.account == IfNull(aca.depreciation_expense_account, company.depreciation_expense_account))
		.where(gle.debit != 0)
		.where(gle.is_cancelled == 0)
		.where(company.name == filters.company)
		.where(asset.docstatus == 1)
	)

	if filters.only_existing_assets:
		query = query.where(asset.is_existing_asset == 1)
	if filters.asset_category:
		query = query.where(asset.asset_category == filters.asset_category)
	if filters.cost_center:
		query = query.where(asset.cost_center == filters.cost_center)
	if filters.status:
		if filters.status == "In Location":
			query = query.where(asset.status.notin(["Sold", "Scrapped", "Capitalized"]))
		else:
			query = query.where(asset.status.isin(["Sold", "Scrapped", "Capitalized"]))
	if finance_book:
		query = query.where((gle.finance_book.isin([cstr(finance_book), ""])) | (gle.finance_book.isnull()))
	else:
		query = query.where((gle.finance_book.isin([""])) | (gle.finance_book.isnull()))
	if filters.filter_based_on in ("Date Range", "Fiscal Year"):
		query = query.where(gle.posting_date >= start_date)
		query = query.where(gle.posting_date <= end_date)

	query = query.groupby(asset.name)

	asset_depr_amount_map = query.run()

	return dict(asset_depr_amount_map)


def get_group_by_data(group_by, conditions, assets_linked_to_fb, depreciation_amount_map):
	fields = [
		group_by,
		"name",
		"gross_purchase_amount",
		"opening_accumulated_depreciation",
		"calculate_depreciation",
	]
	assets = frappe.db.get_all("Asset", filters=conditions, fields=fields)

	data = []

	for a in assets:
		if assets_linked_to_fb and a.calculate_depreciation and a.name not in assets_linked_to_fb:
			continue

		a["depreciated_amount"] = depreciation_amount_map.get(a["name"], 0.0)
		a["asset_value"] = (
			a["gross_purchase_amount"] - a["opening_accumulated_depreciation"] - a["depreciated_amount"]
		)

		del a["name"]
		del a["calculate_depreciation"]

		idx = ([i for i, d in enumerate(data) if a[group_by] == d[group_by]] or [None])[0]
		if idx is None:
			data.append(a)
		else:
			for field in (
				"gross_purchase_amount",
				"opening_accumulated_depreciation",
				"depreciated_amount",
				"asset_value",
			):
				data[idx][field] = data[idx][field] + a[field]

	return data


def get_purchase_receipt_supplier_map():
	return frappe._dict(
		frappe.db.sql(
			""" Select
		pr.name, pr.supplier
		FROM `tabPurchase Receipt` pr, `tabPurchase Receipt Item` pri
		WHERE
			pri.parent = pr.name
			AND pri.is_fixed_asset=1
			AND pr.docstatus=1
			AND pr.is_return=0"""
		)
	)


def get_purchase_invoice_supplier_map():
	return frappe._dict(
		frappe.db.sql(
			""" Select
		pi.name, pi.supplier
		FROM `tabPurchase Invoice` pi, `tabPurchase Invoice Item` pii
		WHERE
			pii.parent = pi.name
			AND pii.is_fixed_asset=1
			AND pi.docstatus=1
			AND pi.is_return=0"""
		)
	)


def get_columns(filters):
	if filters.get("group_by") in ["Asset Category", "Location"]:
		return [
			{
				"label": _("{}").format(filters.get("group_by")),
				"fieldtype": "Link",
				"fieldname": frappe.scrub(filters.get("group_by")),
				"options": filters.get("group_by"),
				"width": 216,
			},
			{
				"label": _("Gross Purchase Amount"),
				"fieldname": "gross_purchase_amount",
				"fieldtype": "Currency",
				"options": "Company:company:default_currency",
				"width": 250,
			},
			{
				"label": _("Opening Accumulated Depreciation"),
				"fieldname": "opening_accumulated_depreciation",
				"fieldtype": "Currency",
				"options": "Company:company:default_currency",
				"width": 250,
			},
			{
				"label": _("Depreciated Amount"),
				"fieldname": "depreciated_amount",
				"fieldtype": "Currency",
				"options": "Company:company:default_currency",
				"width": 250,
			},
			{
				"label": _("Asset Value"),
				"fieldname": "asset_value",
				"fieldtype": "Currency",
				"options": "Company:company:default_currency",
				"width": 250,
			},
			{
				"label": _("Company"),
				"fieldname": "company",
				"fieldtype": "Link",
				"options": "Company",
				"width": 120,
			},
		]

	return [
		{
			"label": _("Asset ID"),
			"fieldtype": "Link",
			"fieldname": "asset_id",
			"options": "Asset",
			"width": 60,
		},
		{"label": _("Asset Name"), "fieldtype": "Data", "fieldname": "asset_name", "width": 140},
		{
			"label": _("Asset Category"),
			"fieldtype": "Link",
			"fieldname": "asset_category",
			"options": "Asset Category",
			"width": 100,
		},
		{"label": _("Status"), "fieldtype": "Data", "fieldname": "status", "width": 80},
		{"label": _("Purchase Date"), "fieldtype": "Date", "fieldname": "purchase_date", "width": 90},
		{
			"label": _("Available For Use Date"),
			"fieldtype": "Date",
			"fieldname": "available_for_use_date",
			"width": 90,
		},
		{
			"label": _("Gross Purchase Amount"),
			"fieldname": "gross_purchase_amount",
			"fieldtype": "Currency",
			"options": "Company:company:default_currency",
			"width": 100,
		},
		{
			"label": _("Asset Value"),
			"fieldname": "asset_value",
			"fieldtype": "Currency",
			"options": "Company:company:default_currency",
			"width": 100,
		},
		{
			"label": _("Opening Accumulated Depreciation"),
			"fieldname": "opening_accumulated_depreciation",
			"fieldtype": "Currency",
			"options": "Company:company:default_currency",
			"width": 90,
		},
		{
			"label": _("Depreciated Amount"),
			"fieldname": "depreciated_amount",
			"fieldtype": "Currency",
			"options": "Company:company:default_currency",
			"width": 100,
		},
		{
			"label": _("Cost Center"),
			"fieldtype": "Link",
			"fieldname": "cost_center",
			"options": "Cost Center",
			"width": 100,
		},
		{
			"label": _("Department"),
			"fieldtype": "Link",
			"fieldname": "department",
			"options": "Department",
			"width": 100,
		},
		{"label": _("Vendor Name"), "fieldtype": "Data", "fieldname": "vendor_name", "width": 100},
		{
			"label": _("Location"),
			"fieldtype": "Link",
			"fieldname": "location",
			"options": "Location",
			"width": 100,
		},
		{
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 120,
		},
	]
