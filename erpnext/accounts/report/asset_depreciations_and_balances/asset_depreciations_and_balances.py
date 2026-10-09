# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import add_days, cstr, flt, formatdate

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
	condition = ""
	if filters.get("asset_category"):
		condition += " and a.asset_category = %(asset_category)s"
	if filters.get("finance_book"):
		condition += " and exists (select 1 from `tabAsset Depreciation Schedule` ads where ads.asset = a.name and ads.finance_book = %(finance_book)s)"

	# nosemgrep
	return frappe.db.sql(
		f"""
		SELECT a.asset_category,
			   ifnull(sum(case when a.purchase_date < %(from_date)s then
							   case when ifnull(a.disposal_date, 0) = 0 or a.disposal_date >= %(from_date)s then
									a.gross_purchase_amount
							   else
									0
							   end
						   else
								0
						   end), 0) as value_as_on_from_date,
			   ifnull(sum(case when a.purchase_date >= %(from_date)s then
			   						a.gross_purchase_amount
			   				   else
			   				   		0
			   				   end), 0) as value_of_new_purchase,
			   ifnull(sum(case when ifnull(a.disposal_date, 0) != 0
			   						and a.disposal_date >= %(from_date)s
			   						and a.disposal_date <= %(to_date)s then
							   case when a.status = "Sold" then
							   		a.gross_purchase_amount
							   else
							   		0
							   end
						   else
								0
						   end), 0) as value_of_sold_asset,
			   ifnull(sum(case when ifnull(a.disposal_date, 0) != 0
			   						and a.disposal_date >= %(from_date)s
			   						and a.disposal_date <= %(to_date)s then
							   case when a.status = "Scrapped" then
							   		a.gross_purchase_amount
							   else
							   		0
							   end
						   else
								0
						   end), 0) as value_of_scrapped_asset,
				ifnull(sum(case when ifnull(a.disposal_date, 0) != 0
			   						and a.disposal_date >= %(from_date)s
			   						and a.disposal_date <= %(to_date)s then
							   case when a.status = "Capitalized" then
							   		a.gross_purchase_amount
							   else
							   		0
							   end
						   else
								0
						   end), 0) as value_of_capitalized_asset
		from `tabAsset` a
		where a.docstatus=1 and a.company=%(company)s and a.purchase_date <= %(to_date)s {condition}
			and not exists(
				select 1 from `tabAsset Capitalization Asset Item` acai join `tabAsset Capitalization` ac on acai.parent=ac.name
				where acai.asset = a.name
				and ac.posting_date < %(from_date)s
				and ac.docstatus=1
			)
		group by a.asset_category
	""",
		{
			"to_date": filters.to_date,
			"from_date": filters.from_date,
			"company": filters.company,
			"asset_category": filters.get("asset_category"),
			"finance_book": filters.get("finance_book"),
		},
		as_dict=1,
	)


