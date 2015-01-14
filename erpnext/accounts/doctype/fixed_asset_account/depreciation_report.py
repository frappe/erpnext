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
    
def getDeprTillLastYear(day_before_start, fixed_asset_name):
        for accdepr in frappe.get_doc("Fixed Asset Account", fixed_asset_name).depreciation:
           if get_fiscal_year(fiscal_year = accdepr.fiscal_year) == get_fiscal_year(date = day_before_start):
               return accdepr.total_accumulated_depreciation
        return 0
        
def getDeprProvidedThisYear(method, depronopening, purchase_value, deprtilllastyr, rateofdepr):
	if method == "Written Down" or (depronopening <= (assets.gross_purchase_value - deprtilllastyr)):
		return flt(depronopening,2)
	elif depronopening > (purchase_value - deprtilllastyr) and \
	(assets.gross_purchase_value - deprtilllastyr) < (assets.gross_purchase_value * rateofdepr / 100) and \
	method=="Straight Line":
		return flt(purchase_value - deprtilllastyr,2)
	else method=="Straight Line":
		return 0

def get_report_data(finyrfrom, finyrto, company, fa_name=None):
    data = []
    finyrfrom = datetime.strptime(finyrfrom, "%Y-%m-%d").date()
    finyrto = datetime.strptime(finyrto, "%Y-%m-%d").date()
    day_before_start = finyrfrom - timedelta (days=1)    
    TOTAL_DAYS_IN_YEAR = 365
    method = frappe.get_doc("Company", company).default_depreciation_method
    global ps
    if fa_name==None:
	    ps = frappe.db.sql("""select led.*,ifnull((select sum(sale.asset_purchase_cost) from `tabFixed Asset Sale` sale where sale.fixed_asset_account=led.fixed_asset_name and sale.docstatus=1  and sale.posting_date>=%s and sale.posting_date<=%s),0) as total_sale_value
           from `tabFixed Asset Account` led where is_sold=false or (is_sold=true and (select count(*) from `tabFixed Asset Sale` sale where sale.fixed_asset_account=led.fixed_asset_name and docstatus=1 and sale.posting_date>=%s and sale.posting_date<=%s)>0)""", (finyrfrom,finyrto,finyrfrom,finyrto), as_dict=True)
    else:
	    ps = frappe.db.sql("""select led.*,ifnull((select sum(sale.asset_purchase_cost) from `tabFixed Asset Sale` sale where sale.fixed_asset_account=led.fixed_asset_name and sale.docstatus=1  and sale.posting_date>=%s and sale.posting_date<=%s),0) as total_sale_value
           from `tabFixed Asset Account` led where (is_sold=false or (is_sold=true and (select count(*) from `tabFixed Asset Sale` sale where sale.fixed_asset_account=led.fixed_asset_name and docstatus=1 and sale.posting_date>=%s and sale.posting_date<=%s)>0)) and led.fixed_asset_name=%s""", (finyrfrom,finyrto,finyrfrom,finyrto,fa_name), as_dict=True)


    for assets in ps:
        fixed_asset_name = assets.fixed_asset_name
        fixed_asset_account = assets.fixed_asset_account
        rateofdepr = abs(assets.depreciation_rate)
        purchase_date = datetime.strptime(assets.purchase_date, "%Y-%m-%d").date()

        global deprtilllastyr # Depreciation provided till close of last fiscal Yr.
        deprtilllastyr = getDeprTillLastYear(day_before_start, fixed_asset_name)

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
        depronopening = 0

        if totalsales == 0:
		if method!="Straight Line":
	            depronopening = float(depronopening + (((opening_balance - deprtilllastyr) * rateofdepr / 100)))
		else:
	            depronopening = float(depronopening + ((opening_balance * rateofdepr / 100)))		
        elif totalsales == opening_balance:
            sales_sql = frappe.db.sql("""select * from `tabFixed Asset Sale` where docstatus=1 and fixed_asset_account=%s and posting_date>=%s and posting_date<=%s""", (fixed_asset_name, finyrfrom, finyrto), as_dict=True)
            factor = 1
            if opening_balance > 0:
                factor = float(deprtilllastyr / opening_balance)
		if method=="Straight Line":
			factor = 0

            for sales in sales_sql:
                saleamount = float(sales.asset_purchase_cost)
                saledate = datetime.strptime(sales.posting_date, "%Y-%m-%d").date()
                days = getDateDiffDays(finyrfrom, saledate)
                depronopening = depronopening + (((saleamount - (saleamount * factor)) * rateofdepr / 100) * (days / TOTAL_DAYS_IN_YEAR))

        global depronpurchases # Depreciation provided on Purchase in the Current FY
        depronpurchases = 0
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
               	getDeprProvidedThisYear(method, depronopening, assets.gross_purchase_value, deprtilllastyr, rateofdepr),
               	flt(depronpurchases,2),
               	flt(depronopening+depronpurchases,2),
               	flt(deprwrittenback,2),
               	flt(((deprtilllastyr + getDeprProvidedThisYear(method, depronopening, assets.gross_purchase_value, deprtilllastyr, rateofdepr) + depronpurchases) - deprwrittenback),2)]

        data.append(row)

    return data

@frappe.whitelist()
def calculateWrittenDownOn(fa_account, saledate, company, saleamount):
	
	saleamount = float(saleamount)
	saledate=datetime.strptime(saledate, "%Y-%m-%d").date()
	from erpnext.accounts.utils import get_fiscal_year	
	finyrfrom, finyrto =get_fiscal_year(saledate)[1:]
	day_before_start = finyrfrom - timedelta (days=1)
	TOTAL_DAYS_IN_YEAR = 365
	
	ps = frappe.db.sql("""select led.* from `tabFixed Asset Account` led where is_sold=false and led.fixed_asset_name=%s limit 1""", (fa_account), as_dict=True)

        global deprwrittenback

	for assets in ps:
	        fixed_asset_account = assets.fixed_asset_account
	        purchase_date = datetime.strptime(assets.purchase_date, "%Y-%m-%d").date()

	        deprtilllastyr = getDeprTillLastYear(day_before_start, assets.fixed_asset_name)

	        opening_balance = 0
	        if deprtilllastyr > 0:
	        	opening_balance = abs(assets.gross_purchase_value)

	        depronopening = 0

	        factor = 1
		if opening_balance > 0:
	             factor = float(deprtilllastyr / opening_balance)
		     if frappe.get_doc("Company", company).default_depreciation_method=="Straight Line":
			factor = 0

                days = getDateDiffDays(finyrfrom, saledate)
                depronopening = depronopening + (((saleamount - (saleamount * factor)) * assets.depreciation_rate / 100) * (days / TOTAL_DAYS_IN_YEAR))
		
                return flt((depronopening + deprtilllastyr),2)

	frappe.throw("Either Asset is Sold, Or no Record Found")
