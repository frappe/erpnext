# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, getdate, formatdate, cstr, rounded
from frappe.utils.data import get_first_day, get_last_day, add_years, date_diff, now, today, getdate
from erpnext.custom_utils import get_date_diff

def execute(filters=None):
    validate_filters(filters)
    data = get_data(filters)
    columns = get_columns()
    return columns, data

def validate_filters(filters):
    if not filters.fiscal_year:
        frappe.throw(_("Fiscal Year {0} is required").format(filters.fiscal_year))

    fiscal_year = frappe.db.get_value("Fiscal Year", filters.fiscal_year, ["year_start_date", "year_end_date"], as_dict=True)
    if not fiscal_year:
        frappe.throw(_("Fiscal Year {0} does not exist").format(filters.fiscal_year))
    else:
        filters.year_start_date = getdate(fiscal_year.year_start_date)
        filters.year_end_date = getdate(fiscal_year.year_end_date)

    if not filters.from_date:
        filters.from_date = filters.year_start_date

    if not filters.to_date:
        filters.to_date = filters.year_end_date

    filters.from_date = getdate(filters.from_date)
    filters.to_date = getdate(filters.to_date)

    if filters.from_date > filters.to_date:
        frappe.throw(_("From Date cannot be greater than To Date"))

    if (filters.from_date < filters.year_start_date) or (filters.from_date > filters.year_end_date):
        frappe.msgprint(_("From Date should be within the Fiscal Year. Assuming From Date = {0}")\
            .format(formatdate(filters.year_start_date)))

        filters.from_date = filters.year_start_date

    if (filters.to_date < filters.year_start_date) or (filters.to_date > filters.year_end_date):
        frappe.msgprint(_("To Date should be within the Fiscal Year. Assuming To Date = {0}")\
            .format(formatdate(filters.year_end_date)))
        filters.to_date = filters.year_end_date

    if filters.get('asset_category'):
        filters.asset_category = filters.get('asset_category')

    if filters.get('asset_code'):
        filters.asset_code = filters.get('asset_code')

def get_depreciation_details(filters):
    query= """
        SELECT
            ds.parent AS asset,
            SUM(CASE
                WHEN ds.schedule_date < '{from_date}' THEN ds.depreciation_amount
                ELSE 0
            END) AS dep_opening,
            SUM(CASE
                WHEN ds.schedule_date BETWEEN '{from_date}' AND '{to_date}' THEN ds.depreciation_amount
                ELSE 0
            END) AS dep_addition,
            SUM(CASE
                WHEN ds.schedule_date < '{from_date}' THEN ds.income_depreciation_amount
                ELSE 0
            END) AS opening_income,
            SUM(CASE
                WHEN ds.schedule_date BETWEEN '{from_date}' AND '{to_date}' THEN ds.income_depreciation_amount
                ELSE 0
            END) AS depreciation_income_tax
        FROM `tabDepreciation Schedule` as ds
        WHERE ds.schedule_date <= '{to_date}'
        AND (IFNULL(ds.journal_entry,'') != '' OR IFNULL(ds.depreciation_entry,'') != '')
        GROUP BY ds.parent
    """.format(from_date=filters.from_date, to_date=filters.to_date, fiscal_year = filters.fiscal_year)

    query_two= """
        SELECT
            ds.parent AS asset,
            SUM(ds.depreciation_amount) AS dep_total_next_year
        FROM `tabDepreciation Schedule` AS ds
        WHERE YEAR(ds.schedule_date) = '{fiscal_year}' 
        AND (SELECT status FROM `tabAsset` WHERE name = ds.parent) IN ('Submitted','Partially Depreciated')
        GROUP BY ds.parent

    """.format(fiscal_year = str(int(filters.fiscal_year)+1))

    depreciation_details = frappe._dict()
    depreciation_details_two = frappe._dict()
    for row in frappe.db.sql(query, as_dict=True):
        depreciation_details.setdefault(row.asset, row)
    for row in frappe.db.sql(query_two, as_dict=True):
        depreciation_details_two.setdefault(row.asset, row)
    return depreciation_details, depreciation_details_two

