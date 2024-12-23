# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import add_days, flt, formatdate


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

	for asset_category in asset_categories:
		row = frappe._dict()
		row.update(asset_category)

		row.value_as_on_to_date = (
			flt(row.value_as_on_from_date)
			+ flt(row.value_of_new_purchase)
			- flt(row.value_of_sold_asset)
			- flt(row.value_of_scrapped_asset)
			- flt(row.value_of_capitalized_asset)
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


def get_asset_details_for_grouped_by_category(filters):
	condition = ""
	if filters.get("asset"):
		condition += " and a.name = %(asset)s"
	if filters.get("finance_book"):
		condition += " and exists (select 1 from `tabAsset Depreciation Schedule` ads where ads.asset = a.name and ads.finance_book = %(finance_book)s)"

	# nosemgrep
	return frappe.db.sql(
		f"""
		SELECT a.name,
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


def get_group_by_asset_data(filters):
	data = []

	asset_details = get_asset_details_for_grouped_by_category(filters)
	assets = get_assets_for_grouped_by_asset(filters)

	for asset_detail in asset_details:
		row = frappe._dict()
		row.update(asset_detail)

		row.value_as_on_to_date = (
			flt(row.value_as_on_from_date)
			+ flt(row.value_of_new_purchase)
			- flt(row.value_of_sold_asset)
			- flt(row.value_of_scrapped_asset)
			- flt(row.value_of_capitalized_asset)
		)

		row.update(next(asset for asset in assets if asset["asset"] == asset_detail.get("name", "")))

		row.accumulated_depreciation_as_on_to_date = (
			flt(row.accumulated_depreciation_as_on_from_date)
			+ flt(row.depreciation_amount_during_the_period)
			- flt(row.depreciation_eliminated_during_the_period)
		)

		row.net_asset_value_as_on_from_date = flt(row.value_as_on_from_date) - flt(
			row.accumulated_depreciation_as_on_from_date
		)

		row.net_asset_value_as_on_to_date = flt(row.value_as_on_to_date) - flt(
			row.accumulated_depreciation_as_on_to_date
		)

		data.append(row)

	return data


def get_assets_for_grouped_by_category(filters):
	condition = ""
	if filters.get("asset_category"):
		condition = f" and a.asset_category = '{filters.get('asset_category')}'"
	finance_book_filter = ""
	if filters.get("finance_book"):
		finance_book_filter += " and ifnull(gle.finance_book, '')=%(finance_book)s"
		condition += " and exists (select 1 from `tabAsset Depreciation Schedule` ads where ads.asset = a.name and ads.finance_book = %(finance_book)s)"

	# nosemgrep
	return frappe.db.sql(
		f"""
		SELECT results.asset_category,
			   sum(results.accumulated_depreciation_as_on_from_date) as accumulated_depreciation_as_on_from_date,
			   sum(results.depreciation_eliminated_during_the_period) as depreciation_eliminated_during_the_period,
			   sum(results.depreciation_amount_during_the_period) as depreciation_amount_during_the_period
		from (SELECT a.asset_category,
				   ifnull(sum(case when gle.posting_date < %(from_date)s and (ifnull(a.disposal_date, 0) = 0 or a.disposal_date >= %(from_date)s) then
								   gle.debit
							  else
								   0
							  end), 0) as accumulated_depreciation_as_on_from_date,
				   ifnull(sum(case when ifnull(a.disposal_date, 0) != 0 and a.disposal_date >= %(from_date)s
										and a.disposal_date <= %(to_date)s and gle.posting_date <= a.disposal_date then
								   gle.debit
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
				and gle.debit != 0
				and gle.is_cancelled = 0
				and gle.account = ifnull(aca.depreciation_expense_account, company.depreciation_expense_account)
				{condition} {finance_book_filter}
			group by a.asset_category
			union
			SELECT a.asset_category,
				   ifnull(sum(case when ifnull(a.disposal_date, 0) != 0 and (a.disposal_date < %(from_date)s or a.disposal_date > %(to_date)s) then
									0
							   else
									a.opening_accumulated_depreciation
							   end), 0) as accumulated_depreciation_as_on_from_date,
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


def get_assets_for_grouped_by_asset(filters):
	condition = ""
	if filters.get("asset"):
		condition = f" and a.name = '{filters.get('asset')}'"
	finance_book_filter = ""
	if filters.get("finance_book"):
		finance_book_filter += " and ifnull(gle.finance_book, '')=%(finance_book)s"
		condition += " and exists (select 1 from `tabAsset Depreciation Schedule` ads where ads.asset = a.name and ads.finance_book = %(finance_book)s)"

	# nosemgrep
	return frappe.db.sql(
		f"""
		SELECT results.name as asset,
			   sum(results.accumulated_depreciation_as_on_from_date) as accumulated_depreciation_as_on_from_date,
			   sum(results.depreciation_eliminated_during_the_period) as depreciation_eliminated_during_the_period,
			   sum(results.depreciation_amount_during_the_period) as depreciation_amount_during_the_period
		from (SELECT a.name as name,
				   ifnull(sum(case when gle.posting_date < %(from_date)s and (ifnull(a.disposal_date, 0) = 0 or a.disposal_date >= %(from_date)s) then
								   gle.debit
							  else
								   0
							  end), 0) as accumulated_depreciation_as_on_from_date,
				   ifnull(sum(case when ifnull(a.disposal_date, 0) != 0 and a.disposal_date >= %(from_date)s
										and a.disposal_date <= %(to_date)s and gle.posting_date <= a.disposal_date then
								   gle.debit
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
				and gle.debit != 0
				and gle.is_cancelled = 0
				and gle.account = ifnull(aca.depreciation_expense_account, company.depreciation_expense_account)
				{finance_book_filter} {condition}
			group by a.name
			union
			SELECT a.name as name,
				   ifnull(sum(case when ifnull(a.disposal_date, 0) != 0 and (a.disposal_date < %(from_date)s or a.disposal_date > %(to_date)s) then
									0
							   else
									a.opening_accumulated_depreciation
							   end), 0) as accumulated_depreciation_as_on_from_date,
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
