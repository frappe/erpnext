# -*- coding: utf-8 -*-
# Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, today


# Depreciate
#------------

def post_depreciation_entries(self):
	assets = get_depreciable_assets()
	for asset in assets:
		depreciate_asset(asset.asset_name, asset.depreciation_amount, asset.schedule_row)
	
def get_depreciable_assets(date=None):
	if not date:
		date = today()
		
	return frappe.db.sql("""
		select a.name as asset_name, ds.depreciation_amount, ds.name as schedule_row 
		from tabAsset a, `tabDepreciation Schedule` ds
		where
			a.name = ds.parent and ds.depreciation_date=%s 
			and a.status = 'Available' and ds.posted=0 and a.docstatus < 2""", date, as_dict=1)
		
def depreciate_asset(asset_name, depreciation_amount, schedule_row):
	asset = frappe.get_doc("Asset", asset_name)
	accumulated_depreciation_account, depreciation_expense_account = get_depreciation_accounts(asset)
	
	je = frappe.new_doc("Journal Entry")
	je.voucher_type = "Depreciation Entry"
	je.posting_date = today()
	je.company = asset.company
	je.remark = "Depreciation Entry against {0} worth {1}".format(asset_name, depreciation_amount)
	
	je.append("accounts", {
		"account": accumulated_depreciation_account,
		"credit_in_account_currency": depreciation_amount,
		"reference_type": "Asset",
		"reference_name": asset.name
	})
	
	je.append("accounts", {
		"account": depreciation_expense_account,
		"debit_in_account_currency": depreciation_amount,
		"reference_type": "Asset",
		"reference_name": asset.name
	})
	
	je.flags.ignore_permissions = True
	je.submit()
	
	frappe.db.sql("""update `tabDepreciation Schedule` 
		set posted=1, journal_entry=%s, modified=now(), modified_by=%s where name=%s""", 
		(je.name, frappe.session.user, schedule_row))

def get_depreciation_accounts(asset):
	accumulated_depreciation_account, depreciation_expense_account = frappe.db.get_value("Asset Category", 
		asset.asset_category, ["accumulated_depreciation_account", "depreciation_expense_account"])
		
	if not accumulated_depreciation_account or not depreciation_expense_account:
		accounts = frappe.db.get_value("Company", asset.company, 
			["accumulated_depreciation_account", "depreciation_expense_account"])
		if not accumulated_depreciation_account:
			accumulated_depreciation_account = accounts[0]
		if not depreciation_expense_account:
			depreciation_expense_account = accounts[1]
			
	if not accumulated_depreciation_account or not depreciation_expense_account:
		frappe.throw(_("Please set Depreciation related Accounts in Asset Category {0} or Company {1}")
			.format(asset.asset_category, asset.company))
			
	return accumulated_depreciation_account, depreciation_expense_account
	
# Scrap
#---------

@frappe.whitelist()
def scrap_asset(asset_name):
	asset = frappe.get_doc("Asset", asset_name)
	asset.status = "Scrapped"
	
	accumulated_depr_amount = frappe.db.sql("""select accumulated_depreciation_amount 
		from `tabDepreciation Schedule` 
		where parent=%s and posted=1
		order by depreciation_date desc limit 1""")
		
	accumulated_depr_amount = flt(accumulated_depr_amount[0][0]) if accumulated_depr_amount else 0
	
	net_value_after_depreciation = flt(asset.gross_value) - accumulated_depr_amount
	
	je = frappe.new_doc("Journal Entry")
	je.voucher_type = "Depreciation Entry"
	je.posting_date = today()
	je.company = asset.company
	je.remark = "Disposal Entry for asset {0}".format(asset_name)
	
	# je.append("accounts", {
	# 	"account": accumulated_depreciation_account,
	# 	"credit_in_account_currency": depreciation_amount,
	# 	"reference_type": "Asset",
	# 	"reference_name": asset.name
	# })
	#
	# je.append("accounts", {
	# 	"account": depreciation_expense_account,
	# 	"debit_in_account_currency": depreciation_amount,
	# 	"reference_type": "Asset",
	# 	"reference_name": asset.name
	# })
	
	je.flags.ignore_permissions = True
	je.submit()