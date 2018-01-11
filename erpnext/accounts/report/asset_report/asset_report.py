# encoding: utf-8
# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import formatdate, getdate, flt, add_days
from datetime import datetime
import datetime
from datetime import date
from dateutil.relativedelta import relativedelta


def execute(filters=None):
	columns, data = get_columns(filters), get_data(filters)
	return columns, data
	
def get_columns(filters):
	return [
		_("Name") + ":Link/Asset:120",
		_("Asset Serial Number") + "::200",
		_("Item Code") + "::120",
		_("Item Name") + "::120",
		_("Asset Category") + "::120",
		_("Asset Parent Category") + "::140",
		_("Purchase Date") + "::120",
		_("Next Depreciation Date") + "::120",
		_("Gross Purchase Amount") + "::120",
		_("Accumulated Depreciation") + "::120",
		_("book value") + "::120",
		_("Total Number of Depreciations") + "::120"
		]


def get_conditions(filters):
	conditions = ""

	if filters.get("company"): conditions += " and company=%(company)s"
	if filters.get("employee"): conditions += " and employee = %(employee)s"

	if filters.get("from_date"): conditions += " and date_of_joining>=%(from_date)s"
	if filters.get("to_date"): conditions += " and date_of_joining<=%(to_date)s"
	
	return conditions


def get_data(filters):
	# conditions = get_conditions(filters)
	li_list=frappe.db.sql("""select name, asset_name, item_code, asset_category, 
		purchase_date, next_depreciation_date, total_number_of_depreciations from `tabAsset`
		where docstatus = 1 order by asset_category""",as_dict=1)

	data=[]
	asset_categories=set()

	for asset in li_list:
		depreciation_schedule=frappe.db.sql("select sum(depreciation_amount) from `tabDepreciation Schedule` where parent ='{0}' and journal_entry is not null ".format(asset.name))
		item_name=frappe.db.sql("select item_name from `tabItem` where item_code ='{0}' ".format(asset.item_code))
		asset_parent_category=frappe.db.sql("select parent_asset_category from `tabAsset Category` where name ='{0}' ".format(asset.asset_category))
		book_value = (flt(asset.gross_purchase_amount)-flt(depreciation_schedule[0][0])) - flt(asset.expected_value_after_useful_life)
		accumulated_depreciation = flt(depreciation_schedule[0][0]) - flt(asset.expected_value_after_useful_life)
		asset_categories.add(asset.asset_category)

		row = [
		asset.name,
		asset.asset_name,
		asset.item_code,
		item_name[0][0],
		asset.asset_category,
		asset_parent_category[0][0],
		asset.purchase_date,
		asset.next_depreciation_date,
		"{:.2f}".format(flt(asset.gross_purchase_amount, precision=2)),
		"{:.2f}".format(flt(accumulated_depreciation, precision=2)),
		"{:.2f}".format(flt(book_value, precision=2)),
		"{:.2f}".format(flt(asset.total_number_of_depreciations, precision=2))
		]
		data.append(row)
	# totals = [item for asset_cat in asset_categories for items in data]

	"""Adding totals for each asset category assets
	list comprehension may adds complixity to this snippet- Ahmed Madi"""

	asset_categories = list(asset_categories)
	grand_totals_list=[""]*len(row)
	gpa_grand_total=0.0
	ad_grand_total=0.0
	bv_grand_total=0.0
	for asset_cat in asset_categories:

		asset_category_gpa_total=0.0
		asset_category_ad_total=0.0
		asset_category_bv_total=0.0
		totals_list=[""]*len(row)

		for items in data:	
			if asset_cat == items[4]:
				asset_category_gpa_total+=flt(items[8])
				asset_category_ad_total+=flt(items[9])
				asset_category_bv_total+=flt(items[10])
				idx=data.index(items)+1
		totals_list.insert(0,"<b>{0} Total</b>".format(asset_cat))
		totals_list.insert(8,"<b>{:.2f}</b>".format(asset_category_gpa_total)) 
		totals_list.insert(9,"<b>{:.2f}</b>".format(asset_category_ad_total)) 
		totals_list.insert(10,"<b>{:.2f}</b>".format(asset_category_bv_total))

		data.insert(idx,totals_list)

		gpa_grand_total+=asset_category_gpa_total
		ad_grand_total+=asset_category_ad_total
		bv_grand_total+=asset_category_bv_total

	grand_totals_list.insert(0,"<b>Grand Total</b>")
	grand_totals_list.insert(8,"<b>{:.2f}</b>".format(gpa_grand_total)) 
	grand_totals_list.insert(9,"<b>{:.2f}</b>".format(ad_grand_total)) 
	grand_totals_list.insert(10,"<b>{:.2f}</b>".format(bv_grand_total))

	data.append([])
	data.append(grand_totals_list)

	return data



