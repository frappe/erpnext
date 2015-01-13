# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from __future__ import division
import frappe
from datetime import date, timedelta
from datetime import datetime
from erpnext.accounts.utils import get_fiscal_year
from frappe.utils import flt

def getDateDiffDays(d1, d2):
    return abs((d2 - d1).days)


def execute(filters=None):
    data = []
    columns = []
    finyrfrom, finyrto = get_fiscal_year(fiscal_year = filters["fiscal_year"])[1:]
    day_before_start = finyrfrom - timedelta (days=1)
    TOTAL_DAYS_IN_YEAR = 365

    ps = frappe.db.sql("""select led.*,ifnull((select sum(sale.asset_purchase_cost) from `tabFixed Asset Sale` sale where sale.fixed_asset_account=led.fixed_asset_name and sale.docstatus=1  and sale.posting_date>=%s and sale.posting_date<=%s),0) as total_sale_value
           from `tabFixed Asset Account` led where is_sold=false or (is_sold=true and (select count(*) from `tabFixed Asset Sale` sale where sale.fixed_asset_account=led.fixed_asset_name and docstatus=1 and sale.posting_date>=%s and sale.posting_date<=%s)>0)""", (finyrfrom,finyrto,finyrfrom,finyrto), as_dict=True)

    for assets in ps:
        fixed_asset_name = assets.fixed_asset_name
        fixed_asset_account = assets.fixed_asset_account
        rateofdepr = abs(assets.depreciation_rate)
        purchase_date = datetime.strptime(assets.purchase_date, "%Y-%m-%d").date()

        global deprtilllastyr # Depreciation provided till close of last fiscal Yr.
        deprtilllastyr = 0
        for accdepr in frappe.get_doc("Fixed Asset Account", fixed_asset_name).depreciation:
           if get_fiscal_year(fiscal_year = accdepr.fiscal_year) == get_fiscal_year(date = day_before_start):
               deprtilllastyr = accdepr.total_accumulated_depreciation

        global opening_balance # Opening Cost of Asset for the Year
        opening_balance = 0
        if deprtilllastyr > 0:
        	opening_balance = abs(assets.gross_purchase_value)

        global totalpurchase # Purchases in this Fiscal Yr
        totalpurchase = 0
        if purchase_date>=finyrfrom and purchase_date<=finyrto:
            totalpurchase = assets.gross_purchase_value

        totalsales = assets.total_sale_value

        global depronopening # Depreciation to be Provided in on the Opening Cost for this Fiscal Yr.
        depronopening = float(0)

        if totalsales == 0:
            depronopening = float(depronopening + (((opening_balance - deprtilllastyr) * rateofdepr / 100)))
        elif totalsales >= opening_balance:
            sales_sql = frappe.db.sql("""select * from `tabFixed Asset Sale` where docstatus=1 and fixed_asset_account=%s and posting_date>=%s and posting_date<=%s""", (fixed_asset_name, finyrfrom, finyrto), as_dict=True)
            factor = 1
            if opening_balance > 0:
                factor = float(deprtilllastyr / opening_balance)

            for sales in sales_sql:
                saleamount = float(sales.asset_purchase_cost)
                saledate = datetime.strptime(sales.posting_date, "%Y-%m-%d").date()
                days = getDateDiffDays(finyrfrom, saledate)
                depronopening = depronopening + (((saleamount - (saleamount * factor)) * rateofdepr / 100) * (days / TOTAL_DAYS_IN_YEAR))

        global depronpurchases # Depreciation provided on Purchase in the Current FY
        depronpurchases = float(0)
        if purchase_date>=finyrfrom and purchase_date<=finyrto:
            days = getDateDiffDays(purchase_date, finyrto)
            depronpurchases = depronpurchases + ((assets.gross_purchase_value * rateofdepr / 100) * (days / TOTAL_DAYS_IN_YEAR))

        global deprwrittenback
        deprwrittenback = 0
        if totalsales > 0:
            deprwrittenback = depronopening + deprtilllastyr

        row = [fixed_asset_name,
               fixed_asset_account,
               rateofdepr,
               flt(opening_balance,2),
               flt(totalpurchase,2),
               flt(totalsales,2),
               flt(((opening_balance + totalpurchase) - totalsales),2),
               flt(deprtilllastyr,2),
               flt(depronopening,2),
               flt(depronpurchases,2),
               flt(depronopening+depronpurchases,2),
               flt(deprwrittenback,2),
               flt(((deprtilllastyr + depronopening + depronpurchases) - deprwrittenback),2)]

        data.append(row)

    columns = ["FIXED ASSET NAME",
               "FIXED ASSET ACCOUNT",
               "RATE OF DEPRECIATION",
               "COST AS ON "+str(finyrfrom),
               "PURCHASES",
               "SALES",
               "CLOSING COST "+str(finyrto),
               "DEPRECIATION AS ON "+str(finyrfrom),
               "DEPRECIATION PROVIDED ON OPENING FOR CUR YR",
               "DEPRECIATION PROVIDED ON PURCHASE FOR CUR YR",
               "TOTAL DEPRECIATION FOR CUR YR",
               "WRITTEN_BACK",
               "TOTAL ACCUMULATED DEPRECIATION AS ON "+str(finyrto)]

    return columns, data

