# -*- coding: utf-8 -*-
# Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, today

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_checks_for_pl_and_bs_accounts,
)


def post_depreciation_entries(date=None):
	# Return if automatic booking of asset depreciation is disabled
	if not cint(frappe.db.get_value("Accounts Settings", None, "book_asset_depreciation_entry_automatically")):
		return

	if not date:
		date = today()
	for asset in get_depreciable_assets(date):
		make_depreciation_entry(asset, date)
		frappe.db.commit()

def get_depreciable_assets(date):
	return frappe.db.sql_list("""select a.name
		from tabAsset a, `tabDepreciation Schedule` ds
		where a.name = ds.parent and a.docstatus=1 and ds.schedule_date<=%s and a.calculate_depreciation = 1
			and a.status in ('Submitted', 'Partially Depreciated')
			and ifnull(ds.journal_entry, '')=''""", date)

@frappe.whitelist()
def make_depreciation_entry(asset_name, date=None):
	frappe.has_permission('Journal Entry', throw=True)

	if not date:
		date = today()

	asset = frappe.get_doc("Asset", asset_name)
	fixed_asset_account, accumulated_depreciation_account, depreciation_expense_account = \
		get_depreciation_accounts(asset)

	depreciation_cost_center, depreciation_series = frappe.get_cached_value('Company',  asset.company,
		["depreciation_cost_center", "series_for_depreciation_entry"])

	depreciation_cost_center = asset.cost_center or depreciation_cost_center

	accounting_dimensions = get_checks_for_pl_and_bs_accounts()

	for d in asset.get("schedules"):
		if not d.journal_entry and getdate(d.schedule_date) <= getdate(date):
			je = frappe.new_doc("Journal Entry")
			je.voucher_type = "Depreciation Entry"
			je.naming_series = depreciation_series
			je.posting_date = d.schedule_date
			je.company = asset.company
			je.finance_book = d.finance_book
			je.remark = "Depreciation Entry against {0} worth {1}".format(asset_name, d.depreciation_amount)

			credit_entry = {
				"account": accumulated_depreciation_account,
				"credit_in_account_currency": d.depreciation_amount,
				"reference_type": "Asset",
				"reference_name": asset.name,
				"cost_center": depreciation_cost_center
			}

			debit_entry = {
				"account": depreciation_expense_account,
				"debit_in_account_currency": d.depreciation_amount,
				"reference_type": "Asset",
				"reference_name": asset.name,
				"cost_center": depreciation_cost_center
			}

			for dimension in accounting_dimensions:
				if (asset.get(dimension['fieldname']) or dimension.get('mandatory_for_bs')):
					credit_entry.update({
						dimension['fieldname']: asset.get(dimension['fieldname']) or dimension.get('default_dimension')
					})

				if (asset.get(dimension['fieldname']) or dimension.get('mandatory_for_pl')):
					debit_entry.update({
						dimension['fieldname']: asset.get(dimension['fieldname']) or dimension.get('default_dimension')
					})

			je.append("accounts", credit_entry)

			je.append("accounts", debit_entry)

			je.flags.ignore_permissions = True
			je.save()
			if not je.meta.get_workflow():
				je.submit()

			d.db_set("journal_entry", je.name)

			idx = cint(d.finance_book_id)
			finance_books = asset.get('finance_books')[idx - 1]
			finance_books.value_after_depreciation -= d.depreciation_amount
			finance_books.db_update()

	asset.set_status()

	return asset

