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
from erpnext.assets.doctype.asset.depreciation import (
	get_depreciation_accounts,
	get_last_depreciation_date,
)
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
		self.validate_asset_not_disposed()
		self.validate_date()
		self.validate_new_asset_value()
		self.validate_finance_book()
		self.set_current_asset_value()
		self.set_difference_amount()
		self.validate_difference_amount()

	def before_cancel(self):
		self.validate_asset_not_disposed()

	def validate_asset_not_disposed(self):
		status, disposal_date = frappe.db.get_value("Asset", self.asset, ["status", "disposal_date"])
		if disposal_date or status in ("Sold", "Scrapped", "Capitalized"):
			frappe.throw(
				_("Asset {0} is disposed, its value cannot be adjusted").format(
					get_link_to_form("Asset", self.asset)
				)
			)

	def validate_date(self):
		asset_purchase_date = frappe.db.get_value("Asset", self.asset, "purchase_date")
		if getdate(self.date) < getdate(asset_purchase_date):
			frappe.throw(
				_("Asset Value Adjustment cannot be posted before Asset's purchase date <b>{0}</b>.").format(
					formatdate(asset_purchase_date)
				),
				title=_("Incorrect Date"),
			)

		last_depreciation_date = get_last_depreciation_date(self.asset, self.finance_book)
		if last_depreciation_date and getdate(self.date) < last_depreciation_date:
			frappe.throw(
				_(
					"Asset Value Adjustment cannot be posted before the last depreciation entry dated {0}"
				).format(formatdate(last_depreciation_date)),
				title=_("Incorrect Date"),
			)

	def validate_new_asset_value(self):
		if flt(self.new_asset_value) < 0:
			frappe.throw(_("New Asset Value cannot be negative"))

	def validate_finance_book(self):
		if not self.finance_book or not frappe.db.get_value("Asset", self.asset, "calculate_depreciation"):
			return

		if not frappe.db.exists(
			"Asset Finance Book",
			{"parent": self.asset, "parenttype": "Asset", "finance_book": self.finance_book},
		):
			frappe.throw(
				_("Finance Book {0} is not set on Asset {1}").format(
					frappe.bold(self.finance_book), get_link_to_form("Asset", self.asset)
				)
			)

	def validate_difference_amount(self):
		if not self.difference_amount:
			frappe.throw(_("New Asset Value is the same as the current asset value"))

	def set_difference_amount(self):
		self.difference_amount = flt(self.new_asset_value - self.current_asset_value)

	def set_current_asset_value(self):
		if self.asset:
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
		self.cancel_asset_revaluation_entry()
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
			value = self.get(dimension["fieldname"])
			# Dimension defaults and mandatory flags are set per company; explicit values always apply
			is_own_company = dimension.get("company") == self.company

			if value or (is_own_company and dimension.get("mandatory_for_bs")):
				credit_entry[dimension["fieldname"]] = value or dimension.get("default_dimension")

			if value or (is_own_company and dimension.get("mandatory_for_pl")):
				debit_entry[dimension["fieldname"]] = value or dimension.get("default_dimension")

	def cancel_asset_revaluation_entry(self):
		if not self.journal_entry:
			return

		revaluation_entry = frappe.get_doc("Journal Entry", self.journal_entry)
		if revaluation_entry.docstatus == 1:
			# Ignore permissions to match Journal Entry submission behavior
			revaluation_entry.flags.ignore_permissions = True
			revaluation_entry.flags.via_asset_value_adjustment = True
			revaluation_entry.cancel()

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
					salvage_value_adjustment = self.get_adjusted_salvage_value_amount(row, difference_amount)
					row.expected_value_after_useful_life += salvage_value_adjustment
					row.value_after_depreciation = row.value_after_depreciation + flt(difference_amount)
					row.db_update()

		asset.value_after_depreciation += flt(difference_amount)
		asset.db_update()
		return asset

	def get_adjusted_salvage_value_amount(self, row, difference_amount):
		return flt((difference_amount * row.salvage_value_percentage) / 100)

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
def get_value_of_accounting_dimensions(asset_name: str):
	dimension_fields = [*frappe.get_list("Accounting Dimension", pluck="fieldname"), "cost_center"]
	return frappe.db.get_value("Asset", asset_name, fieldname=dimension_fields, as_dict=True)
