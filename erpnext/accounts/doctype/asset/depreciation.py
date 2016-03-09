# -*- coding: utf-8 -*-
# Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, today, getdate

def post_depreciation_entries(date=None):
	if not date:
		date = today()
	for asset in get_depreciable_assets(date):
		make_depreciation_entry(asset, date)
	
def get_depreciable_assets(date):
	return frappe.db.sql_list("""select a.name
		from tabAsset a, `tabDepreciation Schedule` ds
		where a.name = ds.parent and a.docstatus=1 and ds.schedule_date<=%s 
			and a.status = 'Available' and ifnull(ds.journal_entry, '')=''""", date)

def make_depreciation_entry(asset_name, date=None):
	if not date:
		date = today()
	
	asset = frappe.get_doc("Asset", asset_name)
	fixed_asset_account, accumulated_depreciation_account, depreciation_expense_account = \
		get_depreciation_accounts(asset)
	
	for d in asset.get("schedules"):
		if not d.journal_entry and getdate(d.schedule_date) <= getdate(date):
			je = frappe.new_doc("Journal Entry")
			je.voucher_type = "Depreciation Entry"
			je.posting_date = d.schedule_date
			je.company = asset.company
			je.remark = "Depreciation Entry against {0} worth {1}".format(asset_name, d.depreciation_amount)
	
			je.append("accounts", {
				"account": accumulated_depreciation_account,
				"credit_in_account_currency": d.depreciation_amount,
				"reference_type": "Asset",
				"reference_name": asset.name
			})
	
			je.append("accounts", {
				"account": depreciation_expense_account,
				"debit_in_account_currency": d.depreciation_amount,
				"reference_type": "Asset",
				"reference_name": asset.name
			})
	
			je.flags.ignore_permissions = True
			je.submit()
	
			d.db_set("journal_entry", je.name)
			asset.current_value -= d.depreciation_amount
			frappe.db.set_value("Asset", asset_name, "current_value", asset.current_value)			
	
def get_depreciation_accounts(asset):
	accounts = frappe.db.sql("""select fixed_asset_account, accumulated_depreciation_account, 
			depreciation_expense_account from `tabAsset Category Account`
			where parent=%s and company=%s""", (asset.asset_category, asset.company), as_dict=1)[0]
	
	fixed_asset_account = accounts.fixed_asset_account
	accumulated_depreciation_account = accounts.accumulated_depreciation_account
	depreciation_expense_account = accounts.depreciation_expense_account
	
	if not accumulated_depreciation_account or not depreciation_expense_account:
		accounts = frappe.db.get_value("Company", asset.company, 
			["accumulated_depreciation_account", "depreciation_expense_account"])
		
		if not accumulated_depreciation_account:
			accumulated_depreciation_account = accounts[0]
		if not depreciation_expense_account:
			depreciation_expense_account = accounts[1]
			
	if not fixed_asset_account or not accumulated_depreciation_account or not depreciation_expense_account:
		frappe.throw(_("Please set Depreciation related Accounts in Asset Category {0} or Company {1}")
			.format(asset.asset_category, asset.company))
			
	return fixed_asset_account, accumulated_depreciation_account, depreciation_expense_account
	
@frappe.whitelist()
def scrap_asset(asset_name):
	asset = frappe.get_doc("Asset", asset_name)
	
	if asset.docstatus != 1 or asset.status != 'Available':
		frappe.throw(_("Asset {0} must be submitted and available").format(asset.name))

	je = frappe.new_doc("Journal Entry")
	je.voucher_type = "Journal Entry"
	je.posting_date = today()
	je.company = asset.company
	je.remark = "Scrap Entry for asset {0}".format(asset_name)
	
	for entry in get_gl_entries_on_asset_disposal(asset):
		entry.update({
			"reference_type": "Asset",
			"reference_name": asset_name
		})
		je.append("accounts", entry)
	
	je.flags.ignore_permissions = True
	je.submit()
	
	frappe.db.set_value("Asset", asset_name, "status", "Scrapped")
	
@frappe.whitelist()
def get_gl_entries_on_asset_disposal(asset, selling_amount=0):
	fixed_asset_account, accumulated_depr_account, depr_expense_account = get_depreciation_accounts(asset)
	disposal_account, disposal_cost_center = get_disposal_account_and_cost_center(asset.company)
	accumulated_depr_amount = flt(asset.gross_purchase_amount) - flt(asset.current_value)
	
	gl_entries = [
		{
			"account": fixed_asset_account,
			"credit_in_account_currency": asset.gross_purchase_amount,
			"credit": asset.gross_purchase_amount
		}, 
		{
			"account": accumulated_depr_account,
			"debit_in_account_currency": accumulated_depr_amount,
			"debit": accumulated_depr_amount
		}
	]
	
	profit_amount = flt(selling_amount) - flt(asset.current_value)
	if flt(asset.current_value) and profit_amount:
		debit_or_credit = "debit" if profit_amount < 0 else "credit"
		gl_entries.append({
			"account": disposal_account,
			"cost_center": disposal_cost_center,
			debit_or_credit: abs(profit_amount),
			debit_or_credit + "_in_account_currency": abs(profit_amount)
		})
	
	return gl_entries
	
def get_disposal_account_and_cost_center(company):
	disposal_account, disposal_cost_center = frappe.db.get_value("Company", company, 
		["disposal_account", "disposal_cost_center"])
	if not disposal_account or not disposal_cost_center:
		frappe.throw(_("Please set 'Asset Disposal Account' and 'Asset Disposal Cost Center' in Company {0}").format(company))
	return disposal_account, disposal_cost_center