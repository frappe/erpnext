# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr, flt, formatdate, get_link_to_form, getdate

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_checks_for_pl_and_bs_accounts,
)
from erpnext.assets.doctype.asset.asset import get_asset_value_after_depreciation
from erpnext.assets.doctype.asset.depreciation import get_depreciation_accounts
from erpnext.assets.doctype.asset_activity.asset_activity import add_asset_activity
from erpnext.assets.doctype.asset_depreciation_schedule.asset_depreciation_schedule import (
	reschedule_depreciation,
)


class AssetValueAdjustment(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		asset: DF.Link
		asset_category: DF.ReadOnly | None
		company: DF.Link | None
		cost_center: DF.Link | None
		current_asset_value: DF.Currency
		date: DF.Date
		difference_account: DF.Link
		difference_amount: DF.Currency
		finance_book: DF.Link | None
		journal_entry: DF.Link | None
		new_asset_value: DF.Currency
	# end: auto-generated types

	def validate(self):
		self.validate_date()
		self.set_current_asset_value()
		self.set_difference_amount()

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
		self.difference_amount = flt(self.new_asset_value - self.current_asset_value)

	def set_current_asset_value(self):
		if not self.current_asset_value and self.asset:
			self.current_asset_value = get_asset_value_after_depreciation(self.asset, self.finance_book)

	def on_submit(self):
		self.make_asset_revaluation_entry()
		self.update_asset()
		add_asset_activity(
			self.asset,
			_("Asset's value adjusted after submission of Asset Value Adjustment {0}").format(
				get_link_to_form("Asset Value Adjustment", self.name)
			),
		)

	def on_cancel(self):
		frappe.get_doc("Journal Entry", self.journal_entry).cancel()
		self.update_asset()
		add_asset_activity(
			self.asset,
			_("Asset's value adjusted after cancellation of Asset Value Adjustment {0}").format(
				get_link_to_form("Asset Value Adjustment", self.name)
			),
		)

	def make_asset_revaluation_entry(self):
		asset = frappe.get_doc("Asset", self.asset)
		(
			fixed_asset_account,
			accumulated_depreciation_account,
			depreciation_expense_account,
		) = get_depreciation_accounts(asset.asset_category, asset.company)

		depreciation_cost_center, depreciation_series = frappe.get_cached_value(
			"Company", asset.company, ["depreciation_cost_center", "series_for_depreciation_entry"]
		)

		je = frappe.new_doc("Journal Entry")
		je.voucher_type = "Journal Entry"
		je.naming_series = depreciation_series
		je.posting_date = self.date
		je.company = self.company
		je.remark = f"Revaluation Entry against {self.asset} worth {self.difference_amount}"
		je.finance_book = self.finance_book

		entry_template = {
			"cost_center": self.cost_center or depreciation_cost_center,
			"reference_type": "Asset",
			"reference_name": asset.name,
		}

		if self.difference_amount < 0:
			credit_entry, debit_entry = self.get_entry_for_asset_value_decrease(
				fixed_asset_account, entry_template
			)
		elif self.difference_amount > 0:
			credit_entry, debit_entry = self.get_entry_for_asset_value_increase(
				fixed_asset_account, entry_template
			)

		self.update_accounting_dimensions(credit_entry, debit_entry)

		je.append("accounts", credit_entry)
		je.append("accounts", debit_entry)

		je.flags.ignore_permissions = True
		je.submit()

		self.db_set("journal_entry", je.name)

	def get_entry_for_asset_value_decrease(self, fixed_asset_account, entry_template):
		credit_entry = {
			"account": fixed_asset_account,
			"credit_in_account_currency": -self.difference_amount,
			**entry_template,
		}
		debit_entry = {
			"account": self.difference_account,
			"debit_in_account_currency": -self.difference_amount,
			**entry_template,
		}

		return credit_entry, debit_entry

	def get_entry_for_asset_value_increase(self, fixed_asset_account, entry_template):
		credit_entry = {
			"account": self.difference_account,
			"credit_in_account_currency": self.difference_amount,
			**entry_template,
		}
		debit_entry = {
			"account": fixed_asset_account,
			"debit_in_account_currency": self.difference_amount,
			**entry_template,
		}

		return credit_entry, debit_entry

	def update_accounting_dimensions(self, credit_entry, debit_entry):
		accounting_dimensions = get_checks_for_pl_and_bs_accounts()

		for dimension in accounting_dimensions:
			dimension_value = self.get(dimension["fieldname"]) or dimension.get("default_dimension")
			if dimension.get("mandatory_for_bs"):
				credit_entry.update({dimension["fieldname"]: dimension_value})

			if dimension.get("mandatory_for_pl"):
				debit_entry.update({dimension["fieldname"]: dimension_value})

	def update_asset(self):
		asset = self.update_asset_value_after_depreciation()
		note = self.get_adjustment_note()
		reschedule_depreciation(asset, note)
		asset.set_status()

	def update_asset_value_after_depreciation(self):
		difference_amount = self.difference_amount if self.docstatus == 1 else -1 * self.difference_amount

		asset = frappe.get_doc("Asset", self.asset)
		if asset.calculate_depreciation:
			for row in asset.finance_books:
				if cstr(row.finance_book) == cstr(self.finance_book):
					salvage_value_adjustment = (
						self.get_adjusted_salvage_value_amount(row, difference_amount) or 0
					)
					row.expected_value_after_useful_life += salvage_value_adjustment
					row.value_after_depreciation = row.value_after_depreciation + flt(difference_amount)
					row.db_update()

		asset.value_after_depreciation += flt(difference_amount)
		asset.db_update()
		return asset

	def get_adjusted_salvage_value_amount(self, row, difference_amount):
		if row.expected_value_after_useful_life:
			salvage_value_adjustment = (difference_amount * row.salvage_value_percentage) / 100
			return flt(salvage_value_adjustment if self.docstatus == 1 else -1 * salvage_value_adjustment)

	def get_adjustment_note(self):
		if self.docstatus == 1:
			notes = _(
				"This schedule was created when Asset {0} was adjusted through Asset Value Adjustment {1}."
			).format(
				get_link_to_form("Asset", self.asset),
				get_link_to_form(self.get("doctype"), self.get("name")),
			)
		elif self.docstatus == 2:
			notes = _(
				"This schedule was created when Asset {0}'s Asset Value Adjustment {1} was cancelled."
			).format(
				get_link_to_form("Asset", self.asset),
				get_link_to_form(self.get("doctype"), self.get("name")),
			)

		return notes


@frappe.whitelist()
def get_value_of_accounting_dimensions(asset_name):
	dimension_fields = [*frappe.get_list("Accounting Dimension", pluck="fieldname"), "cost_center"]
	return frappe.db.get_value("Asset", asset_name, fieldname=dimension_fields, as_dict=True)
