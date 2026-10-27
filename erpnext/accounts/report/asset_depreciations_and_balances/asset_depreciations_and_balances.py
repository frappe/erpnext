# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.query_builder.functions import IfNull, Sum
from frappe.utils import add_days, flt, formatdate

DISPOSAL_VALUE_FIELDS = {
	"Sold": "value_of_sold_asset",
	"Scrapped": "value_of_scrapped_asset",
	"Capitalized": "value_of_capitalized_asset",
}


def execute(filters=None):
	filters.day_before_from_date = add_days(filters.from_date, -1)
	columns, data = get_columns(filters), get_data(filters)
	return columns, data


def get_data(filters):
	if filters.get("group_by") == "Asset Category":
		return get_group_by_asset_category_data(filters)
	elif filters.get("group_by") == "Asset":
		return get_group_by_asset_data(filters)


def get_group_by_asset_category_data(filters):
	data = []

	asset_categories = get_asset_categories_for_grouped_by_category(filters)
	assets = get_assets_for_grouped_by_category(filters)
	asset_value_adjustment_map = get_asset_value_adjustment_map_by_category(filters)

	for asset_category in asset_categories:
		row = frappe._dict()
		row.update(asset_category)

		apply_value_adjustments(row, asset_value_adjustment_map.get(asset_category.get("asset_category"), {}))
		row.value_as_on_to_date = (
			flt(row.value_as_on_from_date)
			+ flt(row.value_of_new_purchase)
			- flt(row.value_of_sold_asset)
			- flt(row.value_of_scrapped_asset)
			- flt(row.value_of_capitalized_asset)
			+ flt(row.adjustment_during_period)
		)

		row.update(
			next(
				asset
				for asset in assets
				if asset["asset_category"] == asset_category.get("asset_category", "")
			)
		)

		row.accumulated_depreciation_as_on_to_date = (
			flt(row.accumulated_depreciation_as_on_from_date)
			+ flt(row.depreciation_amount_during_the_period)
			- flt(row.depreciation_eliminated_during_the_period)
			- flt(row.depreciation_eliminated_via_reversal)
		)

		row.net_asset_value_as_on_from_date = flt(row.value_as_on_from_date) - flt(
			row.accumulated_depreciation_as_on_from_date
		)

		row.net_asset_value_as_on_to_date = flt(row.value_as_on_to_date) - flt(
			row.accumulated_depreciation_as_on_to_date
		)

		data.append(row)

	return data


def get_asset_categories_for_grouped_by_category(filters):
	asset = frappe.qb.DocType("Asset")
	asset_depreciation_schedule = frappe.qb.DocType("Asset Depreciation Schedule")
	asset_capitalization_asset_item = frappe.qb.DocType("Asset Capitalization Asset Item")
	asset_capitalization = frappe.qb.DocType("Asset Capitalization")

	disposal_in_period = (
		(asset.disposal_date.isnotnull())
		& (asset.disposal_date >= filters.from_date)
		& (asset.disposal_date <= filters.to_date)
	)

	value_as_on_from_date = IfNull(
		Sum(
			frappe.qb.terms.Case()
			.when(
				(asset.purchase_date < filters.from_date)
				& ((asset.disposal_date.isnull()) | (asset.disposal_date >= filters.from_date)),
				asset.net_purchase_amount,
			)
			.else_(0)
		),
		0,
	).as_("value_as_on_from_date")

	value_of_new_purchase = IfNull(
		Sum(
			frappe.qb.terms.Case()
			.when(asset.purchase_date >= filters.from_date, asset.net_purchase_amount)
			.else_(0)
		),
		0,
	).as_("value_of_new_purchase")

	value_of_sold_asset = IfNull(
		Sum(
			frappe.qb.terms.Case()
			.when(disposal_in_period & (asset.status == "Sold"), asset.net_purchase_amount)
			.else_(0)
		),
		0,
	).as_("value_of_sold_asset")

	value_of_scrapped_asset = IfNull(
		Sum(
			frappe.qb.terms.Case()
			.when(disposal_in_period & (asset.status == "Scrapped"), asset.net_purchase_amount)
			.else_(0)
		),
		0,
	).as_("value_of_scrapped_asset")

	value_of_capitalized_asset = IfNull(
		Sum(
			frappe.qb.terms.Case()
			.when(disposal_in_period & (asset.status == "Capitalized"), asset.net_purchase_amount)
			.else_(0)
		),
		0,
	).as_("value_of_capitalized_asset")

	capitalized_before_from_date = (
		frappe.qb.from_(asset_capitalization_asset_item)
		.join(asset_capitalization)
		.on(asset_capitalization_asset_item.parent == asset_capitalization.name)
		.select(asset_capitalization_asset_item.asset)
		.where(asset_capitalization.posting_date < filters.from_date)
		.where(asset_capitalization.docstatus == 1)
	)

	query = (
		frappe.qb.from_(asset)
		.select(
			asset.asset_category,
			value_as_on_from_date,
			value_of_new_purchase,
			value_of_sold_asset,
			value_of_scrapped_asset,
			value_of_capitalized_asset,
		)
		.where(asset.docstatus == 1)
		.where(asset.company == filters.company)
		.where(asset.purchase_date <= filters.to_date)
		.where(asset.name.notin(capitalized_before_from_date))
		.groupby(asset.asset_category)
	)

	if filters.get("asset_category"):
		query = query.where(asset.asset_category == filters.get("asset_category"))

	if filters.get("finance_book"):
		assets_with_finance_book = (
			frappe.qb.from_(asset_depreciation_schedule)
			.select(asset_depreciation_schedule.asset)
			.where(asset_depreciation_schedule.finance_book == filters.get("finance_book"))
		)
		query = query.where(asset.name.isin(assets_with_finance_book))

	return query.run(as_dict=True)


