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
		_("Asset Serial Number") + "::180",
		_("Item Code") + "::120",
		_("Item Name") + "::120",
		_("Asset Category") + "::120",
		_("Asset Parent Category") + "::140",
		_("Purchase Date") + "::120",
		_("Next Depreciation Date") + "::120",
		_("Gross Purchase Amount") + "::120",
		_("Opening Accumulated Depreciation") + "::120",
		_("book value") + "::120",
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
	li_list=frappe.db.sql("select * from `tabAsset` where docstatus = 1 ",as_dict=1)

	data = []
	for asset in li_list:
		depreciation_schedule=frappe.db.sql("select sum(depreciation_amount) from `tabDepreciation Schedule` where parent ='{0}' and journal_entry != null ".format(asset.name))
		item_name=frappe.db.sql("select item_name from `tabItem` where item_code ='{0}' ".format(asset.item_code))
		asset_parent_category=frappe.db.sql("select parent_asset_category from `tabAsset Category` where name ='{0}' ".format(asset.asset_category))
		book_value = (flt(asset.gross_purchase_amount)-flt(depreciation_schedule[0][0]))

		row = [
		asset.name,
		asset.asset_name,
		asset.item_code,
		item_name[0][0],
		asset.asset_category,
		asset_parent_category[0][0],
		asset.purchase_date,
		asset.next_depreciation_date,
		"{:,}".format(round(asset.gross_purchase_amount, 2)),
		asset.opening_accumulated_depreciation,
		"{:,}".format(round(book_value, 2)) ,
		]
		data.append(row)
	return data