def get_data(filters):
    query = """
            SELECT
            a.name, a.asset_name, a.asset_category, a.asset_sub_category,
            a.vehicle_number, a.serial_number, a.old_asset_code,
            a.cost_center, a.purchase_date, a.posting_date as date_of_issue, a.status, a.asset_status, 
            a.disposal_date, a.journal_entry_for_scrap,
            a.custodian as issued_to, a.custodian_name as employee_name,
            a.asset_quantity, a.asset_rate, a.additional_value,
            a.gross_purchase_amount, f.expected_value_after_useful_life,
                        a.opening_accumulated_depreciation, f.value_after_depreciation,
                        a.income_tax_opening_depreciation_amount as iopening,
            a.residual_value, a.remarks,
            (
                (CASE WHEN a.purchase_date < '{from_date}' THEN IFNULL(a.asset_rate,0)*IFNULL(a.asset_quantity,1)
                    ELSE 0 END)
                +
                (
                    IFNULL((SELECT SUM(IFNULL(am.difference_amount,0))
                    FROM `tabAsset Value Adjustment` am
                    WHERE am.asset = a.name
                    AND am.docstatus = 1
                    AND am.date < '{from_date}'
                    ),0)
                ) 
            ) gross_opening,
            (
                (CASE WHEN a.purchase_date BETWEEN '{from_date}' AND '{to_date}' THEN IFNULL(a.asset_rate,0)*IFNULL(a.asset_quantity,1)
                    ELSE 0 END)
                +
                (
                    IFNULL((SELECT SUM(IFNULL(am.difference_amount,0))
                    FROM `tabAsset Value Adjustment` am
                    WHERE am.asset = a.name
                    AND am.docstatus = 1
                    AND am.date BETWEEN '{from_date}' AND '{to_date}'
                    AND am.difference_amount > 0
                    ),0)
                ) 
            ) gross_addition,
            (CASE WHEN a.status in ('Scrapped', 'Sold') AND a.disposal_date BETWEEN '{from_date}' AND '{to_date}'
                THEN IFNULL(a.gross_purchase_amount,0)
                ELSE 0
            END) AS gross_adjustment,
            0 AS dep_opening,
            0 AS dep_addition,
            (CASE WHEN a.status in ('Scrapped', 'Sold') AND a.disposal_date BETWEEN '{from_date}' AND '{to_date}'
                THEN IFNULL(a.gross_purchase_amount,0)-IFNULL(a.value_after_depreciation,0)
                ELSE 0
            END) AS dep_adjustment,
            0 AS opening_income,
            (select 
                       round(total_number_of_depreciations/12,2)
                from `tabAsset Finance Book`
                   where parent = a.asset_category 
                  and asset_sub_category = a.asset_sub_category
                limit 1
                ) as total_number_of_depreciations,
            (select 
                income_depreciation_percent 
            from `tabAsset Finance Book`
            where parent = a.asset_category 
            and asset_sub_category = a.asset_sub_category
            limit 1
            ) as depreciation_percent,
            0 AS depreciation_income_tax
                FROM 
            `tabAsset` AS a
            INNER JOIN `tabAsset Finance Book` AS f ON f.parent = a.name       
        WHERE a.docstatus = 1 
        AND a.purchase_date <= '{to_date}'
        AND (
            a.status not in ('Scrapped', 'Sold')
            OR
            (a.status in ('Scrapped', 'Sold') AND a.disposal_date >= '{from_date}')
        )
        """.format(from_date=filters.from_date, to_date=filters.to_date)
                
    if filters.cost_center:
        query+=" and a.cost_center = \'" + filters.cost_center + "\'"

    if filters.asset_category:
        query+=" and a.asset_category = \'" + filters.asset_category + "\'"

    if filters.asset_code:
        query +=" and a.name in %(asset_code)s "

    asset_data = frappe.db.sql(query, filters, as_dict=True)
    depreciation_details, depreciation_details_two = get_depreciation_details(filters)
    data = []

    if asset_data:
        total_gross_opening = 0
        total_gross_addition = 0
        total_gross_adjustment = 0
        total_gross_total = 0
        total_dep_opening = 0
        total_dep_addition = 0
        total_dep_adjustment = 0
        total_dep_total = 0
        total_dep_total_next_year = 0

        total_actual_dep = 0	
        total_net = 0
        total_opening = 0
        total_adjustment = 0
        total_net_income = 0
        total_income = 0

        for a in asset_data:
            gross_opening  	= flt(a.gross_opening,2)
            gross_addition 	= flt(a.gross_addition,2)
            gross_adjustment= flt(a.gross_adjustment,2)
            gross_total	= gross_opening + gross_addition - gross_adjustment
            dep_opening	= 0
            dep_addition	= 0
            dep_adjustment	= 0
            dep_total	= 0
            dep_total_next_year = 0

            # depreciation entry
            depreciation_entry = depreciation_details.get(a.name)
            depreciation_entry_two = depreciation_details_two.get(a.name)
            if depreciation_entry:
                a.update(depreciation_entry)
            if depreciation_entry_two:
                a.update(depreciation_entry_two)

            dep_opening 	= flt(a.opening_accumulated_depreciation,2) + flt(a.dep_opening,2)
            dep_addition	= flt(a.dep_addition,2)
            dep_adjustment 	= flt(a.dep_adjustment,2) if (dep_opening+dep_addition) else 0
            dep_total_next_year = flt(a.dep_total_next_year) if dep_total_next_year else 0
            dep_total	= dep_opening + dep_addition - dep_adjustment

            net_useful_life = gross_total - dep_total
            net_income_tax = flt(a.gross_purchase_amount) - flt(a.iopening) - flt(a.depreciation_income_tax) - flt(a.opening_income)

            total_gross_opening 	+= gross_opening
            total_gross_addition 	+= gross_addition
            total_gross_adjustment 	+= gross_adjustment
            total_gross_total	+= gross_total

            total_dep_opening	+= dep_opening
            total_dep_addition	+= dep_addition
            total_dep_adjustment	+= dep_adjustment
            total_dep_total_next_year += dep_total_next_year
            total_dep_total		+= dep_total

            total_net+= flt(net_useful_life, 2)
            total_income 	 += flt(a.depreciation_income_tax, 2)
            total_net_income += flt(net_income_tax, 2)
            row = {
                "asset_code": a.name,
                "asset_name": a.asset_name,
                "serial_number": a.serial_number,
                "asset_category": a.asset_category,
                "asset_sub_category": a.asset_sub_category,
                "issued_to": a.issued_to,
                "employee_name": a.employee_name,
                "designation": a.designation,
                "cost_center": a.cost_center,
                "date_of_issue": a.purchase_date,
                "qty": a.asset_quantity,
                "gross_opening": gross_opening,
                "gross_addition": gross_addition,
                "gross_adjustment": gross_adjustment,
                "gross_total": gross_total,
                "dep_opening": dep_opening,
                "dep_addition": dep_addition,
                "dep_adjustment": dep_adjustment,
                "dep_total": dep_total,
                "dep_income_tax": a.depreciation_income_tax,
                "iopening": flt(a.iopening) + flt(a.opening_income),
                "net_useful_life": net_useful_life,
                "net_income_tax": net_income_tax,
                "total_number_of_depreciations": a.total_number_of_depreciations,
                "depreciation_percent": a.depreciation_percent,
                "old_asset_code": a.old_asset_code,
                "vehicle_number": a.vehicle_number,
                "asset_status": a.asset_status,
                "residual_value": a.residual_value,
                "status": a.status,
                "project": a.project,
                "dep_total_next_year": a.dep_total_next_year,
                "remarks": a.remarks
            }
            data.append(row)
        # total row
        row = {
            "gross_opening": total_gross_opening, 
            "gross_addition": total_gross_addition, 
            "gross_adjustment": total_gross_adjustment,
            "gross_total": total_gross_total,
            "dep_opening": total_dep_opening,
            "dep_addition": total_dep_addition,
            "dep_adjustment": total_dep_adjustment,
            "dep_total_next_year": total_dep_total_next_year,
            "dep_total": total_dep_total,
            "net_useful_life": flt(total_net, 2), 
            "net_income_tax": total_net_income, 
            "dep_income_tax": total_income}
        data.append(row)
    return data