def get_assets_for_grouped_by_category(filters):
	condition = ""
	if filters.get("asset_category"):
		condition = f" and a.asset_category = '{filters.get('asset_category')}'"
	finance_book_filter = f" and {get_finance_book_condition(filters)}"
	if filters.get("finance_book"):
		condition += " and exists (select 1 from `tabAsset Depreciation Schedule` ads where ads.asset = a.name and ads.finance_book = %(finance_book)s)"

	# nosemgrep
	return frappe.db.sql(
		f"""
		SELECT results.asset_category,
			   sum(results.accumulated_depreciation_as_on_from_date) as accumulated_depreciation_as_on_from_date,
			   sum(results.depreciation_eliminated_via_reversal) as depreciation_eliminated_via_reversal,
			   sum(results.depreciation_eliminated_during_the_period) as depreciation_eliminated_during_the_period,
			   sum(results.depreciation_amount_during_the_period) as depreciation_amount_during_the_period
		from (SELECT a.asset_category,
				   ifnull(sum(case when gle.posting_date < %(from_date)s and (ifnull(a.disposal_date, 0) = 0 or a.disposal_date >= %(from_date)s) then
								   gle.debit - gle.credit
							  else
								   0
							  end), 0) as accumulated_depreciation_as_on_from_date,
				   ifnull(sum(case when gle.posting_date >= %(from_date)s and gle.posting_date <= %(to_date)s
										and (ifnull(a.disposal_date, 0) = 0 or gle.posting_date <= a.disposal_date) then
								   gle.credit
							  else
								   0
							  end), 0) as depreciation_eliminated_via_reversal,
				   ifnull(sum(case when ifnull(a.disposal_date, 0) != 0 and a.disposal_date >= %(from_date)s
										and a.disposal_date <= %(to_date)s and gle.posting_date <= a.disposal_date then
								   gle.debit - gle.credit
							  else
								   0
							  end), 0) as depreciation_eliminated_during_the_period,
				   ifnull(sum(case when gle.posting_date >= %(from_date)s and gle.posting_date <= %(to_date)s
										and (ifnull(a.disposal_date, 0) = 0 or gle.posting_date <= a.disposal_date) then
								   gle.debit
							  else
								   0
							  end), 0) as depreciation_amount_during_the_period
			from `tabGL Entry` gle
			join `tabAsset` a on
				gle.against_voucher = a.name
			join `tabAsset Category Account` aca on
				aca.parent = a.asset_category and aca.company_name = %(company)s
			join `tabCompany` company on
				company.name = %(company)s
			where
				a.docstatus=1
				and a.company=%(company)s
				and a.purchase_date <= %(to_date)s
				and gle.is_cancelled = 0
				and gle.account = ifnull(aca.depreciation_expense_account, company.depreciation_expense_account)
				{condition} {finance_book_filter}
			group by a.asset_category
			union
			SELECT a.asset_category,
				   ifnull(sum(case when ifnull(a.disposal_date, 0) != 0 and a.disposal_date < %(from_date)s then
									0
							   else
									a.opening_accumulated_depreciation
							   end), 0) as accumulated_depreciation_as_on_from_date,
				0 as depreciation_eliminated_via_reversal,
				   ifnull(sum(case when a.disposal_date >= %(from_date)s and a.disposal_date <= %(to_date)s then
								   a.opening_accumulated_depreciation
							  else
								   0
							  end), 0) as depreciation_eliminated_during_the_period,
				   0 as depreciation_amount_during_the_period
			from `tabAsset` a
			where a.docstatus=1 and a.company=%(company)s and a.purchase_date <= %(to_date)s {condition}
			group by a.asset_category) as results
		group by results.asset_category
		""",
		{
			"to_date": filters.to_date,
			"from_date": filters.from_date,
			"company": filters.company,
			"finance_book": filters.get("finance_book", ""),
		},
		as_dict=1,
	)


def get_finance_book_condition(filters) -> str:
	"""GL rows with no finance book, plus the selected book or else the company's default book."""
	finance_book = filters.get("finance_book") or frappe.get_cached_value(
		"Company", filters.company, "default_finance_book"
	)
	return f"ifnull(gle.finance_book, '') in ('', {frappe.db.escape(cstr(finance_book))})"


