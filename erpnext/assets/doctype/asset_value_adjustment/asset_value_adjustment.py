# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, formatdate, get_link_to_form, getdate

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_checks_for_pl_and_bs_accounts,
)
from erpnext.assets.doctype.asset.asset import get_asset_value_after_depreciation
from erpnext.assets.doctype.asset.depreciation import get_depreciation_accounts
from erpnext.assets.doctype.asset_activity.asset_activity import add_asset_activity
from erpnext.assets.doctype.asset_depreciation_schedule.asset_depreciation_schedule import (
	make_new_active_asset_depr_schedules_and_cancel_current_ones,
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
		difference_amount: DF.Currency
		finance_book: DF.Link | None
		impairment_loss_account: DF.Link | None
		journal_entry: DF.Link | None
		new_asset_value: DF.Currency
		revaluation_surplus_account: DF.Link | None
	# end: auto-generated types

	def validate(self):
		self.validate_date()
		self.set_current_asset_value()
		self.set_difference_amount()

	def on_submit(self):
		self.make_gl_entries()
		self.update_asset(self.new_asset_value)
		add_asset_activity(
			self.asset,
			_("Asset's value adjusted after submission of Asset Value Adjustment {0}").format(
				get_link_to_form("Asset Value Adjustment", self.name)
			),
		)

	def on_cancel(self):
		self.update_asset(self.current_asset_value)
		add_asset_activity(
			self.asset,
			_("Asset's value adjusted after cancellation of Asset Value Adjustment {0}").format(
				get_link_to_form("Asset Value Adjustment", self.name)
			),
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

	def set_difference_amount(self):
		self.difference_amount = flt(self.new_asset_value - self.current_asset_value)

	def set_current_asset_value(self):
		if not self.current_asset_value and self.asset:
			self.current_asset_value = get_asset_value_after_depreciation(self.asset, self.finance_book)

	def make_gl_entries(self):
		asset = frappe.get_doc("Asset", self.asset)

		debit_account, credit_account = self.get_debit_and_credit_accounts(
			asset.asset_category, asset.company
		)

		depreciation_cost_center, depreciation_series = frappe.get_cached_value(
			"Company", asset.company, ["depreciation_cost_center", "series_for_depreciation_entry"]
		)

		je = frappe.new_doc("Journal Entry")
		if self.difference_amount < 0:
			je.voucher_type = "Depreciation Entry"
		je.naming_series = depreciation_series
		je.posting_date = self.date
		je.company = self.company
		je.remark = "Accounting Entry against {0} worth {1}".format(self.asset, self.difference_amount)
		je.finance_book = self.finance_book

		debit_entry = {
			"account": debit_account,
			"debit_in_account_currency": abs(self.difference_amount),
			"cost_center": depreciation_cost_center or self.cost_center,
			"reference_type": "Asset",
			"reference_name": self.asset,
		}

		credit_entry = {
			"account": credit_account,
			"credit_in_account_currency": abs(self.difference_amount),
			"cost_center": depreciation_cost_center or self.cost_center,
			"reference_type": "Asset",
			"reference_name": self.asset,
		}

		self.update_accounting_dimensions(debit_entry, credit_entry)

		je.append("accounts", credit_entry)
		je.append("accounts", debit_entry)

		je.flags.ignore_permissions = True
		je.submit()

		self.db_set("journal_entry", je.name)

	def get_debit_and_credit_accounts(self, asset_category, company):
		(
			fixed_asset_account,
			accumulated_depreciation_account,
			_,
		) = get_depreciation_accounts(asset_category, company)

		if self.difference_amount > 0:
			debit_account = fixed_asset_account
			credit_account = self.revaluation_surplus_account
		else:
			debit_account = self.impairment_loss_account
			credit_account = accumulated_depreciation_account

		return debit_account, credit_account

	def update_accounting_dimensions(self, debit_entry, credit_entry):
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

	def update_asset(self, asset_value):
		asset = frappe.get_doc("Asset", self.asset)

		if not asset.calculate_depreciation:
			asset.value_after_depreciation = asset_value
			asset.save()
			return

		asset.flags.decrease_in_asset_value_due_to_value_adjustment = True

		if self.docstatus == 1:
			notes = _(
				"This schedule was created when Asset {0} was adjusted through Asset Value Adjustment {1}."
			).format(
				get_link_to_form("Asset", asset.name),
				get_link_to_form(self.get("doctype"), self.get("name")),
			)
		elif self.docstatus == 2:
			notes = _(
				"This schedule was created when Asset {0}'s Asset Value Adjustment {1} was cancelled."
			).format(
				get_link_to_form("Asset", asset.name),
				get_link_to_form(self.get("doctype"), self.get("name")),
			)

		make_new_active_asset_depr_schedules_and_cancel_current_ones(
			asset, notes, value_after_depreciation=asset_value, ignore_booked_entry=True
		)
		asset.flags.ignore_validate_update_after_submit = True
		asset.save()
