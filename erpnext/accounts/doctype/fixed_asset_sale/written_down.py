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
	day_before_start = finyrfrom - timedelta (days=1)
	TOTAL_DAYS_IN_YEAR = 365;
	
	ps = frappe.db.sql("""select led.* from `tabFixed Asset Account` led where is_sold=false and led.fixed_asset_name=%s""", (fa_account), as_dict=True)

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


	        global depronopening # Depreciation to be Provided in on the Opening Cost for this Fiscal Yr.
	        depronopening = float(0)

	        factor = 1
		if opening_balance > 0:
	             factor = float(deprtilllastyr / opening_balance)

                days = getDateDiffDays(finyrfrom, saledate)
                depronopening = depronopening + (((saleamount - (saleamount * factor)) * rateofdepr / 100) * (days / TOTAL_DAYS_IN_YEAR))

	        global deprwrittenback
                deprwrittenback = depronopening + deprtilllastyr

	return flt(deprwrittenback,2)

@frappe.whitelist()
def assess_profit_or_loss(pc, ad, sa):
	print pc, ad, sa
	if float(pc) - float(ad) > float(sa):
		return "Loss"
	else:
		return "profit"
