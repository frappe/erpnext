from __future__ import unicode_literals
from __future__ import division
import frappe
from frappe import _
from frappe.utils import flt
from datetime import date, timedelta
from datetime import datetime
from erpnext.accounts.report.financial_statements import (get_period_list, get_columns, get_data)

def getDateDiffDays(d1, d2):
    return abs((d2 - d1).days)

@frappe.whitelist()
def calculateWrittenDownOn(fa_account, saledate, saleamount):
	

	saleamount = float(saleamount)
	saledate=datetime.strptime(saledate, "%Y-%m-%d").date()
	from erpnext.accounts.utils import get_fiscal_year	
	finyrfrom, finyrto =get_fiscal_year(saledate)[1:]
	print finyrfrom	
	day_before_start = finyrfrom - timedelta (days=1)
	TOTAL_DAYS_IN_YEAR = 365;
	
        ps = frappe.db.sql("""select led.*,ifnull((select sum(pur.gross_purchase_value) from `tabFixed Asset Account` pur where pur.fixed_asset_name=led.fixed_asset_name and pur.purchase_date>=%s and pur.purchase_date<=%s),0) as total_pur_value,
           ifnull((select sum(sale.asset_purchase_cost) from `tabFixed Asset Sale` sale where sale.fixed_asset_account=led.fixed_asset_name and sale.docstatus=1 and sale.posting_date>=%s and sale.posting_date<=%s),0) as total_sale_value
           from `tabFixed Asset Account` led where fixed_asset_name=%s""", (finyrfrom,finyrto,finyrfrom,finyrto,fa_account), as_dict=True)

	for assets in ps:
		fixed_asset_name = assets.fixed_asset_name
	        global deprtilllastyr
	        deprtilllastyr = 0
	        for accdepr in frappe.get_doc("Fixed Asset Account", fixed_asset_name).depreciation:
	           if get_fiscal_year(fiscal_year = accdepr.fiscal_year) == get_fiscal_year(date = day_before_start):
	               deprtilllastyr = accdepr.total_accumulated_depreciation
		opening_balance = abs(assets.gross_purchase_value)
		rateofdepr = abs(assets.depreciation_rate)
		totalpurchase = (assets.total_pur_value)
		totalsales = abs(assets.total_sale_value)
		factor = deprtilllastyr / opening_balance
		writtendown = 0
		if (totalsales == 0 and saleamount <= opening_balance) or (totalsales < opening_balance and (totalsales + saleamount) <= opening_balance):
			if saleamount == opening_balance:
				writtendown = deprtilllastyr
				calculateon = opening_balance - deprtilllastyr
				days = getDateDiffDays(finyrfrom, saledate)
				writtendown = writtendown + (calculateon * rateofdepr / 100) * (days / TOTAL_DAYS_IN_YEAR)
				return flt(writtendown,2)
			elif saleamount < opening_balance:
				writtendown = (saleamount * factor);
				calculateon = (saleamount - (saleamount * factor));
				days = getDateDiffDays(finyrfrom, saledate);
				writtendown = writtendown + (calculateon * rateofdepr / 100) * (days / TOTAL_DAYS_IN_YEAR);
				return flt(writtendown,2)
		elif opening_balance == 0 and saleamount <= totalpurchase:
			if saleamount < totalpurchase:
				calculatefor = totalpurchase - saleamount
				purchases_sql = frappe.db.sql("""select * from `tabFixed Asset Account` pur where pur.fixed_asset_name=%s and pur.purchase_date>=%s and pur.purchase_date<=%s""", (fixed_asset_name,finyrfrom,finyrto), as_dict=True)
				for purchases in purchases_sql:
					calculatefor = totalpurchase - saleamount
					purdate = purchases.posting_date
					if puramount <= calculatefor:
						days = getDateDiffDays(purdate, saledate)
						writtendown = writtendown + (puramount * rateofdepr / 100) * (days / TOTAL_DAYS_IN_YEAR)
					elif puramount > calculatefor:
						days = getDateDiffDays(purdate, saledate)
						writtendown = writtendown + (calculatefor * rateofdepr / 100) * (days / TOTAL_DAYS_IN_YEAR)
			elif saleamount == totalpurchase:
				purchases_sql = frappe.db.sql("""select * from `tabFixed Asset Account` pur where pur.fixed_asset_name=%s and pur.purchase_date>=%s and pur.purchase_date<=%s""", (fixed_asset_name,finyrfrom,finyrto), as_dict=True)
				for purchases in purchases_sql:
					puramount = purchases.gross_purchase_value
					days = getDateDiffDays(purdate, saledate)
					writtendown = written + ((puramount * rateofdepr / 100) * (days / TOTAL_DAYS_IN_YEAR))
			return flt(writtendown,2)
		elif (totalsales == 0 and saleamount <= (opening_balance + totalpurchase) and saleamount > opening_balance):
			calculateon = opening_balance - deprtilllastyr
			days = getDateDiffDays(finyrfrom, saledate)
			writtendown = writtendown + (calculateon * rateofdepr / 100) * (days / TOTAL_DAYS_IN_YEAR)
			if (saleamount == (opening_balance + totalpurchase)):
				purchases_sql = frappe.db.sql("""select * from `tabFixed Asset Account` pur where pur.fixed_asset_name=%s and pur.purchase_date>=%s and pur.purchase_date<=%s""", (fixed_asset_name,finyrfrom,finyrto), as_dict=True)
				for purchases in purchases_sql:
					puramount = purchases.gross_purchase_value
					purdate = purchases.posting_date
					days = getDateDiffDays(purdate, saledate)
					writtendown = writtendown + ((puramount * rateofdepr / 100) * (days / TOTAL_DAYS_IN_YEAR))
			elif (saleamount < (opening_balance + totalpurchase)):
				calculatefor = (opening_balance + totalpurchase) - saleamount
				purchases_sql = frappe.db.sql("""select * from `tabFixed Asset Account` pur where pur.fixed_asset_name=%s and pur.purchase_date>=%s and pur.purchase_date<=%s""", (fixed_asset_name,finyrfrom,finyrto), as_dict=True)
				for purchases in purchases_sql:
					puramount = purchases.gross_purchase_value
					purdate = purchases.posting_date
					if (puramount <= calculatefor):
						days = getDateDiffDays(purdate, saledate)
						writtendown = writtendown + (puramount * rateofdepr / 100) * (days / TOTAL_DAYS_IN_YEAR)
					elif (puramount > calculatefor):
						days = getDateDiffDays(purdate, saledate)
						writtendown = writtendown + (calculatefor * rateofdepr / 100) * (days / TOTAL_DAYS_IN_YEAR)
			return flt(writtendown,2)
	return -1

@frappe.whitelist()
def assess_profit_or_loss(pc, ad, sa):
	print pc, ad, sa
	if float(pc) - float(ad) > float(sa):
		return "Loss"
	else:
		return "profit"