def get_assets_for_grouped_by_category(filters):
	asset = frappe.qb.DocType("Asset")
	gl_entry = frappe.qb.DocType("GL Entry")
	asset_category_account = frappe.qb.DocType("Asset Category Account")
	company = frappe.qb.DocType("Company")
	asset_depreciation_schedule = frappe.qb.DocType("Asset Depreciation Schedule")

	assets_with_finance_book = None
	if filters.get("finance_book"):
		assets_with_finance_book = (
			frappe.qb.from_(asset_depreciation_schedule)
			.select(asset_depreciation_schedule.asset)
			.where(asset_depreciation_schedule.finance_book == filters.get("finance_book"))
		)

	from_gl_entries_query = (
		frappe.qb.from_(gl_entry)
		.join(asset)
		.on(gl_entry.against_voucher == asset.name)
		.join(asset_category_account)
		.on(
			(asset_category_account.parent == asset.asset_category)
			& (asset_category_account.company_name == filters.company)
		)
		.join(company)
		.on(company.name == filters.company)
		.select(
			asset.asset_category,
			IfNull(
				Sum(
					frappe.qb.terms.Case()
					.when(
						(gl_entry.posting_date < filters.from_date)
						& ((asset.disposal_date.isnull()) | (asset.disposal_date >= filters.from_date)),
						gl_entry.debit - gl_entry.credit,
					)
					.else_(0)
				),
				0,
			).as_("accumulated_depreciation_as_on_from_date"),
			IfNull(
				Sum(
					frappe.qb.terms.Case()
					.when(
						(gl_entry.posting_date >= filters.from_date)
						& (gl_entry.posting_date <= filters.to_date)
						& ((asset.disposal_date.isnull()) | (gl_entry.posting_date <= asset.disposal_date)),
						gl_entry.credit,
					)
					.else_(0)
				),
				0,
			).as_("depreciation_eliminated_via_reversal"),
			IfNull(
				Sum(
					frappe.qb.terms.Case()
					.when(
						(asset.disposal_date.isnotnull())
						& (asset.disposal_date >= filters.from_date)
						& (asset.disposal_date <= filters.to_date)
						& (gl_entry.posting_date <= asset.disposal_date),
						gl_entry.debit - gl_entry.credit,
					)
					.else_(0)
				),
				0,
			).as_("depreciation_eliminated_during_the_period"),
			IfNull(
				Sum(
					frappe.qb.terms.Case()
					.when(
						(gl_entry.posting_date >= filters.from_date)
						& (gl_entry.posting_date <= filters.to_date)
						& ((asset.disposal_date.isnull()) | (gl_entry.posting_date <= asset.disposal_date)),
						gl_entry.debit,
					)
					.else_(0)
				),
				0,
			).as_("depreciation_amount_during_the_period"),
		)
		.where(asset.docstatus == 1)
		.where(asset.company == filters.company)
		.where(asset.purchase_date <= filters.to_date)
		.where(gl_entry.is_cancelled == 0)
		.where(
			gl_entry.account
			== IfNull(
				asset_category_account.depreciation_expense_account,
				company.depreciation_expense_account,
			)
		)
		.groupby(asset.asset_category)
	)

	from_opening_depreciation_query = (
		frappe.qb.from_(asset)
		.select(
			asset.asset_category,
			IfNull(
				Sum(
					frappe.qb.terms.Case()
					.when(
						(asset.disposal_date.isnotnull()) & (asset.disposal_date < filters.from_date),
						0,
					)
					.else_(asset.opening_accumulated_depreciation)
				),
				0,
			).as_("accumulated_depreciation_as_on_from_date"),
			IfNull(
				Sum(
					frappe.qb.terms.Case()
					.when(
						(asset.disposal_date >= filters.from_date) & (asset.disposal_date <= filters.to_date),
						asset.opening_accumulated_depreciation,
					)
					.else_(0)
				),
				0,
			).as_("depreciation_eliminated_during_the_period"),
		)
		.where(asset.docstatus == 1)
		.where(asset.company == filters.company)
		.where(asset.purchase_date <= filters.to_date)
		.groupby(asset.asset_category)
	)

	if filters.get("asset_category"):
		from_gl_entries_query = from_gl_entries_query.where(
			asset.asset_category == filters.get("asset_category")
		)
		from_opening_depreciation_query = from_opening_depreciation_query.where(
			asset.asset_category == filters.get("asset_category")
		)

	from_gl_entries_query = from_gl_entries_query.where(get_finance_book_condition(gl_entry, filters))
	if assets_with_finance_book is not None:
		from_gl_entries_query = from_gl_entries_query.where(asset.name.isin(assets_with_finance_book))
		from_opening_depreciation_query = from_opening_depreciation_query.where(
			asset.name.isin(assets_with_finance_book)
		)

	combined = {}

	for row in from_gl_entries_query.run(as_dict=True):
		combined[row.asset_category] = {
			"asset_category": row.asset_category,
			"accumulated_depreciation_as_on_from_date": flt(row.accumulated_depreciation_as_on_from_date),
			"depreciation_eliminated_via_reversal": flt(row.depreciation_eliminated_via_reversal),
			"depreciation_eliminated_during_the_period": flt(row.depreciation_eliminated_during_the_period),
			"depreciation_amount_during_the_period": flt(row.depreciation_amount_during_the_period),
		}

	for row in from_opening_depreciation_query.run(as_dict=True):
		if row.asset_category not in combined:
			combined[row.asset_category] = {
				"asset_category": row.asset_category,
				"accumulated_depreciation_as_on_from_date": 0.0,
				"depreciation_eliminated_via_reversal": 0.0,
				"depreciation_eliminated_during_the_period": 0.0,
				"depreciation_amount_during_the_period": 0.0,
			}

		combined[row.asset_category]["accumulated_depreciation_as_on_from_date"] += flt(
			row.accumulated_depreciation_as_on_from_date
		)
		combined[row.asset_category]["depreciation_eliminated_during_the_period"] += flt(
			row.depreciation_eliminated_during_the_period
		)

	return list(combined.values())


