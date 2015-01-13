# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class FixedAssetAccount(Document):
	def post_journal_entry(self):
		jv = frappe.new_doc('Journal Entry')
		jv.voucher_type = 'Journal Entry'
		jv.company = self.company
		jv.posting_date = self.purchase_date
		jv.user_remark = 'Fixed Asset Purchase'


		td1 = jv.append("accounts");	
		from erpnext.accounts.party import get_party_account
		td1.account = get_party_account(self.company, self.purchased_from, 'Supplier')
		td1.party = self.purchased_from
		td1.party_type = 'Supplier'
		td1.set("debit", self.gross_purchase_value)

		td2 = jv.append("accounts")
		td2.account = self.fixed_asset_account
		td2.set('credit', self.gross_purchase_value)

		return jv.insert()

	def do_year_closing(fiscal_year):
		finyrfrom, finyrto = get_fiscal_year(fiscal_year)[1:]
		ps = frappe.db.sql("""select * from `tabFixed Asset Account` where is_sold=false or (is_sold=true and (select count(*) from `tabFixed Asset Sale` sale where sale.fixed_asset_account=led.fixed_asset_name and docstatus=1 and sale.posting_date>=%s and sale.posting_date<=%s)>0)""", (finyrfrom, finyrto), as_dict=True)

		jv = frappe.new_doc('Journal Entry')
		jv.voucher_type = 'Journal Entry'
		jv.company = self.company
		jv.posting_date = self.purchase_date
		jv.user_remark = 'Fixed Asset Closing Entry'

		global total_depr
		total_depr = 0
		for assets in ps:
			fixed_asset_name = assets.fixed_asset_name
			total_depreciation_for_year = get_total_depr_for(fiscal_year, fixed_asset_name)
			total_depr = total_depr + total_depreciation_for_year
			td1 = jv.append("accounts")
			td1.account = assets.fixed_asset_account
			td1.set('debit', total_depreciation_for_year)
			td1.against_fixed_asset = fixed_asset_name
	
		td2 = jv.append("accounts")
		td2.account = frappe.db.get_value("Account", {"account_name": "Accumulated Depreciation"})
		td2.set('credit', float(total_depr))

		return jv.insert()

	def get_total_depr_for(fiscal_year,fa_name):
	    finyrfrom, finyrto = get_fiscal_year(fiscal_year)[1:]
	    day_before_start = finyrfrom - timedelta (days=1)
	    TOTAL_DAYS_IN_YEAR = 365

	    ps = frappe.db.sql("""select led.*,ifnull((select sum(sale.asset_purchase_cost) from `tabFixed Asset Sale` sale where sale.fixed_asset_account=led.fixed_asset_name and sale.docstatus=1  and sale.posting_date>=%s and sale.posting_date<=%s),0) as total_sale_value
           from `tabFixed Asset Account` led where fixed_asset_name=%s""", (finyrfrom,finyrto), as_dict=True)

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

	    return flt(depronopening+depronpurchases,2)
		

@frappe.whitelist()
def get_purchase_cost(account):
   val = frappe.get_doc("Fixed Asset Account", account).gross_purchase_value
   return val

