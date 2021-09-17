
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe.utils.make_random import get_random

from erpnext.assets.doctype.asset.asset import make_sales_invoice
from erpnext.assets.doctype.asset.depreciation import post_depreciation_entries, scrap_asset


def work():
	frappe.set_user(frappe.db.get_global('demo_accounts_user'))

	# Enable booking asset depreciation entry automatically
	frappe.db.set_value("Accounts Settings", None, "book_asset_depreciation_entry_automatically", 1)

	# post depreciation entries as on today
	post_depreciation_entries()

	# scrap a random asset
	frappe.db.set_value("Company", "Wind Power LLC", "disposal_account", "Gain/Loss on Asset Disposal - WPL")

	asset = get_random_asset()
	scrap_asset(asset.name)

	# Sell a random asset
	sell_an_asset()


def sell_an_asset():
	asset = get_random_asset()
	si = make_sales_invoice(asset.name, asset.item_code, "Wind Power LLC")
	si.customer = get_random("Customer")
	si.get("items")[0].rate = asset.value_after_depreciation * 0.8 \
		if asset.value_after_depreciation else asset.gross_purchase_amount * 0.9
	si.save()
	si.submit()


def get_random_asset():
	return frappe.db.sql(""" select name, item_code, value_after_depreciation, gross_purchase_amount
		from `tabAsset`
		where docstatus=1 and status not in ("Scrapped", "Sold") order by rand() limit 1""", as_dict=1)[0]
