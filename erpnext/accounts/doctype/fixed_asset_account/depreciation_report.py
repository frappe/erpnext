# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from __future__ import division
import frappe
from frappe import _
from datetime import date, timedelta
from datetime import datetime
from erpnext.accounts.utils import get_fiscal_year
from frappe.utils import flt

def get_date_difference_in_days(d1, d2):
    return abs((d2 - d1).days)

class Depreciation:
	def __init__(self,financial_year_from, financial_year_to, company, fixed_asset=None, expand_levels=False):
		self.financial_year_from = datetime.strptime(financial_year_from, "%Y-%m-%d").date()
		self.financial_year_to = datetime.strptime(financial_year_to, "%Y-%m-%d").date()
		self.day_before_start = self.financial_year_from - timedelta (days=1)    
		self.TOTAL_DAYS_IN_YEAR = 365
		self.depreciation_method = frappe.get_doc("Company", company).default_depreciation_method
		self.fixed_asset = fixed_asset
		self.set_totals_to_zero()
		self.expand_levels = expand_levels
		if fixed_asset:
			self.expand_levels = True

	
	def set_totals_to_zero(self):
		self.group_total_year_start_purchase_cost = 0
		self.group_total_purchases_in_the_year = 0
		self.group_total_sales_in_the_year = 0
		self.group_total_asset_value_at_year_end = 0
		self.group_total_depreciation_till_last_year = 0
		self.group_total_depreciation_in_the_year = 0
		self.group_total_depreciation_on_purchase_in_year = 0
		self.group_total_deprecitaion_this_year = 0
		self.group_total_depreciation_written_back = 0
		self.group_total_accumulated_depreciation_at_year_end = 0
		self.group_total_net_closing = 0
		self.group_total_net_opening = 0


	def get_assets(self):
	    asset_query = """select fa.* from `tabFixed Asset Account` fa 
		  where (is_sold=false or (is_sold=true and (select count(*) from `tabFixed Asset Sale` sale 
		     where sale.fixed_asset_account=fa.fixed_asset_name and docstatus=1 and 
			sale.posting_date>=%s and sale.posting_date<=%s)>0))"""

	    if self.fixed_asset==None:
		    asset_query = asset_query + """ order by fa.fixed_asset_account"""
		    return frappe.db.sql(asset_query, (self.financial_year_from,self.financial_year_to), as_dict=True)
	    else:
		    asset_query = asset_query + """ and fa.fixed_asset_name=%s"""
		    return frappe.db.sql(asset_query, (self.financial_year_from, self.financial_year_to, \
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
	    self.get_start_group_name()
	    for assets in asset_query_result:
		asset_value_dict = {}

	        asset_value_dict['depreciation_provided_till_last_year'] = self.get_depreciation_provided_till_last_year(assets)

	        asset_value_dict['purchase_cost_at_year_start']  = self.get_purchase_cost_at_year_start(assets, asset_value_dict)

	        asset_value_dict['total_purchases_during_the_year'] = self.get_asset_purchases_in_the_year(assets)

	        asset_value_dict['total_sales_during_the_year'] = self.get_asset_sales_in_the_year(assets)

	        asset_value_dict['depreciation_provided_on_opening_purchase_cost'] = \
			 self.get_depreciation_provided_on_opening_purchase_cost(assets, asset_value_dict)

	        asset_value_dict['depreciation_provided_on_purchases'] = \
			self.get_depreciation_provided_on_purchases(assets)

	        asset_value_dict['depreciation_written_back'] = self.get_depreciation_written_back(asset_value_dict)

		asset_value_dict['depreciation_provided_this_year'] = \
			self.get_depreciation_provided_this_year(assets, asset_value_dict)

		self.do_depreciation_total(asset_value_dict)

		self.calculate_sub_total(asset_value_dict, assets.fixed_asset_account, data)

		if asset_value_dict['total_purchases_during_the_year'] + \
			asset_value_dict['purchase_cost_at_year_start'] > 0:			
				if self.expand_levels==True:
					data.append(self.build_row(assets, asset_value_dict))
			

  	    self.calculate_sub_total(asset_value_dict, assets.fixed_asset_account, data, True)	

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
	

	def get_depreciation_provided_on_opening_purchase_cost(self, asset, dict_value):
	   if dict_value['total_sales_during_the_year'] == 0:
		return self.depreciation_provided_on_opening_purchase_cost_no_sale(asset, dict_value)
           elif dict_value['total_sales_during_the_year'] > 0:
		return self.depreciation_provided_on_opening_purchase_cost_with_sale(asset, dict_value)
	   return 0


	def get_depreciation_provided_this_year(self, asset, dict_value):
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

	def do_depreciation_total(self, dict_value):
		dict_value['total_accumulated_depreciation_till_year_end'] = \
				((dict_value['depreciation_provided_till_last_year'] + \
				dict_value['depreciation_provided_this_year'] + \
				dict_value['depreciation_provided_on_purchases']) - \
				dict_value['depreciation_written_back'])

		dict_value['total_asset_value_at_year_end'] = \
				((dict_value['purchase_cost_at_year_start'] + \
				dict_value['total_purchases_during_the_year']) - \
				dict_value['total_sales_during_the_year'])


	def build_row(self, asset, dict_value):

		return {
			"fixed_asset_name": asset.fixed_asset_name,
			"fixed_asset_account": asset.fixed_asset_account,
			"rate_of_depreciation": asset.depreciation_rate,
			"cost_as_on": dict_value['purchase_cost_at_year_start'],

			"purchases": dict_value['total_purchases_during_the_year'],

			"sales": dict_value['total_sales_during_the_year'],

			"closing_cost": dict_value['total_asset_value_at_year_end'],

			"opening_depreciation": dict_value['depreciation_provided_till_last_year'],

			"depreciation_provided_on_opening_current_year": \
					dict_value['depreciation_provided_this_year'],

			"depreciation_provided_on_purchase_current_year": \
					dict_value['depreciation_provided_on_purchases'],

			"total_depreciation_for_current_year": \
				dict_value['depreciation_provided_on_opening_purchase_cost']+\
				dict_value['depreciation_provided_on_purchases'],

			"depreciation_written_back": \
				dict_value['depreciation_written_back'],

			"total_accumulated_depreciation": \
				dict_value['total_accumulated_depreciation_till_year_end'],

			"net_closing_value": \
				dict_value['total_asset_value_at_year_end'] - \
				dict_value['total_accumulated_depreciation_till_year_end'],

			"net_opening_value": \
				dict_value['purchase_cost_at_year_start'] - \
				dict_value['depreciation_provided_till_last_year']
		       }

	def calculate_sub_total(self, dict_value, group_name, data, end=False):

		if (self.old_group_name != group_name or end==True) and self.fixed_asset==None:
			data.append(self.get_total_row(self.old_group_name))
			self.old_group_name = group_name
			self.set_totals_to_zero()

		self.group_total_year_start_purchase_cost += dict_value['purchase_cost_at_year_start']

		self.group_total_purchases_in_the_year += dict_value['total_purchases_during_the_year']

		self.group_total_sales_in_the_year += dict_value['total_sales_during_the_year']

		self.group_total_asset_value_at_year_end += dict_value['total_asset_value_at_year_end']

		self.group_total_depreciation_till_last_year += dict_value['depreciation_provided_till_last_year']

		self.group_total_depreciation_in_the_year += dict_value['depreciation_provided_this_year']

		self.group_total_depreciation_on_purchase_in_year += dict_value['depreciation_provided_on_purchases']

		self.group_total_deprecitaion_this_year += dict_value['depreciation_provided_on_opening_purchase_cost']+\
				dict_value['depreciation_provided_on_purchases']

		self.group_total_depreciation_written_back += dict_value['depreciation_written_back']

		self.group_total_accumulated_depreciation_at_year_end += \
				dict_value['total_accumulated_depreciation_till_year_end']

		self.group_total_net_closing += dict_value['total_asset_value_at_year_end'] - \
				dict_value['total_accumulated_depreciation_till_year_end']

		self.group_total_net_opening += dict_value['purchase_cost_at_year_start'] - \
				dict_value['depreciation_provided_till_last_year']


	def get_total_row(self, group_name):
			return {
				"fixed_asset_name": 'Sub Total',
				"fixed_asset_account": group_name,
				"rate_of_depreciation": '',
				"cost_as_on": self.group_total_year_start_purchase_cost,
				"purchases": self.group_total_purchases_in_the_year,
				"sales": self.group_total_sales_in_the_year,
				"closing_cost": self.group_total_asset_value_at_year_end,
				"opening_depreciation": self.group_total_depreciation_till_last_year,
				"depreciation_provided_on_opening_current_year": \
					self.group_total_depreciation_in_the_year,
				"depreciation_provided_on_purchase_current_year": \
					self.group_total_depreciation_on_purchase_in_year,
				"total_depreciation_for_current_year": \
					self.group_total_deprecitaion_this_year,
				"depreciation_written_back": \
					self.group_total_depreciation_written_back,
				"total_accumulated_depreciation": \
					self.group_total_accumulated_depreciation_at_year_end,
				"net_closing_value": self.group_total_net_closing,
				"net_opening_value": self.group_total_net_opening
			      }


	def get_start_group_name(self):
		query = frappe.db.sql("""select fixed_asset_account from `tabFixed Asset Account` 
				order by fixed_asset_account limit 1""", as_dict=True)

		for results in query:
			self.old_group_name = results.fixed_asset_account


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

		return -1


	def get_unsold_asset(self):
		unsold_query = frappe.db.sql("""select * from `tabFixed Asset Account` where is_sold=false 
			and fixed_asset_name=%s limit 1""", (self.fixed_asset), as_dict=True)
		for result in unsold_query:
			return result


def get_report_columns(financial_year_from, financial_year_to):
    columns = [
		{
			"fieldname": "fixed_asset_name",
			"label": _("FIXED ASSET NAME"),
			"fieldtype": "Data",
			"width": 300
		},
		{
			"fieldname": "fixed_asset_account",
			"label": _("FIXED ASSET ACCOUNT"),
			"fieldtype": "Data",
			"width": 250
		},
		{
			"fieldname": "rate_of_depreciation",
			"label": _("RATE OF DEPRECIATION"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "cost_as_on",
			"label": _("COST AS ON "+financial_year_from),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "purchases",
			"label": _("PURCHASES"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "sales",
			"label": _("SALES"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "closing_cost",
			"label": _("CLOSING COST "+financial_year_to),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "opening_depreciation",
			"label": _("DEPRECIATION AS ON"+financial_year_from),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "depreciation_provided_on_opening_current_year",
			"label": _("DEPRECIATION PROVIDED ON OPENING BALANCE FOR CURRENT YEAR"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "depreciation_provided_on_purchase_current_year",
			"label": _("DEPRECIATION PROVIDED ON PURCHASES FOR CURRENT YEAR"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "total_depreciation_for_current_year",
			"label": _("TOTAL DEPRECIATION FOR CURRENT YEAR"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "depreciation_written_back",
			"label": _("DEPRECIATION WRITTEN BACK"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "total_accumulated_depreciation",
			"label": _("TOTAL ACCUMULATED DEPRECIATION AS ON "+financial_year_to),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "net_closing_value",
			"label": _("NET ASSET VALUE "+financial_year_to),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "net_opening_value",
			"label": _("NET ASSET VALUE "+financial_year_from),
			"fieldtype": "Currency",
			"width": 120
		}
			
	]
    return columns
    

def get_report_data(financial_year_from, financial_year_to, company, fixed_asset=None, expand_levels=False):
    depreciation = Depreciation(financial_year_from, financial_year_to, company, fixed_asset, expand_levels)
    return depreciation.run()


@frappe.whitelist()
def get_written_down_when_selling_fixed_asset(fixed_asset, saledate, company, saleamount):
	
	saleamount = float(saleamount)
	saledate=datetime.strptime(saledate, "%Y-%m-%d").date()
	from erpnext.accounts.utils import get_fiscal_year	
	financial_year_from, financial_year_to = get_fiscal_year(saledate)[1:]
	
	depreciation = Depreciation(str(financial_year_from), str(financial_year_to), company, fixed_asset)
	value = depreciation.calculate_written_down_on(saledate, saleamount)
	if value > 0:
		return value
	raise frappe.ValidationError, "Either Asset Already Sold OR No Record Found"