def get_finance_book_condition(gl_entry, filters):
	"""GL rows with no finance book, plus the selected book or else the company's default book."""
	finance_book = filters.get("finance_book") or frappe.get_cached_value(
		"Company", filters.company, "default_finance_book"
	)
	return IfNull(gl_entry.finance_book, "").isin(["", finance_book or ""])


def get_asset_value_adjustment_map_by_category(filters):
	asset = frappe.qb.DocType("Asset")
	gl_entry = frappe.qb.DocType("GL Entry")
	asset_category_account = frappe.qb.DocType("Asset Category Account")

	asset_value_adjustments = (
		frappe.qb.from_(gl_entry)
		.join(asset)
		.on(gl_entry.against_voucher == asset.name)
		.join(asset_category_account)
		.on(
			(asset_category_account.parent == asset.asset_category)
			& (asset_category_account.company_name == filters.company)
		)
		.select(
			asset.asset_category.as_("asset_category"),
			*get_value_adjustment_columns(asset, gl_entry, filters),
		)
		.where(gl_entry.is_cancelled == 0)
		.where(asset.docstatus == 1)
		.where(asset.company == filters.company)
		.where(asset.purchase_date <= filters.to_date)
		.where(gl_entry.account == asset_category_account.fixed_asset_account)
		.where(gl_entry.is_opening == "No")
		.where(get_finance_book_condition(gl_entry, filters))
		.groupby(asset.asset_category)
	).run(as_dict=True)

	return {row.pop("asset_category"): row for row in asset_value_adjustments}