def get_asset_value_adjustment_map_by_category(filters):
	# nosemgrep
	asset_value_adjustments = frappe.db.sql(
		f"""
		SELECT
			a.asset_category AS asset_category,
			{get_value_adjustment_columns()}

		FROM `tabGL Entry` gle
		JOIN `tabAsset` a ON gle.against_voucher = a.name
		JOIN `tabAsset Category Account` aca
			ON aca.parent = a.asset_category
			AND aca.company_name = %(company)s
		WHERE gle.is_cancelled = 0
			AND a.docstatus = 1
			AND a.company = %(company)s
			AND a.purchase_date <= %(to_date)s
			AND gle.account = aca.fixed_asset_account
			AND gle.is_opening = 'No'
			AND {get_finance_book_condition(filters)}
		GROUP BY a.asset_category
	""",
		{"from_date": filters.from_date, "to_date": filters.to_date, "company": filters.company},
		as_dict=1,
	)

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
	condition = ""
	if filters.get("asset"):
		condition += " and a.name = %(asset)s"
	if filters.get("finance_book"):
		condition += " and exists (select 1 from `tabAsset Depreciation Schedule` ads where ads.asset = a.name and ads.finance_book = %(finance_book)s)"

	# nosemgrep
	asset_details = frappe.db.sql(
		f"""
		SELECT a.name, a.asset_name,
			   ifnull(sum(case when a.purchase_date < %(from_date)s then
							   case when ifnull(a.disposal_date, 0) = 0 or a.disposal_date >= %(from_date)s then
									a.gross_purchase_amount
							   else
									0
							   end
						   else
								0
						   end), 0) as value_as_on_from_date,
			   ifnull(sum(case when a.purchase_date >= %(from_date)s then
			   						a.gross_purchase_amount
			   				   else
			   				   		0
			   				   end), 0) as value_of_new_purchase,
			   ifnull(sum(case when ifnull(a.disposal_date, 0) != 0
			   						and a.disposal_date >= %(from_date)s
			   						and a.disposal_date <= %(to_date)s then
							   case when a.status = "Sold" then
							   		a.gross_purchase_amount
							   else
							   		0
							   end
						   else
								0
						   end), 0) as value_of_sold_asset,
			   ifnull(sum(case when ifnull(a.disposal_date, 0) != 0
			   						and a.disposal_date >= %(from_date)s
			   						and a.disposal_date <= %(to_date)s then
							   case when a.status = "Scrapped" then
							   		a.gross_purchase_amount
							   else
							   		0
							   end
						   else
								0
						   end), 0) as value_of_scrapped_asset,
				ifnull(sum(case when ifnull(a.disposal_date, 0) != 0
			   						and a.disposal_date >= %(from_date)s
			   						and a.disposal_date <= %(to_date)s then
							   case when a.status = "Capitalized" then
							   		a.gross_purchase_amount
							   else
							   		0
							   end
						   else
								0
						   end), 0) as value_of_capitalized_asset
		from `tabAsset` a
		where a.docstatus=1 and a.company=%(company)s and a.purchase_date <= %(to_date)s {condition}
		and not exists(
				select 1 from `tabAsset Capitalization Asset Item` acai join `tabAsset Capitalization` ac on acai.parent=ac.name
				where acai.asset = a.name
				and ac.posting_date < %(from_date)s
				and ac.docstatus=1
			)
		group by a.name
	""",
		{
			"to_date": filters.to_date,
			"from_date": filters.from_date,
			"company": filters.company,
			"asset": filters.get("asset"),
			"finance_book": filters.get("finance_book"),
		},
		as_dict=1,
	)

	return get_permitted_assets(asset_details)


def get_permitted_assets(asset_details: list) -> list:
	"""Keep only the assets the user may read."""
	if not asset_details:
		return []

	names = [asset.name for asset in asset_details]
	permitted = set(frappe.get_list("Asset", filters={"name": ["in", names]}, pluck="name"))
	return [asset for asset in asset_details if asset.name in permitted]


def get_assets_for_grouped_by_asset(filters):
	condition = ""
	if filters.get("asset"):
		condition = f" and a.name = '{filters.get('asset')}'"
	finance_book_filter = f" and {get_finance_book_condition(filters)}"
	if filters.get("finance_book"):
		condition += " and exists (select 1 from `tabAsset Depreciation Schedule` ads where ads.asset = a.name and ads.finance_book = %(finance_book)s)"

	# nosemgrep
	return frappe.db.sql(
		f"""
		SELECT results.name as asset,
			   sum(results.accumulated_depreciation_as_on_from_date) as accumulated_depreciation_as_on_from_date,
			   sum(results.depreciation_eliminated_via_reversal) as depreciation_eliminated_via_reversal,
			   sum(results.depreciation_eliminated_during_the_period) as depreciation_eliminated_during_the_period,
			   sum(results.depreciation_amount_during_the_period) as depreciation_amount_during_the_period
		from (SELECT a.name as name,
				   ifnull(sum(case when gle.posting_date < %(from_date)s and (ifnull(a.disposal_date, 0) = 0 or a.disposal_date >= %(from_date)s) then
								   gle.debit - gle.credit
							  else
								   0
							  end), 0) as accumulated_depreciation_as_on_from_date,
				   ifnull(sum(case when gle.posting_date >= %(from_date)s and gle.posting_date <= %(to_date)s
										and (ifnull(a.disposal_date, 0) = 0 or gle.posting_date <= a.disposal_date) then
								   gle.credit
							  else
								   0
							  end), 0) as depreciation_eliminated_via_reversal,
				   ifnull(sum(case when ifnull(a.disposal_date, 0) != 0 and a.disposal_date >= %(from_date)s
										and a.disposal_date <= %(to_date)s and gle.posting_date <= a.disposal_date then
								   gle.debit - gle.credit
							  else
								   0
							  end), 0) as depreciation_eliminated_during_the_period,
				   ifnull(sum(case when gle.posting_date >= %(from_date)s and gle.posting_date <= %(to_date)s
										and (ifnull(a.disposal_date, 0) = 0 or gle.posting_date <= a.disposal_date) then
								   gle.debit
							  else
								   0
							  end), 0) as depreciation_amount_during_the_period
			from `tabGL Entry` gle
			join `tabAsset` a on
				gle.against_voucher = a.name
			join `tabAsset Category Account` aca on
				aca.parent = a.asset_category and aca.company_name = %(company)s
			join `tabCompany` company on
				company.name = %(company)s
			where
				a.docstatus=1
				and a.company=%(company)s
				and a.purchase_date <= %(to_date)s
				and gle.is_cancelled = 0
				and gle.account = ifnull(aca.depreciation_expense_account, company.depreciation_expense_account)
				{finance_book_filter} {condition}
			group by a.name
			union
			SELECT a.name as name,
				   ifnull(sum(case when ifnull(a.disposal_date, 0) != 0 and a.disposal_date < %(from_date)s then
									0
							   else
									a.opening_accumulated_depreciation
							   end), 0) as accumulated_depreciation_as_on_from_date,
				   0 as depreciation_as_on_from_date_credit,
				   ifnull(sum(case when a.disposal_date >= %(from_date)s and a.disposal_date <= %(to_date)s then
								   a.opening_accumulated_depreciation
							  else
								   0
							  end), 0) as depreciation_eliminated_during_the_period,
				   0 as depreciation_amount_during_the_period
			from `tabAsset` a
			where a.docstatus=1 and a.company=%(company)s and a.purchase_date <= %(to_date)s {condition}
			group by a.name) as results
		group by results.name
		""",
		{
			"to_date": filters.to_date,
			"from_date": filters.from_date,
			"company": filters.company,
			"finance_book": filters.get("finance_book", ""),
		},
		as_dict=1,
	)


