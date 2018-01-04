# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
#~ from erpnext.accounts.doctype.asset.depreciation import make_depreciation_entry_bulk
from frappe.utils import flt, today, getdate

class AssetsSetting(Document):
	def make_depreciation_entry_bulk(self):
		self.last_journal_entry = make_depreciation_entry_bulk_manage(self.scrape_date)
		return self.last_journal_entry.name

def make_depreciation_entry_bulk_manage(date=None):
	frappe.has_permission('Journal Entry', throw=True)
	
	if not date:
		date = today()
		
	depreciation_schedule=frappe.get_all("Depreciation Schedule",['*'],filters={"schedule_date":date ,"journal_entry":None})
	je = frappe.new_doc("Journal Entry")
	je.voucher_type = "Depreciation Entry"
	je.posting_date = date
	je.company = frappe.db.get_value("Global Defaults", None, "default_company")
	
	for ds in depreciation_schedule:
		print("Asst", ds.parent)
		asset = frappe.get_doc("Asset", ds.parent)
		fixed_asset_account, accumulated_depreciation_account, depreciation_expense_account = \
			get_depreciation_accounts(asset)

		for d in asset.get("schedules"):
			if not d.journal_entry and getdate(d.schedule_date) == getdate(date) and asset.freeze ==0:
				

				je.append("accounts", {
					"account": accumulated_depreciation_account,
					"credit_in_account_currency": d.depreciation_amount,
					"reference_type": "Asset",
					"reference_name": asset.name,
					"cost_center": asset.depreciation_cost_center,
					"description":"Depreciation Entry against {0} worth {1}".format(ds.parent, d.depreciation_amount)		
				})

				je.append("accounts", {
					"account": depreciation_expense_account,
					"debit_in_account_currency": d.depreciation_amount,
					"reference_type": "Asset",
					"reference_name": asset.name,
					"cost_center": asset.depreciation_cost_center,
					"description":"Depreciation Entry against {0} worth {1}".format(ds.parent, d.depreciation_amount)
				})

		je.flags.ignore_permissions = True
		je.save()
		
	for ds in depreciation_schedule:
		asset = frappe.get_doc("Asset", ds.parent)
		if asset.freeze ==0 :
			for d in asset.get("schedules"):
				if not d.journal_entry and getdate(d.schedule_date) == getdate(date) and asset.freeze ==0:
					d.db_set("journal_entry", je.name)
					asset.value_after_depreciation -= d.depreciation_amount
					asset.db_set("value_after_depreciation", asset.value_after_depreciation)
					asset.set_status()

	return je


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


@frappe.whitelist(allow_guest=True)
def get_scrapped_assets(sc_date,settings):
	import datetime
	import time
	from datetime import datetime
	from datetime import timedelta
	import dateutil.parser
	dep=[]
	schedules=frappe.get_all("Depreciation Schedule",['*'],filters={"schedule_date":sc_date,"journal_entry":None})
	if schedules:
		for l in schedules:
			if not l.journal_entry:
				dep.append({
					'asset_name':l.parent,
					'depreciation_amount':l.depreciation_amount,
					'accumulated_depreciation_amount':l.accumulated_depreciation_amount,
					'journal_entry':l.journal_entry,
					})
	return dep
	