def get_group_by_asset_data(filters):
	data = []

	asset_details = get_asset_details_for_grouped_by_category(filters)
	assets = get_assets_for_grouped_by_asset(filters)
	asset_value_adjustment_map = get_asset_value_adjustment_map(filters)

	for asset_detail in asset_details:
		row = frappe._dict()
		row.update(asset_detail)

		row.update(next(asset for asset in assets if asset["asset"] == asset_detail.get("name", "")))
		apply_value_adjustments(row, asset_value_adjustment_map.get(asset_detail.get("name", ""), {}))
		row.value_as_on_to_date = (
			flt(row.value_as_on_from_date)
			+ flt(row.value_of_new_purchase)
			- flt(row.value_of_sold_asset)
			- flt(row.value_of_scrapped_asset)
			- flt(row.value_of_capitalized_asset)
			+ flt(row.adjustment_during_period)
		)

		row.accumulated_depreciation_as_on_to_date = (
			flt(row.accumulated_depreciation_as_on_from_date)
			+ flt(row.depreciation_amount_during_the_period)
			- flt(row.depreciation_eliminated_during_the_period)
			- flt(row.depreciation_eliminated_via_reversal)
		)

		row.net_asset_value_as_on_from_date = flt(row.value_as_on_from_date) - flt(
			row.accumulated_depreciation_as_on_from_date
		)

		row.net_asset_value_as_on_to_date = flt(row.value_as_on_to_date) - flt(
			row.accumulated_depreciation_as_on_to_date
		)

		data.append(row)

	return data


def get_asset_details_for_grouped_by_category(filters):
	asset = frappe.qb.DocType("Asset")
	asset_depreciation_schedule = frappe.qb.DocType("Asset Depreciation Schedule")
	asset_capitalization_asset_item = frappe.qb.DocType("Asset Capitalization Asset Item")
	asset_capitalization = frappe.qb.DocType("Asset Capitalization")

	disposal_in_period = (
		(asset.disposal_date.isnotnull())
		& (asset.disposal_date >= filters.from_date)
		& (asset.disposal_date <= filters.to_date)
	)

	capitalized_before_from_date = (
		frappe.qb.from_(asset_capitalization_asset_item)
		.join(asset_capitalization)
		.on(asset_capitalization_asset_item.parent == asset_capitalization.name)
		.select(asset_capitalization_asset_item.asset)
		.where(asset_capitalization.posting_date < filters.from_date)
		.where(asset_capitalization.docstatus == 1)
	)

	query = (
		frappe.qb.from_(asset)
		.select(
			asset.name,
			asset.asset_name,
			IfNull(
				Sum(
					frappe.qb.terms.Case()
					.when(
						(asset.purchase_date < filters.from_date)
						& ((asset.disposal_date.isnull()) | (asset.disposal_date >= filters.from_date)),
						asset.net_purchase_amount,
					)
					.else_(0)
				),
				0,
			).as_("value_as_on_from_date"),
			IfNull(
				Sum(
					frappe.qb.terms.Case()
					.when(asset.purchase_date >= filters.from_date, asset.net_purchase_amount)
					.else_(0)
				),
				0,
			).as_("value_of_new_purchase"),
			IfNull(
				Sum(
					frappe.qb.terms.Case()
					.when(disposal_in_period & (asset.status == "Sold"), asset.net_purchase_amount)
					.else_(0)
				),
				0,
			).as_("value_of_sold_asset"),
			IfNull(
				Sum(
					frappe.qb.terms.Case()
					.when(disposal_in_period & (asset.status == "Scrapped"), asset.net_purchase_amount)
					.else_(0)
				),
				0,
			).as_("value_of_scrapped_asset"),
			IfNull(
				Sum(
					frappe.qb.terms.Case()
					.when(
						disposal_in_period & (asset.status == "Capitalized"),
						asset.net_purchase_amount,
					)
					.else_(0)
				),
				0,
			).as_("value_of_capitalized_asset"),
		)
		.where(asset.docstatus == 1)
		.where(asset.company == filters.company)
		.where(asset.purchase_date <= filters.to_date)
		.where(asset.name.notin(capitalized_before_from_date))
		.where(asset.name.isin(frappe.qb.get_query("Asset", fields=["name"], ignore_permissions=False)))
		.groupby(asset.name)
	)

	if filters.get("asset"):
		query = query.where(asset.name == filters.get("asset"))

	if filters.get("finance_book"):
		assets_with_finance_book = (
			frappe.qb.from_(asset_depreciation_schedule)
			.select(asset_depreciation_schedule.asset)
			.where(asset_depreciation_schedule.finance_book == filters.get("finance_book"))
		)
		query = query.where(asset.name.isin(assets_with_finance_book))

	return query.run(as_dict=True)


