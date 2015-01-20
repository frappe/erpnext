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

class Depreciation:
	def __init__(self,financial_year_from, financial_year_to, company, fixed_asset=None):
	    self.financial_year_from = datetime.strptime(financial_year_from, "%Y-%m-%d").date()
	    self.financial_year_to = datetime.strptime(financial_year_to, "%Y-%m-%d").date()
	    self.day_before_start = self.financial_year_from - timedelta (days=1)    
	    self.TOTAL_DAYS_IN_YEAR = 365
	    self.depreciation_method = frappe.get_doc("Company", company).default_depreciation_method
	    self.fixed_asset = fixed_asset


	def get_assets(self):
	    asset_query = """select fa.* from `tabFixed Asset Account` fa 
		  where (is_sold=false or (is_sold=true and (select count(*) from `tabFixed Asset Sale` sale 
		     where sale.fixed_asset_account=fa.fixed_asset_name and docstatus=1 and 
			sale.posting_date>=%s and sale.posting_date<=%s)>0))"""

	    if self.fixed_asset==None:
		    return frappe.db.sql(asset_query, (self.financial_year_from,self.financial_year_to), as_dict=True)
	    else:
		    asset_query = asset_query + """and fa.fixed_asset_name=%s"""
		    return frappe.db.sql(asset_query, (self.financial_year_from,self.financial_year_to, \
				self.fixed_asset), as_dict=True)

	def get_asset_sales_in_the_year(self,asset):
	    sale_query = """select ifnull(sum(sale.asset_purchase_cost),0) as total_sales 
			from `tabFixed Asset Sale` sale where sale.fixed_asset_account=%s and sale.docstatus=1
			and sale.posting_date>=%s and sale.posting_date<=%s limit 1"""

	    sales_query_result = frappe.db.sql(sale_query, \
			(asset.fixed_asset_name, self.financial_year_from, self.financial_year_to), \
			as_dict=True)

	    for results in sales_query_result:
		return results.total_sales


	def get_asset_purchases_in_the_year(self,asset):
	        purchase_date = datetime.strptime(asset.purchase_date, "%Y-%m-%d").date()	    
	        if purchase_date>=self.financial_year_from and purchase_date<=self.financial_year_to:
	            return asset.gross_purchase_value
	        return 0	        


	def get_depreciation_provided_till_last_year(self,asset):
	        for accdepr in frappe.get_doc("Fixed Asset Account", asset.fixed_asset_name).depreciation:
	           if get_fiscal_year(fiscal_year = accdepr.fiscal_year) == \
				get_fiscal_year(date = self.day_before_start):
	               return accdepr.total_accumulated_depreciation
	        return 0


	def get_purchase_cost_at_year_start(self,asset,dict_value):
	        if dict_value['depreciation_provided_till_last_year'] > 0:
	        	return abs(asset.gross_purchase_value)
		return 0
	    

	def run(self):
	    asset_query_result = self.get_assets()
	    data = []
	    for assets in asset_query_result:
		asset_value_dict = {}

	        asset_value_dict['depreciation_provided_till_last_year'] = self.get_depreciation_provided_till_last_year(assets)

	        asset_value_dict['purchase_cost_at_year_start']  = self.get_purchase_cost_at_year_start(assets,asset_value_dict)

	        asset_value_dict['total_purchases_during_the_year'] = self.get_asset_purchases_in_the_year(assets)

	        asset_value_dict['total_sales_during_the_year'] = self.get_asset_sales_in_the_year(assets)

	        asset_value_dict['depreciation_provided_on_opening_purchase_cost'] = \
			 self.get_depreciation_provided_on_opening_purchase_cost(assets,asset_value_dict)

	        asset_value_dict['depreciation_provided_on_purchases'] = \
			self.get_depreciation_provided_on_purchases(assets)

	        asset_value_dict['depreciation_written_back'] = self.get_depreciation_written_back(asset_value_dict)

		asset_value_dict['depreciation_provided_this_year'] = self.get_depr_provided_this_year(asset_value_dict, assets)

		if asset_value_dict['total_purchases_during_the_year'] + \
			asset_value_dict['purchase_cost_at_year_start'] > 0:
			data.append(self.build_row(assets, asset_value_dict))

	    return data

		

	def get_depreciation_written_back(self,dict_value):
            if dict_value['total_sales_during_the_year'] > 0:
	        return dict_value['depreciation_provided_on_opening_purchase_cost'] +\
			dict_value['depreciation_provided_till_last_year']
	    return 0


	def get_depreciation_provided_on_purchases(self,asset):
	    purchase_date = datetime.strptime(asset.purchase_date, "%Y-%m-%d").date()	    
            if purchase_date>=self.financial_year_from and \
	    	    purchase_date<=self.financial_year_to:
	        days = get_date_difference_in_days(purchase_date, self.financial_year_to)
	        return (asset.gross_purchase_value * asset.depreciation_rate / 100) * \
				  (days / self.TOTAL_DAYS_IN_YEAR)
	    return 0


	def get_sales_data(self,asset):
            sales_sql = frappe.db.sql("""select * from `tabFixed Asset Sale` where docstatus=1 and 
		fixed_asset_account=%s and posting_date>=%s and posting_date<=%s limit 1""", \
		(asset.fixed_asset_name, self.financial_year_from, self.financial_year_to), as_dict=True)

	    for sales in sales_sql:
		return sales
	   


	def depreciation_provided_on_opening_purchase_cost_no_sale(self,asset, dict_value):
		if self.depreciation_method!="Straight Line":
	            return ((dict_value['purchase_cost_at_year_start'] - \
			       dict_value['depreciation_provided_till_last_year']) *\
				 asset.depreciation_rate / 100)
		else:
	            return (dict_value['purchase_cost_at_year_start'] *\
			       asset.depreciation_rate / 100)

	def depreciation_provided_on_opening_purchase_cost_with_sale(self,asset, dict_value):
	            factor = self.get_factor(dict_value)

	            sales = self.get_sales_data(asset)
	            asset_purchase_cost = float(sales.asset_purchase_cost)
	            saledate = datetime.strptime(sales.posting_date, "%Y-%m-%d").date()
	            days = get_date_difference_in_days(self.financial_year_from, saledate)
	            return ((asset_purchase_cost - (asset_purchase_cost * factor)) \
			* asset.depreciation_rate / 100) * (days / self.TOTAL_DAYS_IN_YEAR)
		

	def get_factor(self, dict_value):
	            factor = 1
	            if dict_value['purchase_cost_at_year_start'] > 0:
	                factor = dict_value['depreciation_provided_till_last_year'] /\
				 dict_value['purchase_cost_at_year_start']
			if self.depreciation_method=="Straight Line":
	 			factor = 0
		    return factor
	

	def get_depreciation_provided_on_opening_purchase_cost(self,asset,dict_value):
	   if dict_value['total_sales_during_the_year'] == 0:
		return self.depreciation_provided_on_opening_purchase_cost_no_sale(asset, dict_value)
           elif dict_value['total_sales_during_the_year'] > 0:
		return self.depreciation_provided_on_opening_purchase_cost_with_sale(asset, dict_value)
	   return 0


	def get_depr_provided_this_year(self,dict_value, asset):
		purchase_less_depreciation = asset.gross_purchase_value -\
			 dict_value['depreciation_provided_till_last_year']
		if self.depreciation_method == "Written Down" or \
		    	(dict_value['depreciation_provided_on_opening_purchase_cost'] <= \
			(purchase_less_depreciation)):
			return flt(dict_value['depreciation_provided_on_opening_purchase_cost'],2)

		elif dict_value['depreciation_provided_on_opening_purchase_cost'] > \
			(purchase_less_depreciation) and (purchase_less_depreciation) < \
			  (asset.gross_purchase_value * asset.depreciation_rate / 100) and \
			    self.depreciation_method=="Straight Line":
			return flt(purchase_less_depreciation,2)

		elif self.depreciation_method=="Straight Line":
			return 0


	def build_row(self,asset, dict_value):
		return [asset.fixed_asset_name,
       		asset.fixed_asset_account,
        	asset.depreciation_rate,
               	flt(dict_value['purchase_cost_at_year_start'],2),

               	flt(dict_value['total_purchases_during_the_year'],2),

               	flt(dict_value['total_sales_during_the_year'],2),

               	flt(((dict_value['purchase_cost_at_year_start'] + \
			dict_value['total_purchases_during_the_year']) - \
			dict_value['total_sales_during_the_year']),2),

               	flt(dict_value['depreciation_provided_till_last_year'],2),

               	dict_value['depreciation_provided_this_year'],

               	flt(dict_value['depreciation_provided_on_purchases'],2),

               	flt(dict_value['depreciation_provided_on_opening_purchase_cost']+\
			dict_value['depreciation_provided_on_purchases'],2),

               	flt(dict_value['depreciation_written_back'],2),

               	flt(((dict_value['depreciation_provided_till_last_year'] + \
			dict_value['depreciation_provided_this_year'] + \
			dict_value['depreciation_provided_on_purchases']) - \
			dict_value['depreciation_written_back']),2)]


	def calculate_written_down_on(self, saledate, saleamount):
		assets = self.get_unsold_asset()
		if assets:
			asset_value_dict = {}
		        purchase_date = datetime.strptime(assets.purchase_date, "%Y-%m-%d").date()

		        asset_value_dict['depreciation_provided_till_last_year'] =\
			   self.get_depreciation_provided_till_last_year(assets)

		        asset_value_dict['purchase_cost_at_year_start']  =\
			   self.get_purchase_cost_at_year_start(assets,asset_value_dict)

		        factor = self.get_factor(asset_value_dict)

	                days = get_date_difference_in_days(self.financial_year_from, saledate)
	                asset_value_dict['depreciation_provided_on_opening_purchase_cost'] = \
				((saleamount - (saleamount * factor)) *\
				 assets.depreciation_rate / 100) * (days / self.TOTAL_DAYS_IN_YEAR)
		
	                return flt((asset_value_dict['depreciation_provided_on_opening_purchase_cost'] +\
				 asset_value_dict['depreciation_provided_till_last_year']),2)					



	def get_unsold_asset(self):
		unsold_query = frappe.db.sql("""select * from `tabFixed Asset Account` where is_sold=false 
			and fixed_asset_name=%s limit 1""", (self.fixed_asset), as_dict=True)
		for result in unsold_query:
			return result


