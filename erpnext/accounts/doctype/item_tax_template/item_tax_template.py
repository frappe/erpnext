# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import cstr


class ItemTaxTemplate(Document):
	def validate(self):
		self.validate_tax_accounts()

	def validate_tax_accounts(self):
		"""Check whether Tax Rate is not entered twice for same Tax Type"""
		check_list = []
		for d in self.get('taxes'):
			if not d.tax_type:
				continue

			account_type = frappe.db.get_value("Account", d.tax_type, "account_type")
			if account_type not in ['Tax', 'Chargeable', 'Income Account', 'Expense Account', 'Expenses Included In Valuation']:
				frappe.throw(_("Item Tax Row {0} must have account of type Tax or Income or Expense or Chargeable").format(
					d.idx))

			key = (d.tax_type, cstr(d.valid_from))
			if key in check_list:
				frappe.throw(_("Row #{0}: {1} entered twice in Item Tax").format(d.idx, d.tax_type))

			check_list.append(key)