def get_asset_value_adjustment_map(filters):
	# nosemgrep
	asset_with_value_adjustments = frappe.db.sql(
		f"""
		SELECT
			a.name AS asset,
			{get_value_adjustment_columns()}

		FROM `tabGL Entry` gle
		JOIN `tabAsset` a ON gle.against_voucher = a.name
		JOIN `tabAsset Category Account` aca
			ON aca.parent = a.asset_category
			AND aca.company_name = %(company)s
		WHERE gle.is_cancelled = 0
			AND a.docstatus = 1
			AND a.company = %(company)s
			AND a.purchase_date <= %(to_date)s
			AND gle.account = aca.fixed_asset_account
			AND gle.is_opening = 'No'
			AND {get_finance_book_condition(filters)}
		GROUP BY a.name
	""",
		{"from_date": filters.from_date, "to_date": filters.to_date, "company": filters.company},
		as_dict=1,
	)

	return {row.pop("asset"): row for row in asset_with_value_adjustments}


def get_value_adjustment_columns() -> str:
	"""Fixed asset GL rows other than the disposal entry, summed before the period, till its end and,
	for assets disposed in the period, till its end by how they were disposed."""
	is_adjustment = (
		"gle.voucher_type not in ('Sales Invoice', 'Asset Capitalization')"
		" and gle.voucher_no != ifnull(a.journal_entry_for_scrap, '')"
	)
	held_in_period = "(a.disposal_date is null or a.disposal_date >= %(from_date)s)"
	till_to_date = f"{is_adjustment} and {held_in_period} and gle.posting_date <= %(to_date)s"
	disposed_in_period = "a.disposal_date is not null and a.disposal_date <= %(to_date)s"

	columns = [
		get_adjustment_sum(
			f"{held_in_period} and gle.posting_date < %(from_date)s", "adjustment_before_from_date"
		),
		get_adjustment_sum(till_to_date, "adjustment_till_to_date"),
	]
	columns += [
		get_adjustment_sum(
			f"{till_to_date} and {disposed_in_period} and a.status = '{status}'", f"adjustment_of_{fieldname}"
		)
		for status, fieldname in DISPOSAL_VALUE_FIELDS.items()
	]
	return ",\n".join(columns)


def get_adjustment_sum(condition: str, alias: str) -> str:
	return f"ifnull(sum(case when {condition} then gle.debit - gle.credit else 0 end), 0) as {alias}"


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
			"label": _("Value of New Capitalized Asset"),
			"fieldname": "value_of_capitalized_asset",
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