def get_depreciation_accounts(asset):
	fixed_asset_account = accumulated_depreciation_account = depreciation_expense_account = None

	accounts = frappe.db.get_value("Asset Category Account",
		filters={'parent': asset.asset_category, 'company_name': asset.company},
		fieldname = ['fixed_asset_account', 'accumulated_depreciation_account',
			'depreciation_expense_account'], as_dict=1)

	if accounts:
		fixed_asset_account = accounts.fixed_asset_account
		accumulated_depreciation_account = accounts.accumulated_depreciation_account
		depreciation_expense_account = accounts.depreciation_expense_account

	if not accumulated_depreciation_account or not depreciation_expense_account:
		accounts = frappe.get_cached_value('Company',  asset.company,
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

	if asset.docstatus != 1:
		frappe.throw(_("Asset {0} must be submitted").format(asset.name))
	elif asset.status in ("Cancelled", "Sold", "Scrapped"):
		frappe.throw(_("Asset {0} cannot be scrapped, as it is already {1}").format(asset.name, asset.status))

	depreciation_series = frappe.get_cached_value('Company',  asset.company,  "series_for_depreciation_entry")

	je = frappe.new_doc("Journal Entry")
	je.voucher_type = "Journal Entry"
	je.naming_series = depreciation_series
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

	frappe.db.set_value("Asset", asset_name, "disposal_date", today())
	frappe.db.set_value("Asset", asset_name, "journal_entry_for_scrap", je.name)
	asset.set_status("Scrapped")

	frappe.msgprint(_("Asset scrapped via Journal Entry {0}").format(je.name))

@frappe.whitelist()
def restore_asset(asset_name):
	asset = frappe.get_doc("Asset", asset_name)

	je = asset.journal_entry_for_scrap

	asset.db_set("disposal_date", None)
	asset.db_set("journal_entry_for_scrap", None)

	frappe.get_doc("Journal Entry", je).cancel()

	asset.set_status()

def get_gl_entries_on_asset_regain(asset, selling_amount=0, finance_book=None):
	fixed_asset_account, asset, depreciation_cost_center, accumulated_depr_account, accumulated_depr_amount, disposal_account, value_after_depreciation = \
		get_asset_details(asset, finance_book)

	gl_entries = [
		{
			"account": fixed_asset_account,
			"debit_in_account_currency": asset.gross_purchase_amount,
			"debit": asset.gross_purchase_amount,
			"cost_center": depreciation_cost_center
		},
		{
			"account": accumulated_depr_account,
			"credit_in_account_currency": accumulated_depr_amount,
			"credit": accumulated_depr_amount,
			"cost_center": depreciation_cost_center
		}
	]

	profit_amount = abs(flt(value_after_depreciation)) - abs(flt(selling_amount))
	if profit_amount:
		get_profit_gl_entries(profit_amount, gl_entries, disposal_account, depreciation_cost_center)

	return gl_entries

def get_gl_entries_on_asset_disposal(asset, selling_amount=0, finance_book=None):
	fixed_asset_account, asset, depreciation_cost_center, accumulated_depr_account, accumulated_depr_amount, disposal_account, value_after_depreciation = \
		get_asset_details(asset, finance_book)

	gl_entries = [
		{
			"account": fixed_asset_account,
			"credit_in_account_currency": asset.gross_purchase_amount,
			"credit": asset.gross_purchase_amount,
			"cost_center": depreciation_cost_center
		},
		{
			"account": accumulated_depr_account,
			"debit_in_account_currency": accumulated_depr_amount,
			"debit": accumulated_depr_amount,
			"cost_center": depreciation_cost_center
		}
	]

	profit_amount = flt(selling_amount) - flt(value_after_depreciation)
	if profit_amount:
		get_profit_gl_entries(profit_amount, gl_entries, disposal_account, depreciation_cost_center)

	return gl_entries

def get_asset_details(asset, finance_book=None):
	fixed_asset_account, accumulated_depr_account, depr_expense_account = get_depreciation_accounts(asset)
	disposal_account, depreciation_cost_center = get_disposal_account_and_cost_center(asset.company)
	depreciation_cost_center = asset.cost_center or depreciation_cost_center

	idx = 1
	if finance_book:
		for d in asset.finance_books:
			if d.finance_book == finance_book:
				idx = d.idx
				break

	value_after_depreciation = (asset.finance_books[idx - 1].value_after_depreciation
		if asset.calculate_depreciation else asset.value_after_depreciation)
	accumulated_depr_amount = flt(asset.gross_purchase_amount) - flt(value_after_depreciation)

	return fixed_asset_account, asset, depreciation_cost_center, accumulated_depr_account, accumulated_depr_amount, disposal_account, value_after_depreciation

def get_profit_gl_entries(profit_amount, gl_entries, disposal_account, depreciation_cost_center):
	debit_or_credit = "debit" if profit_amount < 0 else "credit"
	gl_entries.append({
		"account": disposal_account,
		"cost_center": depreciation_cost_center,
		debit_or_credit: abs(profit_amount),
		debit_or_credit + "_in_account_currency": abs(profit_amount)
	})

@frappe.whitelist()
def get_disposal_account_and_cost_center(company):
	disposal_account, depreciation_cost_center = frappe.get_cached_value('Company',  company,
		["disposal_account", "depreciation_cost_center"])

	if not disposal_account:
		frappe.throw(_("Please set 'Gain/Loss Account on Asset Disposal' in Company {0}").format(company))
	if not depreciation_cost_center:
		frappe.throw(_("Please set 'Asset Depreciation Cost Center' in Company {0}").format(company))

	return disposal_account, depreciation_cost_center
