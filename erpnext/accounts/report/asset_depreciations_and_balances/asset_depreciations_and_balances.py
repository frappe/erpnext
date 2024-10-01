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
		# row.asset_category = asset_category
		row.update(asset_category)

		row.cost_as_on_to_date = (
			flt(row.cost_as_on_from_date)
			+ flt(row.cost_of_new_purchase)
			- flt(row.cost_of_sold_asset)
			- flt(row.cost_of_scrapped_asset)
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

		row.net_asset_value_as_on_from_date = flt(row.cost_as_on_from_date) - flt(
			row.accumulated_depreciation_as_on_from_date
		)

		row.net_asset_value_as_on_to_date = flt(row.cost_as_on_to_date) - flt(
			row.accumulated_depreciation_as_on_to_date
		)

		data.append(row)

	return data


def get_asset_categories_for_grouped_by_category(filters):
	condition = ""
	if filters.get("asset_category"):
		condition += " and asset_category = %(asset_category)s"
	if filters.get("finance_book"):
		condition += " and exists (select 1 from `tabAsset Depreciation Schedule` ads where ads.asset = a.name and ads.finance_book = %(finance_book)s)"

	# nosemgrep
	return frappe.db.sql(
    f"""
    SELECT a.asset_category,
           IFNULL(SUM(CASE 
                        WHEN a.purchase_date < %(from_date)s THEN
                            CASE 
                                WHEN a.disposal_date IS NULL OR a.disposal_date >= %(from_date)s THEN
                                    a.gross_purchase_amount
                                ELSE
                                    0
                            END
                        ELSE
                            0
                    END), 0) AS cost_as_on_from_date,
           IFNULL(SUM(CASE 
                        WHEN a.purchase_date >= %(from_date)s THEN
                            a.gross_purchase_amount
                        ELSE
                            0
                    END), 0) AS cost_of_new_purchase,
           IFNULL(SUM(CASE 
                        WHEN a.disposal_date IS NOT NULL 
                             AND a.disposal_date >= %(from_date)s 
                             AND a.disposal_date <= %(to_date)s THEN
                            CASE 
                                WHEN a.status = 'Sold' THEN
                                    a.gross_purchase_amount
                                ELSE
                                    0
                            END
                        ELSE
                            0
                    END), 0) AS cost_of_sold_asset,
           IFNULL(SUM(CASE 
                        WHEN a.disposal_date IS NOT NULL 
                             AND a.disposal_date >= %(from_date)s 
                             AND a.disposal_date <= %(to_date)s THEN
                            CASE 
                                WHEN a.status = 'Scrapped' THEN
                                    a.gross_purchase_amount
                                ELSE
                                    0
                            END
                        ELSE
                            0
                    END), 0) AS cost_of_scrapped_asset
    FROM `tabAsset` a
    WHERE docstatus = 1 
      AND company = %(company)s 
      AND purchase_date <= %(to_date)s {condition}
      AND NOT EXISTS (SELECT name 
                      FROM `tabAsset Capitalization Asset Item` 
                      WHERE asset = a.name)
    GROUP BY a.asset_category
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
		condition += " and name = %(asset)s"
	if filters.get("finance_book"):
		condition += " and exists (select 1 from `tabAsset Depreciation Schedule` ads where ads.asset = `tabAsset`.name and ads.finance_book = %(finance_book)s)"

	# nosemgrep
	return frappe.db.sql(
		f"""
		SELECT name,
			IFNULL(SUM(CASE 
							WHEN purchase_date < %(from_date)s THEN
								CASE 
									WHEN disposal_date IS NULL OR disposal_date >= %(from_date)s THEN
										gross_purchase_amount
									ELSE
										0
								END
							ELSE
								0
						END), 0) AS cost_as_on_from_date,
			IFNULL(SUM(CASE 
							WHEN purchase_date >= %(from_date)s THEN
								gross_purchase_amount
							ELSE
								0
						END), 0) AS cost_of_new_purchase,
			IFNULL(SUM(CASE 
							WHEN disposal_date IS NOT NULL
								AND disposal_date >= %(from_date)s
								AND disposal_date <= %(to_date)s THEN
								CASE 
									WHEN status = 'Sold' THEN
										gross_purchase_amount
									ELSE
										0
								END
							ELSE
								0
						END), 0) AS cost_of_sold_asset,
			IFNULL(SUM(CASE 
							WHEN disposal_date IS NOT NULL
								AND disposal_date >= %(from_date)s
								AND disposal_date <= %(to_date)s THEN
								CASE 
									WHEN status = 'Scrapped' THEN
										gross_purchase_amount
									ELSE
										0
								END
							ELSE
								0
						END), 0) AS cost_of_scrapped_asset
		FROM `tabAsset`
		WHERE docstatus=1 
		AND company=%(company)s 
		AND purchase_date <= %(to_date)s {condition}
		GROUP BY name
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
		# row.asset_category = asset_category
		row.update(asset_detail)

		row.cost_as_on_to_date = (
			flt(row.cost_as_on_from_date)
			+ flt(row.cost_of_new_purchase)
			- flt(row.cost_of_sold_asset)
			- flt(row.cost_of_scrapped_asset)
		)

		row.update(next(asset for asset in assets if asset["asset"] == asset_detail.get("name", "")))

		row.accumulated_depreciation_as_on_to_date = (
			flt(row.accumulated_depreciation_as_on_from_date)
			+ flt(row.depreciation_amount_during_the_period)
			- flt(row.depreciation_eliminated_during_the_period)
		)

		row.net_asset_value_as_on_from_date = flt(row.cost_as_on_from_date) - flt(
			row.accumulated_depreciation_as_on_from_date
		)

		row.net_asset_value_as_on_to_date = flt(row.cost_as_on_to_date) - flt(
			row.accumulated_depreciation_as_on_to_date
		)

		data.append(row)

	return data


def get_assets_for_grouped_by_category(filters):
	condition = ""
	if filters.get("asset_category"):
		condition = " and a.asset_category = '{}'".format(filters.get("asset_category"))
	return frappe.db.sql(
    """
    SELECT results.asset_category,
           SUM(results.accumulated_depreciation_as_on_from_date) AS accumulated_depreciation_as_on_from_date,
           SUM(results.depreciation_eliminated_during_the_period) AS depreciation_eliminated_during_the_period,
           SUM(results.depreciation_amount_during_the_period) AS depreciation_amount_during_the_period
    FROM (
        SELECT a.asset_category,
               IFNULL(SUM(CASE 
                            WHEN gle.posting_date < %(from_date)s 
                                 AND (a.disposal_date IS NULL OR a.disposal_date >= %(from_date)s) THEN
                                gle.debit
                            ELSE
                                0
                        END), 0) AS accumulated_depreciation_as_on_from_date,
               IFNULL(SUM(CASE 
                            WHEN a.disposal_date IS NOT NULL 
                                 AND a.disposal_date >= %(from_date)s 
                                 AND a.disposal_date <= %(to_date)s 
                                 AND gle.posting_date <= a.disposal_date THEN
                                gle.debit
                            ELSE
                                0
                        END), 0) AS depreciation_eliminated_during_the_period,
               IFNULL(SUM(CASE 
                            WHEN gle.posting_date >= %(from_date)s 
                                 AND gle.posting_date <= %(to_date)s 
                                 AND (a.disposal_date IS NULL OR gle.posting_date <= a.disposal_date) THEN
                                gle.debit
                            ELSE
                                0
                        END), 0) AS depreciation_amount_during_the_period
        FROM `tabGL Entry` gle
        JOIN `tabAsset` a ON gle.against_voucher = a.name
        JOIN `tabAsset Category Account` aca ON 
            aca.parent = a.asset_category AND aca.company_name = %(company)s
        JOIN `tabCompany` company ON 
            company.name = %(company)s
        WHERE a.docstatus = 1 
          AND a.company = %(company)s 
          AND a.purchase_date <= %(to_date)s 
          AND gle.debit != 0 
          AND gle.is_cancelled = 0 
          AND gle.account = IFNULL(aca.depreciation_expense_account, company.depreciation_expense_account) 
          {0}
        GROUP BY a.asset_category
        
        UNION
        
        SELECT a.asset_category,
               IFNULL(SUM(CASE 
                            WHEN a.disposal_date IS NOT NULL 
                                 AND (a.disposal_date < %(from_date)s OR a.disposal_date > %(to_date)s) THEN
                                0
                            ELSE
                                a.opening_accumulated_depreciation
                        END), 0) AS accumulated_depreciation_as_on_from_date,
               IFNULL(SUM(CASE 
                            WHEN a.disposal_date >= %(from_date)s 
                                 AND a.disposal_date <= %(to_date)s THEN
                                a.opening_accumulated_depreciation
                            ELSE
                                0
                        END), 0) AS depreciation_eliminated_during_the_period,
               0 AS depreciation_amount_during_the_period
        FROM `tabAsset` a
        WHERE a.docstatus = 1 
          AND a.company = %(company)s 
          AND a.purchase_date <= %(to_date)s 
          {0}
        GROUP BY a.asset_category
    ) AS results
    GROUP BY results.asset_category
    """.format(condition),
    {
        "to_date": filters.to_date,
        "from_date": filters.from_date,
        "company": filters.company,
    },
    as_dict=1,
)


def get_assets_for_grouped_by_asset(filters):
	condition = ""
	if filters.get("asset"):
		condition = " and a.name = '{}'".format(filters.get("asset"))
	return frappe.db.sql(
		f"""
		SELECT results.name as asset,
			SUM(results.accumulated_depreciation_as_on_from_date) AS accumulated_depreciation_as_on_from_date,
			SUM(results.depreciation_eliminated_during_the_period) AS depreciation_eliminated_during_the_period,
			SUM(results.depreciation_amount_during_the_period) AS depreciation_amount_during_the_period
		FROM (
			SELECT a.name AS name,
				IFNULL(SUM(CASE 
					WHEN gle.posting_date < %(from_date)s 
							AND (a.disposal_date IS NULL OR a.disposal_date >= %(from_date)s) THEN gle.debit
					ELSE 0
				END), 0) AS accumulated_depreciation_as_on_from_date,
				
				IFNULL(SUM(CASE 
					WHEN a.disposal_date IS NOT NULL 
							AND a.disposal_date >= %(from_date)s 
							AND a.disposal_date <= %(to_date)s 
							AND gle.posting_date <= a.disposal_date THEN gle.debit
					ELSE 0
				END), 0) AS depreciation_eliminated_during_the_period,
				
				IFNULL(SUM(CASE 
					WHEN gle.posting_date >= %(from_date)s 
							AND gle.posting_date <= %(to_date)s 
							AND (a.disposal_date IS NULL OR gle.posting_date <= a.disposal_date) THEN gle.debit
					ELSE 0
				END), 0) AS depreciation_amount_during_the_period
				
			FROM `tabGL Entry` gle
			JOIN `tabAsset` a ON gle.against_voucher = a.name
			JOIN `tabAsset Category Account` aca ON aca.parent = a.asset_category 
				AND aca.company_name = %(company)s
			JOIN `tabCompany` company ON company.name = %(company)s
			WHERE a.docstatus = 1 
			AND a.company = %(company)s 
			AND a.purchase_date <= %(to_date)s 
			AND gle.debit != 0 
			AND gle.is_cancelled = 0 
			AND gle.account = IFNULL(aca.depreciation_expense_account, company.depreciation_expense_account) 
			{condition}
			GROUP BY a.name
			
			UNION
			
			SELECT a.name AS name,
				IFNULL(SUM(CASE 
					WHEN a.disposal_date IS NOT NULL 
							AND (a.disposal_date < %(from_date)s OR a.disposal_date > %(to_date)s) THEN 0
					ELSE a.opening_accumulated_depreciation
				END), 0) AS accumulated_depreciation_as_on_from_date,
				
				IFNULL(SUM(CASE 
					WHEN a.disposal_date >= %(from_date)s 
							AND a.disposal_date <= %(to_date)s THEN a.opening_accumulated_depreciation
					ELSE 0
				END), 0) AS depreciation_eliminated_during_the_period,
				
				0 AS depreciation_amount_during_the_period
				
			FROM `tabAsset` a
			WHERE a.docstatus = 1 
			AND a.company = %(company)s 
			AND a.purchase_date <= %(to_date)s 
			{condition}
			GROUP BY a.name
		) AS results
		GROUP BY results.name
		""",
		{
			"to_date": filters.to_date,
			"from_date": filters.from_date,
			"company": filters.company,
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
			"label": _("Cost as on") + " " + formatdate(filters.day_before_from_date),
			"fieldname": "cost_as_on_from_date",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _("Cost of New Purchase"),
			"fieldname": "cost_of_new_purchase",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _("Cost of Sold Asset"),
			"fieldname": "cost_of_sold_asset",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _("Cost of Scrapped Asset"),
			"fieldname": "cost_of_scrapped_asset",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _("Cost as on") + " " + formatdate(filters.to_date),
			"fieldname": "cost_as_on_to_date",
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
