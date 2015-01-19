# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from __future__ import division
import frappe
from datetime import date, timedelta
from datetime import datetime
from erpnext.accounts.utils import get_fiscal_year
from frappe.utils import flt


def get_date_difference_in_days(d1, d2):
    return abs((d2 - d1).days)

    
def get_depr_provided_till_last_year(day_before_start, fixed_asset_name):
        for accdepr in frappe.get_doc("Fixed Asset Account", fixed_asset_name).depreciation:
           if get_fiscal_year(fiscal_year = accdepr.fiscal_year) == get_fiscal_year(date = day_before_start):
               return accdepr.total_accumulated_depreciation
        return 0

        
def get_depr_provided_this_year(depreciation_method, depr_provided_on_opening_balance, \
	purchase_value, depr_provided_till_last_year, rate_of_depreciation):

	if depreciation_method == "Written Down" or \
	    (depr_provided_on_opening_balance <= (purchase_value - depr_provided_till_last_year)):
		return flt(depr_provided_on_opening_balance,2)

	elif depr_provided_on_opening_balance > (purchase_value - depr_provided_till_last_year) and \
	    (purchase_value - depr_provided_till_last_year) < (purchase_value * rate_of_depreciation / 100) and \
	    depreciation_method=="Straight Line":
		return flt(purchase_value - depr_provided_till_last_year,2)

	elif depreciation_method=="Straight Line":
		return 0


def get_report_data(financial_year_from, financial_year_to, company, fixed_asset=None):
    data = []
    financial_year_from = datetime.strptime(financial_year_from, "%Y-%m-%d").date()
    financial_year_to = datetime.strptime(financial_year_to, "%Y-%m-%d").date()
    day_before_start = financial_year_from - timedelta (days=1)    
    TOTAL_DAYS_IN_YEAR = 365
    depreciation_method = frappe.get_doc("Company", company).default_depreciation_method

    asset_query = """select fa.*,
		  ifnull((select sum(sale.asset_purchase_cost) from `tabFixed Asset Sale` sale 
			where sale.fixed_asset_account=fa.fixed_asset_name and sale.docstatus=1
			and sale.posting_date>=%s and sale.posting_date<=%s),0) as total_sale_value
		  from `tabFixed Asset Account` fa where (is_sold=false or 
		  (is_sold=true and (select count(*) from `tabFixed Asset Sale` sale where 
			sale.fixed_asset_account=fa.fixed_asset_name and docstatus=1 and 
			sale.posting_date>=%s and sale.posting_date<=%s)>0))"""

    if fixed_asset==None:
	    asset_query_result = frappe.db.sql(asset_query, \
	     (financial_year_from,financial_year_to,financial_year_from,financial_year_to), as_dict=True)
    else:
	    asset_query = asset_query + """and fa.fixed_asset_name=%s"""
	    asset_query_result = frappe.db.sql(asset_query, \
	     (financial_year_from,financial_year_to,financial_year_from,financial_year_to,fixed_asset), as_dict=True)


    for assets in asset_query_result:
        fixed_asset_name = assets.fixed_asset_name
        fixed_asset_account = assets.fixed_asset_account
        rate_of_depreciation = assets.depreciation_rate
        purchase_date = datetime.strptime(assets.purchase_date, "%Y-%m-%d").date()

        depr_provided_till_last_year = get_depr_provided_till_last_year(day_before_start, fixed_asset_name)

        opening_balance = 0
        if depr_provided_till_last_year > 0:
        	opening_balance = abs(assets.gross_purchase_value)

        totalpurchase = 0
        if purchase_date>=financial_year_from and purchase_date<=financial_year_to:
            totalpurchase = assets.gross_purchase_value

        totalsales = assets.total_sale_value

        depr_provided_on_opening_balance = 0

        if totalsales == 0:
		if depreciation_method!="Straight Line":
	            depr_provided_on_opening_balance = float(depr_provided_on_opening_balance + \
			(((opening_balance - depr_provided_till_last_year) * rate_of_depreciation / 100)))
		else:
	            depr_provided_on_opening_balance = float(depr_provided_on_opening_balance + \
			((opening_balance * rate_of_depreciation / 100)))		
        elif totalsales == opening_balance:
            sales_sql = frappe.db.sql("""select * from `tabFixed Asset Sale` where docstatus=1 and 
		fixed_asset_account=%s and posting_date>=%s and posting_date<=%s""", \
		(fixed_asset_name, financial_year_from, financial_year_to), as_dict=True)

            factor = 1
            if opening_balance > 0:
                factor = float(depr_provided_till_last_year / opening_balance)
		if depreciation_method=="Straight Line":
			factor = 0

            for sales in sales_sql:
                saleamount = float(sales.asset_purchase_cost)
                saledate = datetime.strptime(sales.posting_date, "%Y-%m-%d").date()
                days = get_date_difference_in_days(financial_year_from, saledate)
                depr_provided_on_opening_balance = depr_provided_on_opening_balance + \
		     (((saleamount - (saleamount * factor)) * rate_of_depreciation / 100) * \
		     (days / TOTAL_DAYS_IN_YEAR))

        depronpurchases = 0
        if purchase_date>=financial_year_from and purchase_date<=financial_year_to:
            days = get_date_difference_in_days(purchase_date, financial_year_to)
            depronpurchases = depronpurchases + \
	         ((assets.gross_purchase_value * rate_of_depreciation / 100) * \
		  (days / TOTAL_DAYS_IN_YEAR))

        depreciation_written_back = 0
        if totalsales > 0:
            depreciation_written_back = depr_provided_on_opening_balance + depr_provided_till_last_year

	depreciation_provided_this_year = get_depr_provided_this_year(depreciation_method, \
			depr_provided_on_opening_balance, \
			assets.gross_purchase_value, \
			depr_provided_till_last_year, \
			rate_of_depreciation)


        row = [fixed_asset_name,

       		fixed_asset_account,

        	rate_of_depreciation,

               	flt(opening_balance,2),

               	flt(totalpurchase,2),

               	flt(totalsales,2),

               	flt(((opening_balance + totalpurchase) - totalsales),2),

               	flt(depr_provided_till_last_year,2),

               	depreciation_provided_this_year,

               	flt(depronpurchases,2),

               	flt(depr_provided_on_opening_balance+depronpurchases,2),

               	flt(depreciation_written_back,2),

               	flt(((depr_provided_till_last_year + depreciation_provided_this_year + depronpurchases) \
			- depreciation_written_back),2)]

        data.append(row)

    return data

