# encoding: utf-8
# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import formatdate, getdate, flt, add_days
from datetime import datetime
import datetime
# import operator
import re
from datetime import date
from dateutil.relativedelta import relativedelta


def execute(filters=None):
	columns, data = get_columns(filters), get_data(filters)
	return columns, data

def get_columns(filters):
	return [
		_("Name") + ":Link/Asset:150",
		_("Asset Serial Number") + "::150",
		_("Item Code") + "::150",
		_("Item Name") + "::150",
		_("Asset Category") + "::150",
		_("Asset Parent Category") + "::150",
		_("Purchase Date") + ":Date:150",
		_("Next Depreciation Date") + ":Date:150",
		_("Gross Purchase Amount") + ":Currency:150",
		_("Accumulated Depreciation") + ":Currency:150",
		_("book value") + ":Currency:150",
		_("Total Number of Depreciations") + "::150"
		]


def get_conditions(filters):
	conditions = ""

	if filters.get("asset_category"): conditions += " and asset_category= '{0}' ".format(filters.get("asset_category"))

	# if filters.get("employee"): conditions += " and employee = %(employee)s"

	# if filters.get("from_date"): conditions += " and date_of_joining>=%(from_date)s"
	# if filters.get("to_date"): conditions += " and date_of_joining<=%(to_date)s"

	return conditions


def get_data(filters):
	conditions = get_conditions(filters)
	li_list=frappe.db.sql("""select name, asset_name, item_code, asset_category,
		purchase_date,expected_value_after_useful_life, gross_purchase_amount, next_depreciation_date, total_number_of_depreciations from `tabAsset`
		where docstatus = 1 {0} """.format(conditions),as_dict=1)

	data=[]
	asset_parent_categories=set()

	for asset in li_list:
		# depreciation_schedule=frappe.db.sql("select sum(depreciation_amount) from `tabDepreciation Schedule` where parent ='{0}' and journal_entry is not null ".format(asset.name))

		jes = frappe.db.sql("select journal_entry from `tabDepreciation Schedule` where parent ='{0}' and journal_entry is not null ".format(asset.name))

		ds_total = 0
		if jes:
			for je in jes:
				ds_total += frappe.db.sql("select credit from `tabGL Entry` where voucher_no='{0}' and against_voucher='{1}'".format(je[0], asset.name))[0][0]

		# frappe.throw(str(depreciation_schedule[0][0]) + "  " + str(ds_test))

		item_name=frappe.db.sql("select item_name from `tabItem` where item_code ='{0}' ".format(asset.item_code))
		asset_parent_category=frappe.db.sql("select parent_asset_category from `tabAsset Category` where name ='{0}' ".format(asset.asset_category))
		book_value = (flt(asset.gross_purchase_amount)-flt(ds_total))
		 # - flt(asset.expected_value_after_useful_life)
		accumulated_depreciation = flt(ds_total)
		asset_parent_categories.add(asset_parent_category[0][0])

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
		accumulated_depreciation,
		# "{:.2f}".format(flt(accumulated_depreciation, precision=2)),
		"{:.2f}".format(flt(book_value, precision=2)),
		"{:.2f}".format(flt(asset.total_number_of_depreciations, precision=2))
		]
		data.append(row)
	# totals = [item for asset_cat in asset_categories for items in data]

	"""Adding totals for each asset category assets
	list comprehension may adds complixity to this snippet- Ahmed Madi"""
	asset_parent_categories = list(asset_parent_categories)
	# frappe.throw(str(asset_parent_categories))
	
	if data:
		data.sort(key=lambda x: x[5])
		grand_totals_list=[""]*len(row)
		gpa_grand_total=0.0
		ad_grand_total=0.0
		bv_grand_total=0.0
		for asset_cat in asset_parent_categories:

			asset_category_gpa_total=0.0
			asset_category_ad_total=0.0
			asset_category_bv_total=0.0
			totals_list=[""]*len(row)

			for items in data:
				if asset_cat == items[5]:
					asset_category_gpa_total+=flt(re.findall("\d+\.\d+", items[8])[0])
					asset_category_ad_total+=items[9]
					asset_category_bv_total+=flt(re.findall("\d+\.\d+", items[10])[0])
					idx=data.index(items)+1
			totals_list.insert(0,asset_cat)
			totals_list.insert(8,asset_category_gpa_total)
			totals_list.insert(9,asset_category_ad_total)
			totals_list.insert(10,asset_category_bv_total)

			data.insert(idx,totals_list)

			gpa_grand_total+=asset_category_gpa_total
			ad_grand_total+=asset_category_ad_total
			bv_grand_total+=asset_category_bv_total

		grand_totals_list.insert(0,"<b>Grand Total</b>")
		grand_totals_list.insert(8,gpa_grand_total)
		grand_totals_list.insert(9,ad_grand_total)
		grand_totals_list.insert(10,bv_grand_total)

		data.append([])
		data.append(grand_totals_list)

	return data