def get_depreciation_details(filters):
    query= """
        SELECT
            ds.parent AS asset,
            SUM(CASE
                WHEN ds.schedule_date < '{from_date}' THEN ds.depreciation_amount
                ELSE 0
            END) AS dep_opening,
            SUM(CASE
                WHEN ds.schedule_date BETWEEN '{from_date}' AND '{to_date}' THEN ds.depreciation_amount
                ELSE 0
            END) AS dep_addition,
            SUM(CASE
                WHEN ds.schedule_date < '{from_date}' THEN ds.income_depreciation_amount
                ELSE 0
            END) AS opening_income,
            SUM(CASE
                WHEN ds.schedule_date BETWEEN '{from_date}' AND '{to_date}' THEN ds.income_depreciation_amount
                ELSE 0
            END) AS depreciation_income_tax
        FROM `tabDepreciation Schedule` as ds
        WHERE ds.schedule_date <= '{to_date}'
        AND (IFNULL(ds.journal_entry,'') != '' OR IFNULL(ds.depreciation_entry,'') != '')
        GROUP BY ds.parent
    """.format(from_date=filters.from_date, to_date=filters.to_date, fiscal_year = filters.fiscal_year)

    query_two= """
        SELECT
            ds.parent AS asset,
            SUM(ds.depreciation_amount) AS dep_total_next_year
        FROM `tabDepreciation Schedule` AS ds
        WHERE YEAR(ds.schedule_date) = '{fiscal_year}' AND (SELECT status FROM `tabAsset` WHERE name = ds.parent) IN ('Submitted','Partially Depreciated')
        GROUP BY ds.parent
    """.format(fiscal_year = str(int(filters.fiscal_year)+1))

    depreciation_details = frappe._dict()
    depreciation_details_two = frappe._dict()
    for row in frappe.db.sql(query, as_dict=True):
        depreciation_details.setdefault(row.asset, row)
    for row in frappe.db.sql(query_two, as_dict=True):
        depreciation_details_two.setdefault(row.asset, row)
    return depreciation_details, depreciation_details_two

