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

def get_cwip_account(item_code, company):
	asset_category = frappe.db.get_value('Item', item_code, 'asset_category')
	cwip_account = frappe.db.get_value('Asset Category Account',
		{'parent': asset_category, 'company_name': company}, 'capital_work_in_progress_account')

	return cwip_account or None