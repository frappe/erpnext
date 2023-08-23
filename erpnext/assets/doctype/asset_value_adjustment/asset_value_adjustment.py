# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, formatdate, getdate

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_checks_for_pl_and_bs_accounts,
)
from erpnext.assets.doctype.asset.asset import get_asset_value_after_depreciation
from erpnext.assets.doctype.asset.depreciation import get_depreciation_accounts


class AssetValueAdjustment(Document):
	def validate(self):
		self.validate_date()
		self.set_current_asset_value()
		self.set_difference_amount()

	def on_submit(self):
		self.make_depreciation_entry()
		self.update_asset(self.new_asset_value)

	def on_cancel(self):
		self.update_asset(self.current_asset_value)

	def validate_date(self):
		asset_purchase_date = frappe.db.get_value("Asset", self.asset, "purchase_date")
		if getdate(self.date) < getdate(asset_purchase_date):
			frappe.throw(
				_("Asset Value Adjustment cannot be posted before Asset's purchase date <b>{0}</b>.").format(
					formatdate(asset_purchase_date)
				),
				title=_("Incorrect Date"),
			)

	def set_difference_amount(self):
		self.difference_amount = flt(self.current_asset_value - self.new_asset_value)

	def set_current_asset_value(self):
		if not self.current_asset_value and self.asset:
			self.current_asset_value = get_asset_value_after_depreciation(self.asset, self.finance_book)

	def make_depreciation_entry(self):
		asset = frappe.get_doc("Asset", self.asset)
		(
			_,
			accumulated_depreciation_account,
			depreciation_expense_account,
		) = get_depreciation_accounts(asset.asset_category, asset.company)

		depreciation_cost_center, depreciation_series = frappe.get_cached_value(
			"Company", asset.company, ["depreciation_cost_center", "series_for_depreciation_entry"]
		)

		je = frappe.new_doc("Journal Entry")
		je.voucher_type = "Depreciation Entry"
		je.naming_series = depreciation_series
		je.posting_date = self.date
		je.company = self.company
		je.remark = "Depreciation Entry against {0} worth {1}".format(self.asset, self.difference_amount)
		je.finance_book = self.finance_book

		credit_entry = {
			"account": accumulated_depreciation_account,
			"credit_in_account_currency": self.difference_amount,
			"cost_center": depreciation_cost_center or self.cost_center,
			"reference_type": "Asset",
			"reference_name": asset.name,
		}

		debit_entry = {
			"account": depreciation_expense_account,
			"debit_in_account_currency": self.difference_amount,
			"cost_center": depreciation_cost_center or self.cost_center,
			"reference_type": "Asset",
			"reference_name": asset.name,
		}

		accounting_dimensions = get_checks_for_pl_and_bs_accounts()

		for dimension in accounting_dimensions:
			if dimension.get("mandatory_for_bs"):
				credit_entry.update(
					{
						dimension["fieldname"]: self.get(dimension["fieldname"])
						or dimension.get("default_dimension")
					}
				)

			if dimension.get("mandatory_for_pl"):
				debit_entry.update(
					{
						dimension["fieldname"]: self.get(dimension["fieldname"])
						or dimension.get("default_dimension")
					}
				)

		je.append("accounts", credit_entry)
		je.append("accounts", debit_entry)

		je.flags.ignore_permissions = True
		je.submit()

		self.db_set("journal_entry", je.name)

	def update_asset(self, asset_value):
		asset = frappe.get_doc("Asset", self.asset)

		asset.flags.decrease_in_asset_value_due_to_value_adjustment = True

		asset.prepare_depreciation_data(value_after_depreciation=asset_value, ignore_booked_entry=True)
		asset.flags.ignore_validate_update_after_submit = True
		asset.save()