def get_assets_for_grouped_by_asset(filters):
	asset = frappe.qb.DocType("Asset")
	gl_entry = frappe.qb.DocType("GL Entry")
	asset_category_account = frappe.qb.DocType("Asset Category Account")
	company = frappe.qb.DocType("Company")
	asset_depreciation_schedule = frappe.qb.DocType("Asset Depreciation Schedule")

	assets_with_finance_book = None
	if filters.get("finance_book"):
		assets_with_finance_book = (
			frappe.qb.from_(asset_depreciation_schedule)
			.select(asset_depreciation_schedule.asset)
			.where(asset_depreciation_schedule.finance_book == filters.get("finance_book"))
		)

	from_gl_entries_query = (
		frappe.qb.from_(gl_entry)
		.join(asset)
		.on(gl_entry.against_voucher == asset.name)
		.join(asset_category_account)
		.on(
			(asset_category_account.parent == asset.asset_category)
			& (asset_category_account.company_name == filters.company)
		)
		.join(company)
		.on(company.name == filters.company)
		.select(
			asset.name.as_("asset"),
			IfNull(
				Sum(
					frappe.qb.terms.Case()
					.when(
						(gl_entry.posting_date < filters.from_date)
						& ((asset.disposal_date.isnull()) | (asset.disposal_date >= filters.from_date)),
						gl_entry.debit - gl_entry.credit,
					)
					.else_(0)
				),
				0,
			).as_("accumulated_depreciation_as_on_from_date"),
			IfNull(
				Sum(
					frappe.qb.terms.Case()
					.when(
						(gl_entry.posting_date >= filters.from_date)
						& (gl_entry.posting_date <= filters.to_date)
						& ((asset.disposal_date.isnull()) | (gl_entry.posting_date <= asset.disposal_date)),
						gl_entry.credit,
					)
					.else_(0)
				),
				0,
			).as_("depreciation_eliminated_via_reversal"),
			IfNull(
				Sum(
					frappe.qb.terms.Case()
					.when(
						(asset.disposal_date.isnotnull())
						& (asset.disposal_date >= filters.from_date)
						& (asset.disposal_date <= filters.to_date)
						& (gl_entry.posting_date <= asset.disposal_date),
						gl_entry.debit - gl_entry.credit,
					)
					.else_(0)
				),
				0,
			).as_("depreciation_eliminated_during_the_period"),
			IfNull(
				Sum(
					frappe.qb.terms.Case()
					.when(
						(gl_entry.posting_date >= filters.from_date)
						& (gl_entry.posting_date <= filters.to_date)
						& ((asset.disposal_date.isnull()) | (gl_entry.posting_date <= asset.disposal_date)),
						gl_entry.debit,
					)
					.else_(0)
				),
				0,
			).as_("depreciation_amount_during_the_period"),
		)
		.where(asset.docstatus == 1)
		.where(asset.company == filters.company)
		.where(asset.purchase_date <= filters.to_date)
		.where(gl_entry.is_cancelled == 0)
		.where(
			gl_entry.account
			== IfNull(
				asset_category_account.depreciation_expense_account,
				company.depreciation_expense_account,
			)
		)
		.groupby(asset.name)
	)

	from_opening_depreciation_query = (
		frappe.qb.from_(asset)
		.select(
			asset.name.as_("asset"),
			IfNull(
				Sum(
					frappe.qb.terms.Case()
					.when(
						(asset.disposal_date.isnotnull()) & (asset.disposal_date < filters.from_date),
						0,
					)
					.else_(asset.opening_accumulated_depreciation)
				),
				0,
			).as_("accumulated_depreciation_as_on_from_date"),
			IfNull(
				Sum(
					frappe.qb.terms.Case()
					.when(
						(asset.disposal_date >= filters.from_date) & (asset.disposal_date <= filters.to_date),
						asset.opening_accumulated_depreciation,
					)
					.else_(0)
				),
				0,
			).as_("depreciation_eliminated_during_the_period"),
		)
		.where(asset.docstatus == 1)
		.where(asset.company == filters.company)
		.where(asset.purchase_date <= filters.to_date)
		.groupby(asset.name)
	)

	if filters.get("asset"):
		from_gl_entries_query = from_gl_entries_query.where(asset.name == filters.get("asset"))
		from_opening_depreciation_query = from_opening_depreciation_query.where(
			asset.name == filters.get("asset")
		)

	from_gl_entries_query = from_gl_entries_query.where(get_finance_book_condition(gl_entry, filters))
	if assets_with_finance_book is not None:
		from_gl_entries_query = from_gl_entries_query.where(asset.name.isin(assets_with_finance_book))
		from_opening_depreciation_query = from_opening_depreciation_query.where(
			asset.name.isin(assets_with_finance_book)
		)

	combined = {}

	for row in from_gl_entries_query.run(as_dict=True):
		combined[row.asset] = {
			"asset": row.asset,
			"accumulated_depreciation_as_on_from_date": flt(row.accumulated_depreciation_as_on_from_date),
			"depreciation_eliminated_via_reversal": flt(row.depreciation_eliminated_via_reversal),
			"depreciation_eliminated_during_the_period": flt(row.depreciation_eliminated_during_the_period),
			"depreciation_amount_during_the_period": flt(row.depreciation_amount_during_the_period),
		}

	for row in from_opening_depreciation_query.run(as_dict=True):
		if row.asset not in combined:
			combined[row.asset] = {
				"asset": row.asset,
				"accumulated_depreciation_as_on_from_date": 0.0,
				"depreciation_eliminated_via_reversal": 0.0,
				"depreciation_eliminated_during_the_period": 0.0,
				"depreciation_amount_during_the_period": 0.0,
			}

		combined[row.asset]["accumulated_depreciation_as_on_from_date"] += flt(
			row.accumulated_depreciation_as_on_from_date
		)
		combined[row.asset]["depreciation_eliminated_during_the_period"] += flt(
			row.depreciation_eliminated_during_the_period
		)

	return list(combined.values())