def get_columns():
    return [
        {
            "fieldname": "asset_code",
            "label": _("Asset Code"),
            "fieldtype": "Link",
            "options": "Asset",
            "width": 140
        },
        {
            "fieldname": "asset_name",
            "label": _("Asset Name"),
            "fieldtype": "Data",
            "width": 200
        },
        {
            "fieldname": "serial_number",
            "label": _("Serial Number"),
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "asset_category",
            "label": _("Asset Category"),
            "fieldtype": "Link",
            "options":"Asset Category",
            "width": 150
        },
        {
            "fieldname": "asset_sub_category",
            "label": _("Sub Category"),
            "fieldtype": "Link",
            "options":"Item Sub Group",
            "width": 150
        },
        {
            "fieldname": "issued_to",
            "label": _("Issued To"),
            "fieldtype": "Data",
            "width": 100
        },
         {
            "fieldname": "employee_name",
            "label": _("Employee Name"),
            "fieldtype": "Data",
            "width": 150
        },
        {
            "fieldname": "cost_center",
            "label": _("Cost Center"),
            "fieldtype": "Link",
            "options": "Cost Center",
            "width": 130
        },
        {
            "fieldname": "date_of_issue",
            "label": _("Dep Start Date"),
            "fieldtype": "Date",
            "width": 120
        },
        {
            "fieldname": "total_number_of_depreciations",
            "label": _("Useful Life(Years)"),
            "fieldtype": "Float",
            "width": 100
        },
        {
            "fieldname": "depreciation_percent",
            "label": _("Income Dep. Percent"),
            "fieldtype": "Data",
            "width": 120	
        },
        {
            "fieldname": "qty",
            "label": _("Quantity"),
            "fieldtype": "Data",
            "width": 100
        },
        {
            "fieldname": "gross_opening",
            "label": _("Gross Opening"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "gross_addition",
            "label": _("Gross Addition"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "gross_adjustment",
            "label": _("Gross Adjustments"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "gross_total",
            "label": _("Gross Total"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "dep_opening",
            "label": _("Accumulated Dep."),
            "fieldtype": "Currency",
            "width": 120
        },
     
        {
            "fieldname": "dep_addition",
            "label": _("Dep. During the Year"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "dep_adjustment",
            "label": _("Dep. Adjustment During the Year"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "dep_total",
            "label": _("Dep. Total"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "net_useful_life",
            "label": _("Net Book Value"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "iopening",
            "label": _("Income Open. Dep."),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "dep_income_tax",
            "label": _("Income Tax"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "net_income_tax",
            "label": _("Net Income Tax"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "old_asset_code",
            "label": _("Old Asset Code"),
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "vehicle_number",
            "label": _("Vehicle Number"),
            "fieldtype": "Link",
            "options": "Vehicle",
            "width": 120
        },
        {
            "fieldname": "asset_status",
            "label": _("Asset Status"),
            "fieldtype": "data",
            "width": 120
        },
        {
            "fieldname": "residual_value",
            "label": _("Residual Value"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "status",
            "label": _("Status"),
            "fieldtype": "data",
            "width": 120
        },
        {
            "fieldname": "remarks",
            "label": _("Remarks"),
            "fieldtype": "data",
            "width": 120
        },
    ]