@frappe.whitelist()
def calculateWrittenDownOn(fixed_asset, saledate, company, saleamount):
	
	saleamount = float(saleamount)
	saledate=datetime.strptime(saledate, "%Y-%m-%d").date()
	from erpnext.accounts.utils import get_fiscal_year	
	financial_year_from, financial_year_to = get_fiscal_year(saledate)[1:]
	day_before_start = financial_year_from - timedelta (days=1)
	TOTAL_DAYS_IN_YEAR = 365
	
	ps = frappe.db.sql("""select led.* from `tabFixed Asset Account` led where is_sold=false 
		and led.fixed_asset_name=%s limit 1""", (fixed_asset), as_dict=True)

	for assets in ps:
	        fixed_asset_account = assets.fixed_asset_account
	        purchase_date = datetime.strptime(assets.purchase_date, "%Y-%m-%d").date()

	        depr_provided_till_last_year = get_depr_provided_till_last_year(day_before_start, assets.fixed_asset_name)

	        opening_balance = 0
	        if depr_provided_till_last_year > 0:
	        	opening_balance = abs(assets.gross_purchase_value)

	        factor = 1
		if opening_balance > 0:
	             factor = float(depr_provided_till_last_year / opening_balance)
		     if frappe.get_doc("Company", company).default_depreciation_method=="Straight Line":
			factor = 0

                days = get_date_difference_in_days(financial_year_from, saledate)
                depr_provided_on_opening_balance = depr_provided_on_opening_balance + \
			(((saleamount - (saleamount * factor)) * assets.depreciation_rate / 100) \
			 * (days / TOTAL_DAYS_IN_YEAR))
		
                return flt((depr_provided_on_opening_balance + depr_provided_till_last_year),2)

	frappe.throw("Either Asset is Sold Or no Record Found")