def get_asset_value_adjustment_map(filters):
	asset = frappe.qb.DocType("Asset")
	gl_entry = frappe.qb.DocType("GL Entry")
	asset_category_account = frappe.qb.DocType("Asset Category Account")

	asset_with_value_adjustments = (
		frappe.qb.from_(gl_entry)
		.join(asset)
		.on(gl_entry.against_voucher == asset.name)
		.join(asset_category_account)
		.on(
			(asset_category_account.parent == asset.asset_category)
			& (asset_category_account.company_name == filters.company)
		)
		.select(
			asset.name.as_("asset"),
			*get_value_adjustment_columns(asset, gl_entry, filters),
		)
		.where(gl_entry.is_cancelled == 0)
		.where(asset.docstatus == 1)
		.where(asset.company == filters.company)
		.where(asset.purchase_date <= filters.to_date)
		.where(gl_entry.account == asset_category_account.fixed_asset_account)
		.where(gl_entry.is_opening == "No")
		.where(get_finance_book_condition(gl_entry, filters))
		.groupby(asset.name)
	).run(as_dict=True)

	return {row.pop("asset"): row for row in asset_with_value_adjustments}


def get_value_adjustment_columns(asset, gl_entry, filters) -> list:
	"""Fixed asset GL rows other than the disposal entry, summed before the period, till its end and,
	for assets disposed in the period, till its end by how they were disposed."""
	is_adjustment = gl_entry.voucher_type.notin(["Sales Invoice", "Asset Capitalization"]) & (
		gl_entry.voucher_no != IfNull(asset.journal_entry_for_scrap, "")
	)
	held_in_period = asset.disposal_date.isnull() | (asset.disposal_date >= filters.from_date)
	till_to_date = is_adjustment & held_in_period & (gl_entry.posting_date <= filters.to_date)
	disposed_in_period = asset.disposal_date.isnotnull() & (asset.disposal_date <= filters.to_date)

	return [
		get_adjustment_sum(
			gl_entry,
			held_in_period & (gl_entry.posting_date < filters.from_date),
			"adjustment_before_from_date",
		),
		get_adjustment_sum(gl_entry, till_to_date, "adjustment_till_to_date"),
		*(
			get_adjustment_sum(
				gl_entry,
				till_to_date & disposed_in_period & (asset.status == status),
				f"adjustment_of_{fieldname}",
			)
			for status, fieldname in DISPOSAL_VALUE_FIELDS.items()
		),
	]


