# -*- coding: utf-8 -*-
# Copyright, (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _, scrub
from frappe.model.document import Document


class AccountingDimensionFilter(Document):
	def validate(self):
		self.validate_applicable_accounts()

	def validate_applicable_accounts(self):
		accounts = frappe.db.sql(
			"""
				SELECT a.applicable_on_account as account
				FROM `tabApplicable On Account` a, `tabAccounting Dimension Filter` d
				WHERE d.name = a.parent
				and d.name != %s
				and d.accounting_dimension = %s
			""", (self.name, self.accounting_dimension), as_dict=1)

		account_list = [d.account for d in accounts]

		for account in self.get('accounts'):
			if account.applicable_on_account in account_list:
				frappe.throw(_("Row {0}: {1} account already applied for Accounting Dimension {2}").format(
					account.idx, frappe.bold(account.applicable_on_account), frappe.bold(self.accounting_dimension)))

def get_dimension_filter_map():
	filters = frappe.db.sql("""
		SELECT
			a.applicable_on_account, d.dimension_value, p.accounting_dimension,
			p.allow_or_restrict, a.is_mandatory
		FROM
			`tabApplicable On Account` a, `tabAllowed Dimension` d,
			`tabAccounting Dimension Filter` p
		WHERE
			p.name = a.parent
			AND p.disabled = 0
			AND p.name = d.parent
	""", as_dict=1)

	dimension_filter_map = {}

	for f in filters:
		f.fieldname = scrub(f.accounting_dimension)

		build_map(dimension_filter_map, f.fieldname, f.applicable_on_account, f.dimension_value,
			f.allow_or_restrict, f.is_mandatory)

	return dimension_filter_map

def build_map(map_object, dimension, account, filter_value, allow_or_restrict, is_mandatory):
	map_object.setdefault((dimension, account), {
		'allowed_dimensions': [],
		'is_mandatory': is_mandatory,
		'allow_or_restrict': allow_or_restrict
	})
	map_object[(dimension, account)]['allowed_dimensions'].append(filter_value)
