# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Deferred revenue/expense accounting validations."""

import frappe
from frappe import _
from frappe.utils import getdate

DEFERRED_ACCOUNT_FIELD = {
	"Sales Invoice": "deferred_revenue_account",
	"Purchase Invoice": "deferred_expense_account",
}


class DeferredAccountingService:
	def __init__(self, doc):
		self.doc = doc

	def validate_income_expense_account(self) -> None:
		account_field = DEFERRED_ACCOUNT_FIELD.get(self.doc.doctype)

		for item in self.doc.get("items"):
			if not self._is_deferred(item) or item.get(account_field):
				continue

			default_account = frappe.get_cached_value("Company", self.doc.company, "default_" + account_field)
			if not default_account:
				frappe.throw(
					_(
						"Row #{0}: Please update deferred revenue/expense account in item row or default account in company master"
					).format(item.idx)
				)
			item.set(account_field, default_account)

	def validate_start_and_end_date(self) -> None:
		for item in self.doc.items:
			if not self._is_deferred(item):
				continue

			if not (item.service_start_date and item.service_end_date):
				frappe.throw(
					_("Row #{0}: Service Start and End Date is required for deferred accounting").format(
						item.idx
					)
				)
			elif getdate(item.service_start_date) > getdate(item.service_end_date):
				frappe.throw(
					_("Row #{0}: Service Start Date cannot be greater than Service End Date").format(item.idx)
				)
			elif getdate(self.doc.posting_date) > getdate(item.service_end_date):
				frappe.throw(
					_("Row #{0}: Service End Date cannot be before Invoice Posting Date").format(item.idx)
				)

	def _is_deferred(self, item) -> bool:
		return bool(item.get("enable_deferred_revenue") or item.get("enable_deferred_expense"))