def get_adjustment_sum(gl_entry, condition, alias: str):
	amount = frappe.qb.terms.Case().when(condition, gl_entry.debit - gl_entry.credit).else_(0)
	return IfNull(Sum(amount), 0).as_(alias)


def apply_value_adjustments(row, adjustments: dict) -> None:
	"""Add value adjustments to the opening value, to the period, and to the value of assets disposed in it."""
	row.adjustment_during_period = flt(adjustments.get("adjustment_till_to_date")) - flt(
		adjustments.get("adjustment_before_from_date")
	)
	row.value_as_on_from_date += flt(adjustments.get("adjustment_before_from_date"))
	for fieldname in DISPOSAL_VALUE_FIELDS.values():
		row[fieldname] = flt(row[fieldname]) + flt(adjustments.get(f"adjustment_of_{fieldname}"))


def get_columns(filters):
	columns = []

	if filters.get("group_by") == "Asset Category":
		columns.append(
			{
				"label": _("Asset Category"),
				"fieldname": "asset_category",
				"fieldtype": "Link",
				"options": "Asset Category",
				"width": 120,
			}
		)
	elif filters.get("group_by") == "Asset":
		columns.append(
			{
				"label": _("Asset"),
				"fieldname": "asset",
				"fieldtype": "Link",
				"options": "Asset",
				"width": 120,
			}
		)
		columns.append(
			{
				"label": _("Asset Name"),
				"fieldname": "asset_name",
				"fieldtype": "Data",
				"width": 140,
			}
		)

	columns += [
		{
			"label": _("Value as on") + " " + formatdate(filters.day_before_from_date),
			"fieldname": "value_as_on_from_date",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _("Value of New Purchase"),
			"fieldname": "value_of_new_purchase",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _("Value of Sold Asset"),
			"fieldname": "value_of_sold_asset",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _("Value of Scrapped Asset"),
			"fieldname": "value_of_scrapped_asset",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _("Value of Assets Consumed in Capitalization"),
			"fieldname": "value_of_capitalized_asset",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _("Adjustment during the period"),
			"fieldname": "adjustment_during_period",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _("Value as on") + " " + formatdate(filters.to_date),
			"fieldname": "value_as_on_to_date",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _("Accumulated Depreciation as on") + " " + formatdate(filters.day_before_from_date),
			"fieldname": "accumulated_depreciation_as_on_from_date",
			"fieldtype": "Currency",
			"width": 270,
		},
		{
			"label": _("Depreciation Amount during the period"),
			"fieldname": "depreciation_amount_during_the_period",
			"fieldtype": "Currency",
			"width": 240,
		},
		{
			"label": _("Depreciation Eliminated due to disposal of assets"),
			"fieldname": "depreciation_eliminated_during_the_period",
			"fieldtype": "Currency",
			"width": 300,
		},
		{
			"label": _("Accumulated Depreciation as on") + " " + formatdate(filters.to_date),
			"fieldname": "accumulated_depreciation_as_on_to_date",
			"fieldtype": "Currency",
			"width": 270,
		},
		{
			"label": _("Depreciation eliminated via reversal"),
			"fieldname": "depreciation_eliminated_via_reversal",
			"fieldtype": "Currency",
			"width": 270,
		},
		{
			"label": _("Net Asset value as on") + " " + formatdate(filters.day_before_from_date),
			"fieldname": "net_asset_value_as_on_from_date",
			"fieldtype": "Currency",
			"width": 200,
		},
		{
			"label": _("Net Asset value as on") + " " + formatdate(filters.to_date),
			"fieldname": "net_asset_value_as_on_to_date",
			"fieldtype": "Currency",
			"width": 200,
		},
	]

	return columns
