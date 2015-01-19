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

    
def get_depreciation_provided_till_last_year(day_before_start, fixed_asset_name):
        for accdepr in frappe.get_doc("Fixed Asset Account", fixed_asset_name).depreciation:
           if get_fiscal_year(fiscal_year = accdepr.fiscal_year) == get_fiscal_year(date = day_before_start):
               return accdepr.total_accumulated_depreciation
        return 0

        
def get_depr_provided_this_year(depreciation_method, depreciation_provided_on_opening_purchase_cost, \
	purchase_value, depreciation_provided_till_last_year, rate_of_depreciation):

	if depreciation_method == "Written Down" or \
	    (depreciation_provided_on_opening_purchase_cost <= (purchase_value - depreciation_provided_till_last_year)):
		return flt(depreciation_provided_on_opening_purchase_cost,2)

	elif depreciation_provided_on_opening_purchase_cost > (purchase_value - depreciation_provided_till_last_year) and \
	    (purchase_value - depreciation_provided_till_last_year) < (purchase_value * rate_of_depreciation / 100) and \
	    depreciation_method=="Straight Line":
		return flt(purchase_value - depreciation_provided_till_last_year,2)

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

        depreciation_provided_till_last_year = get_depreciation_provided_till_last_year(day_before_start, fixed_asset_name)

        purchase_cost_at_year_start = 0
        if depreciation_provided_till_last_year > 0:
        	purchase_cost_at_year_start = abs(assets.gross_purchase_value)

        total_purchases_during_the_year = 0
        if purchase_date>=financial_year_from and purchase_date<=financial_year_to:
            total_purchases_during_the_year = assets.gross_purchase_value

        total_sales_during_the_year = assets.total_sale_value

        depreciation_provided_on_opening_purchase_cost = 0

        if total_sales_during_the_year == 0:
		if depreciation_method!="Straight Line":
	            depreciation_provided_on_opening_purchase_cost = float(depreciation_provided_on_opening_purchase_cost + \
			(((purchase_cost_at_year_start - depreciation_provided_till_last_year) * rate_of_depreciation / 100)))
		else:
	            depreciation_provided_on_opening_purchase_cost = float(depreciation_provided_on_opening_purchase_cost + \
			((purchase_cost_at_year_start * rate_of_depreciation / 100)))		
        elif total_sales_during_the_year == purchase_cost_at_year_start:
            sales_sql = frappe.db.sql("""select * from `tabFixed Asset Sale` where docstatus=1 and 
		fixed_asset_account=%s and posting_date>=%s and posting_date<=%s""", \
		(fixed_asset_name, financial_year_from, financial_year_to), as_dict=True)

            factor = 1
            if purchase_cost_at_year_start > 0:
                factor = float(depreciation_provided_till_last_year / purchase_cost_at_year_start)
		if depreciation_method=="Straight Line":
			factor = 0

            for sales in sales_sql:
                saleamount = float(sales.asset_purchase_cost)
                saledate = datetime.strptime(sales.posting_date, "%Y-%m-%d").date()
                days = get_date_difference_in_days(financial_year_from, saledate)
                depreciation_provided_on_opening_purchase_cost = depreciation_provided_on_opening_purchase_cost + \
		     (((saleamount - (saleamount * factor)) * rate_of_depreciation / 100) * \
		     (days / TOTAL_DAYS_IN_YEAR))

        depreciation_provided_on_purchases = 0
        if purchase_date>=financial_year_from and purchase_date<=financial_year_to:
            days = get_date_difference_in_days(purchase_date, financial_year_to)
            depreciation_provided_on_purchases = depreciation_provided_on_purchases + \
	         ((assets.gross_purchase_value * rate_of_depreciation / 100) * \
		  (days / TOTAL_DAYS_IN_YEAR))

        depreciation_written_back = 0
        if total_sales_during_the_year > 0:
            depreciation_written_back = depreciation_provided_on_opening_purchase_cost + depreciation_provided_till_last_year

	depreciation_provided_this_year = get_depr_provided_this_year(depreciation_method, \
			depreciation_provided_on_opening_purchase_cost, \
			assets.gross_purchase_value, \
			depreciation_provided_till_last_year, \
			rate_of_depreciation)


        row = [fixed_asset_name,

       		fixed_asset_account,

        	rate_of_depreciation,

               	flt(purchase_cost_at_year_start,2),

               	flt(total_purchases_during_the_year,2),

               	flt(total_sales_during_the_year,2),

               	flt(((purchase_cost_at_year_start + total_purchases_during_the_year) - total_sales_during_the_year),2),

               	flt(depreciation_provided_till_last_year,2),

               	depreciation_provided_this_year,

               	flt(depreciation_provided_on_purchases,2),

               	flt(depreciation_provided_on_opening_purchase_cost+depreciation_provided_on_purchases,2),

               	flt(depreciation_written_back,2),

               	flt(((depreciation_provided_till_last_year + \
			depreciation_provided_this_year + \
			depreciation_provided_on_purchases) - depreciation_written_back),2)]

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
	
	ps = frappe.db.sql("""select * from `tabFixed Asset Account` where is_sold=false 
		and fixed_asset_name=%s limit 1""", (fixed_asset), as_dict=True)

	for assets in ps:
	        fixed_asset_account = assets.fixed_asset_account
	        purchase_date = datetime.strptime(assets.purchase_date, "%Y-%m-%d").date()

	        depreciation_provided_till_last_year = get_depreciation_provided_till_last_year(day_before_start, assets.fixed_asset_name)

	        purchase_cost_at_year_start = 0
	        if depreciation_provided_till_last_year > 0:
	        	purchase_cost_at_year_start = abs(assets.gross_purchase_value)

	        factor = 1
		if purchase_cost_at_year_start > 0:
	             factor = depreciation_provided_till_last_year / purchase_cost_at_year_start
		     if frappe.get_doc("Company", company).default_depreciation_method=="Straight Line":
			factor = 0

                days = get_date_difference_in_days(financial_year_from, saledate)
                depreciation_provided_on_opening_purchase_cost = depreciation_provided_on_opening_purchase_cost + \
			(((saleamount - (saleamount * factor)) * assets.depreciation_rate / 100) \
			 * (days / TOTAL_DAYS_IN_YEAR))
		
                return flt((depreciation_provided_on_opening_purchase_cost + depreciation_provided_till_last_year),2)

	frappe.throw("Either Asset is Sold Or no Record Found")
