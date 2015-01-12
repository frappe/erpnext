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

    ps = frappe.db.sql("""select led.*,ifnull((select sum(pur.gross_purchase_value) from `tabFixed Asset Account` pur where pur.fixed_asset_name=led.fixed_asset_name and pur.purchase_date>=%s and pur.purchase_date<=%s),0) as total_pur_value,
           ifnull((select sum(sale.asset_purchase_cost) from `tabFixed Asset Sale` sale where sale.fixed_asset_account=led.fixed_asset_name and sale.docstatus=1  and sale.posting_date>=%s and sale.posting_date<=%s),0) as total_sale_value
           from `tabFixed Asset Account` led where is_sold=false or (is_sold=true and (select count(*) from `tabFixed Asset Sale` sale where sale.fixed_asset_account=led.fixed_asset_name and docstatus=1 and sale.posting_date>=%s and sale.posting_date<=%s)>0)""", (finyrfrom,finyrto,finyrfrom,finyrto,finyrfrom,finyrto), as_dict=True)

    for assets in ps:
        fixed_asset_name = assets.fixed_asset_name
        fixed_asset_account = assets.fixed_asset_account
        global deprtilllastyr
        deprtilllastyr = 0
        for accdepr in frappe.get_doc("Fixed Asset Account", fixed_asset_name).depreciation:
           if get_fiscal_year(fiscal_year = accdepr.fiscal_year) == get_fiscal_year(date = day_before_start):
               deprtilllastyr = accdepr.total_accumulated_depreciation
        global opening_balance
        opening_balance = 0
        if deprtilllastyr > 0:
        	opening_balance = abs(assets.gross_purchase_value)
        rateofdepr = abs(assets.depreciation_rate)
        totalpurchase = assets.total_pur_value
        totalsales = assets.total_sale_value

        global depronopening
        depronopening = float(0)

        if totalsales == 0:
            depronopening = float(depronopening + (((opening_balance - deprtilllastyr) * rateofdepr / 100)))
        elif totalsales >= opening_balance:
            sales_sql = frappe.db.sql("""select * from `tabFixed Asset Sale` where docstatus=1 and fixed_asset_account=%s and posting_date>=%s and posting_date<=%s""", (fixed_asset_name, finyrfrom, finyrto), as_dict=True)
            value = totalsales
            factor = 1
            if opening_balance > 0:
                factor = float(deprtilllastyr / opening_balance)

            salesupto = 0
            for sales in sales_sql:
                saleamount = float(sales.asset_purchase_cost)
                saledate = datetime.strptime(sales.posting_date, "%Y-%m-%d").date()
                days = getDateDiffDays(finyrfrom, saledate)
                if salesupto > opening_balance:
                    calcdepron = abs(abs((opening_balance - salesupto)) - saleamount)
                    calcdepron = calcdepron - (calcdepron * factor)
                    depronopening = depronopening + ((calcdepron * rateofdepr / 100) * (days / TOTAL_DAYS_IN_YEAR))
                else:
                    depronopening = depronopening + (((saleamount - (saleamount * factor)) * rateofdepr / 100) * (days / TOTAL_DAYS_IN_YEAR))
                value = value - saleamount;
                if (value <= 0):
                    break

        elif (totalsales < opening_balance):
            sales_sql = frappe.db.sql("""select * from `tabFixed Asset Sale` where docstatus=1 and fixed_asset_account=%s and posting_date>=%s and posting_date<=%s""", (fixed_asset_name, finyrfrom, finyrto), as_dict=True)
            value = totalsales
            factor = 1
            factor = deprtilllastyr / opening_balance
            for sales in sales_sql:
                saleamount = float(sales.asset_purchase_cost)
                saledate = datetime.strptime(sales.posting_date, "%Y-%m-%d").date()
                days = getDateDiffDays(finyrfrom, saledate)
                depronopening = depronopening + (((saleamount - (saleamount * factor)) * rateofdepr / 100) * (days / TOTAL_DAYS_IN_YEAR))
                value = value - saleamount;
            if value > 0:
                depronopening = depronopening + (((value - (value * factor)) * rateofdepr / 100))

        global depronpurchases
        depronpurchases = float(0)

        if (totalsales <= opening_balance or totalsales == 0):
            purchases_sql = frappe.db.sql("""select * from `tabFixed Asset Account` pur where pur.fixed_asset_name=%s and pur.purchase_date>=%s and pur.purchase_date<=%s""", (fixed_asset_name, finyrfrom, finyrto), as_dict=True)
            for purchases in purchases_sql:
                puramount = purchases.gross_purchase_value
                purdate = datetime.strptime(purchases.purchase_date, "%Y-%m-%d").date()
                days = getDateDiffDays(purdate, finyrto)
                depronpurchases = depronpurchases + ((puramount * rateofdepr / 100) * (days / TOTAL_DAYS_IN_YEAR))

        elif totalsales < (opening_balance + totalpurchase):
            difference = totalsales - opening_balance;
            purchases_sql = frappe.db.sql("""select * from `tabFixed Asset Account` pur where pur.fixed_asset_name=%s and pur.purchase_date>=%s and pur.purchase_date<=%s""", (fixed_asset_name, finyrfrom, finyrto), as_dict=True)
            for purchases in purchases_sql:
                puramount = purchases.gross_purchase_value
                purdate = purchases.purchase_date
                sales_sql = frappe.db.sql("""select * from `tabFixed Asset Sale` where docstatus=1 and fixed_asset_account=%s and posting_date>=%s and posting_date<=%s""", (fixed_asset_name, finyrfrom, finyrto), as_dict=True)
                selectsaledt = 0;
                days = 0;
                for sales in sales_sql:
                    saleamount = float(sales.asset_purchase_cost)
                    selectsaledt = selectsaledt + saleamount
                    saledate = datetime.strptime(sales.posting_date, "%Y-%m-%d").date()
                    if (selectsaledt > opening_balance and selectsaledt <= (opening_balance + totalpurchase)) :
                        days = getDateDiffDays(purdate, saledate)

                while ((puramount - difference) > 0):
                    if (difference <= 0 and puramount > 0):
                        days = getDateDiffDays(purdate, finyrto)
                        depronpurchases = depronpurchases + ((((puramount - difference) * rateofdepr / 100)) * (days / TOTAL_DAYS_IN_YEAR))
                        break
                    elif (difference < puramount):
                        depronpurchases = depronpurchases + (((difference * rateofdepr / 100)) * (days / TOTAL_DAYS_IN_YEAR))
                        puramount = puramount - difference
                        difference = 0;
                    elif (difference >= puramount):
                        depronpurchases = depronpurchases + (((puramount * rateofdepr / 100)) * (days / TOTAL_DAYS_IN_YEAR))
                        difference = difference - puramount
                    puramount = puramount - difference

        elif (totalsales == (opening_balance + totalpurchase)):
                difference = (opening_balance + totalpurchase) - totalsales
                purchases_sql = frappe.db.sql("""select * from `tabFixed Asset Account` pur where  pur.fixed_asset_name=%s and pur.purchase_date>=%s and pur.purchase_date<=%s""", (fixed_asset_name, finyrfrom, finyrto), as_dict=True)
                for purchases in purchases_sql:
                    puramount = purchases.gross_purchase_value
                    purdate = datetime.strptime(purchases.purchase_date, "%Y-%m-%d").date()
                    if ((puramount + difference) < totalpurchase):
                        sales_sql = frappe.db.sql("""select * from `tabFixed Asset Sale` where docstatus = 1 and fixed_asset_account=%s and posting_date>=%s and posting_date<=%s""", (fixed_asset_name, finyrfrom, finyrto), as_dict=True)
                        selectsaledt = 0
                        days = 0
                        for sales in sales_sql:
                            saleamount = float(sales.asset_purchase_cost)
                            selectsaledt = selectsaledt + saleamount
                            saledate = datetime.strptime(sales.posting_date, "%Y-%m-%d").date()
                            if (selectsaledt > opening_balance and selectsaledt <= (opening_balance + totalpurchase)):
                                days = getDateDiffDays(purdate, saledate)

                        depronpurchases = depronpurchases + ((puramount * rateofdepr / 100) * (days / TOTAL_DAYS_IN_YEAR))

                    elif ((puramount + difference) == totalpurchase):
                        sales_sql = frappe.db.sql("""select * from `tabFixed Asset Sale` where docstatus = 1 and fixed_asset_account=%s and posting_date>=%s and posting_date<=%s""", (fixed_asset_name, finyrfrom, finyrto), as_dict=True)
                        selectsaledt = 0
                        days = 0
                        for sales in sales_sql:
                            saleamount = float(sales.asset_purchase_cost)
                            selectsaledt = selectsaledt + saleamount
                            saledate = datetime.strptime(sales.posting_date, "%Y-%m-%d").date()
                            if (selectsaledt > opening_balance and selectsaledt <= (opening_balance + totalpurchase)):
                                days = getDateDiffDays(purdate, saledate)

                        depronpurchases = depronpurchases + ((puramount * rateofdepr / 100) * (days / TOTAL_DAYS_IN_YEAR))

        deprwrittenback = 0

        if (totalsales == opening_balance):
            deprwrittenback = depronopening + deprtilllastyr
        elif (totalsales == (opening_balance + totalpurchase)):
            deprwrittenback = deprtilllastyr + depronopening + depronpurchases
        elif (totalsales < opening_balance):
            sales_sql = frappe.db.sql("""select * from `tabFixed Asset Sale` where docstatus = 1 and fixed_asset_account=%s and posting_date>=%s and posting_date<=%s""", (fixed_asset_name, finyrfrom, finyrto), as_dict=True)
            value = totalsales
            factor = deprtilllastyr / opening_balance
            for sales in sales_sql:
                saleamount = float(sales.asset_purchase_cost)
                saledate = datetime.strptime(sales.posting_date, "%Y-%m-%d").date()
                days = getDateDiffDays(finyrfrom, saledate)
                deprwrittenback = deprwrittenback + ((saleamount * rateofdepr / 100) * (days / TOTAL_DAYS_IN_YEAR))
                deprwrittenback = deprwrittenback + (saleamount * factor)
                value = value - saleamount
                if (value <= 0):
                    break

        elif (totalsales < (opening_balance + totalpurchase)):
                purchases_sql = frappe.db.sql("""select * from `tabFixed Asset Account` pur where pur.fixed_asset_name=%s and pur.purchase_date>=%s and pur.purchase_date<=%s""", (fixed_asset_name, finyrfrom, finyrto), as_dict=True)
                deprwrittenback = depronopening + deprtilllastyr
                value = totalsales - opening_balance
                for purchases in purchases_sql:
                    puramount = purchases.purchase_amount
                    purdate = datetime.strptime(purchases.purchase_date, "%Y-%m-%d").date()
                    if (value <= puramount):
                        sales_sql = frappe.db.sql("""select * from `tabFixed Asset Sale` where docstatus = 1 and fixed_asset_account=%s and posting_date>=%s and posting_date<=%s""", (fixed_asset_name, finyrfrom, finyrto), as_dict=True)
                        salevsopen = 0;
                        for sales in sales_sql:
                            saleamount = float(sales.asset_purchase_cost)
                            saledate = datetime.strptime(sales.posting_date, "%Y-%m-%d").date()
                            salevsopen = salevsopen + saleamount
                            if (value <= saleamount and salevsopen > opening_balance):
                                days = getDateDiffDays(purdate, saledate)
                                deprwrittenback = deprwrittenback + ((value * rateofdepr / 100) * (days / TOTAL_DAYS_IN_YEAR))
                                value = value - saleamount

                    if (value <= 0) :
                        break

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
               flt(deprwrittenback,2),
               flt(((deprtilllastyr + depronopening + depronpurchases) - deprwrittenback),2)]

        data.append(row)

    columns = ["FIXED_ASSET_NAME",
               "FIXED_ASSET_ACCOUNT",
               "RATEOFDEPR",
               "COST_AS_ON "+str(finyrfrom),
               "PURCHASES",
               "SALES",
               "CLOSING_COST "+str(finyrto),
               "DEPRECIATION_AS_ON "+str(finyrfrom),
               "DEPR_OPENING_FOR_CURRENT_YEAR",
               "DEPR_PROVIDED_ON_PURCHASE_FOR_YEAR",
               "WRITTEN_BACK",
               "DEPRECIATION_CLOSING_AS_ON "+str(finyrto)]

    return columns, data

