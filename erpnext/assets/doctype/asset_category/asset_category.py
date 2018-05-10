# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cint
from frappe.model.document import Document

class AssetCategory(Document):
	def validate(self):
		for field in ("total_number_of_depreciations", "frequency_of_depreciation"):
			if cint(self.get(field))<1:
				frappe.throw(_("{0} must be greater than 0").format(self.meta.get_label(field)), frappe.MandatoryError)

@frappe.whitelist()
def get_asset_category_account(asset, fieldname, account=None, asset_category = None, company = None):
	if not asset_category and company:
		if account:
			if frappe.db.get_value("Account", account, "account_type") != "Fixed Asset":
				account=None

		if not account:
			asset_category, company = frappe.db.get_value("Asset", asset, ["asset_category", "company"])

	account = frappe.db.get_value("Asset Category Account",
		filters={"parent": asset_category, "company_name": company}, fieldname=fieldname)

	return account