def get_report_columns(financial_year_from, financial_year_to):
    columns = ["FIXED ASSET NAME",
               "FIXED ASSET ACCOUNT",
               "RATE OF DEPRECIATION",
               "COST AS ON "+financial_year_from,
               "PURCHASES",
               "SALES",
               "CLOSING COST "+financial_year_to,
               "DEPRECIATION AS ON "+financial_year_from,
               "DEPRECIATION PROVIDED ON OPENING FOR CUR YR",
               "DEPRECIATION PROVIDED ON PURCHASE FOR CUR YR",
               "TOTAL DEPRECIATION FOR CUR YR",
               "WRITTEN_BACK",
               "TOTAL ACCUMULATED DEPRECIATION AS ON "+financial_year_to]
    return columns
    

def get_report_data(financial_year_from, financial_year_to, company, fixed_asset=None):
    depreciation = Depreciation(financial_year_from, financial_year_to, company, fixed_asset)
    return depreciation.run()


@frappe.whitelist()
def get_written_down_when_selling_fixed_asset(fixed_asset, saledate, company, saleamount):
	
	saleamount = float(saleamount)
	saledate=datetime.strptime(saledate, "%Y-%m-%d").date()
	from erpnext.accounts.utils import get_fiscal_year	
	financial_year_from, financial_year_to = get_fiscal_year(saledate)[1:]
	
	depreciation = Depreciation(str(financial_year_from), str(financial_year_to), company, fixed_asset)
	return depreciation.calculate_written_down_on(saledate, saleamount)
