# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import (flt, getdate, get_first_day, get_last_day, add_months, add_days, formatdate)
from erpnext.accounts.report.financial_statements import (
	get_data,
	get_filtered_list_for_consolidated_report,
	get_period_list,
)
def execute(filters=None):
    if filters.periodicity == 'Daily':
        period_list = ""
    else: 
        if filters.periodicity == 'Yearly':
            from_fiscal_year = filters.fiscal_year,
            to_fiscal_year   = filters.to_fiscal_year
        else:
            from_fiscal_year = filters.fiscal_year,
            to_fiscal_year   = filters.fiscal_year
        period_list = get_period_list(
					from_fiscal_year    = from_fiscal_year,
					to_fiscal_year      = to_fiscal_year,
					period_start_date   = getdate(str(filters.fiscal_year + '-01-01')),
					period_end_date     = getdate(str(filters.fiscal_year + '-12-31')),
					filter_based_on     = filters.filter_based_on,
					periodicity         = filters.periodicity,
					company             =filters.company)
    
    columns = get_columns(filters, period_list)
    data = get_data(filters, period_list)
    return columns, data

def get_data(filters, period_list):
    data= []
    conditions = get_conditions(filters)

    if filters.periodicity == 'Daily':
        query1 = frappe.db.sql("""
                    SELECT  
                        ppi.item_code, ppi.item_name
                    FROM `tabProduction` p, `tabProduction Product Item` ppi
                    WHERE ppi.parent = p.name AND p.docstatus = 1 GROUP BY ppi.item_code
                """, as_dict=1)

        for i in query1:
            row = {}
            total = 0
            flag = 0
            
            for cur_date in get_dates(filters):
                query = frappe.db.sql("""
                    SELECT 
                        ppi.item_code, 
                        sum(ppi.qty) as qty
                    FROM `tabProduction` p, `tabProduction Product Item` ppi 
                    WHERE ppi.parent = p.name AND p.docstatus = 1
                    AND p.posting_date = '{from_date}' {cond}
                    GROUP BY ppi.item_code;
                """.format(from_date=cur_date, cond=conditions), as_dict=True)

                for q in query:
                    if q.item_code == i.item_code:
                        total += q.qty
                        row["date_" + str(formatdate(cur_date, 'yyyyMMdd'))] = q.qty
                        row['total'] = total
                        flag = 1
            
            if flag == 1:
                row['item_code'] = '<b>' + i.item_code + '</b>'
                row['item_name'] = '<b>' + i.item_name + '</b>'
                data.append(row)
    else:
        query1 = frappe.db.sql(
                """
                    SELECT  
                        ppi.item_code, ppi.item_name
                    FROM `tabProduction` p, `tabProduction Product Item` ppi
                    WHERE ppi.parent = p.name AND p.docstatus = 1 GROUP BY ppi.item_code
                """, as_dict=1)

        for i in query1:
            row = {}
            total = 0
            flag = 0
            
            for d in period_list:
                query = frappe.db.sql("""
                    SELECT 
                        ppi.item_code, 
                        sum(ppi.qty) as qty
                    FROM `tabProduction` p, `tabProduction Product Item` ppi 
                    WHERE ppi.parent = p.name AND p.docstatus = 1
                    AND p.posting_date BETWEEN '{from_date}' AND '{to_date}' {cond}
                    GROUP BY ppi.item_code;
                """.format(from_date=d.from_date, to_date=d.to_date, cond=conditions), as_dict=True)

                for q in query:
                    if q.item_code == i.item_code:
                        total += q.qty
                        row[d.key] = q.qty
                        row['total'] = total
                        flag = 1
            
            if flag == 1:
                row['item_code'] = '<b>' + i.item_code + '</b>'
                row['item_name'] = '<b>' + i.item_name + '</b>'
                data.append(row)
    return data

def get_columns(filters , period_list):
    columns = [
        {
            "fieldname": "item_code",
            "label": _("Material Code"),
            "fieldtype": "Link",
            "options": "Item",
            "width": 80
        },
        {
            "fieldname": "item_name",
            "label": _("Material Name"),
            "fieldtype": "Data",
            "width": 200
        }
    ]

    if filters.periodicity == 'Daily':
        if filters.from_date and filters.to_date:
            if getdate(filters.from_date) > getdate(filters.to_date):
                frappe.throw("From Date should not be before To Date")

            for cur_date in get_dates(filters):
                columns.append({
                    "fieldname": "date_" + str(formatdate(cur_date, 'yyyyMMdd')),
                    "label": str(formatdate(cur_date, 'dd/MM/yyyy')),
                    "fieldtype": "Float"
                })
    else:
        for period in period_list:
            columns.append({
                "fieldname": period.key,
                "label": period.label,
                "fieldtype": "Data",
                "width": 120
            })

    columns.append({
        "fieldname": "total",
        "label": _("Grand Total"),
        "fieldtype": "Float",
        "width": 120
    })
    return columns

def get_dates(filters):
    date_list = []
    current_date = getdate(filters.from_date)
    while True:
        date_list.append(current_date)
        current_date = add_days(current_date, 1)
        if current_date > getdate(filters.to_date):
            break
    return date_list

def get_conditions(filters):
    conditions = ""
    if filters.get("cost_center"):
        conditions += " and p.cost_center = '{}'".format(filters.cost_center)
    if filters.get("branch"):
        conditions += " and p.branch = '{}'".format(filters.branch)
    if filters.get("warehouse"):
        conditions += " and p.warehouse = '{}'".format(filters.warehouse)
    if filters.get("to_warehouse"):
        conditions += " and p.to_warehouse = '{}'".format(filters.to_warehouse)
    if filters.get("location"):
        conditions += " and p.location = '{}'".format(filters.location)
    return conditions

