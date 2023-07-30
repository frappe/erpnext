# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import date_diff, flt, formatdate, get_link_to_form, getdate

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_checks_for_pl_and_bs_accounts,
)
from erpnext.assets.doctype.asset.asset import get_asset_value_after_depreciation
from erpnext.assets.doctype.asset.depreciation import get_depreciation_accounts
from erpnext.assets.doctype.asset_activity.asset_activity import add_asset_activity
from erpnext.assets.doctype.asset_depreciation_schedule.asset_depreciation_schedule import (
	get_asset_depr_schedule_doc,
	get_depreciation_amount,
)


class AssetValueAdjustment(Document):
	def validate(self):
		self.validate_date()
		self.set_current_asset_value()
		self.set_difference_amount()

	def on_submit(self):
		self.make_depreciation_entry()
		self.reschedule_depreciations(self.new_asset_value)
		add_asset_activity(
			self.asset,
			_("Asset's value adjusted after submission of Asset Value Adjustment {0}").format(
				get_link_to_form("Asset Value Adjustment", self.name)
			),
		)

	def on_cancel(self):
		self.reschedule_depreciations(self.current_asset_value)
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
		self.difference_amount = flt(self.current_asset_value - self.new_asset_value)

	def set_current_asset_value(self):
		if not self.current_asset_value and self.asset:
			self.current_asset_value = get_asset_value_after_depreciation(self.asset, self.finance_book)

	def make_depreciation_entry(self):
		asset = frappe.get_doc("Asset", self.asset)
		(
			fixed_asset_account,
			accumulated_depreciation_account,
			depreciation_expense_account,
		) = get_depreciation_accounts(asset)

		depreciation_cost_center, depreciation_series = frappe.get_cached_value(
			"Company", asset.company, ["depreciation_cost_center", "series_for_depreciation_entry"]
		)

		je = frappe.new_doc("Journal Entry")
		je.voucher_type = "Depreciation Entry"
		je.naming_series = depreciation_series
		je.posting_date = self.date
		je.company = self.company
		je.remark = _("Depreciation Entry against {0} worth {1}").format(
			self.asset, self.difference_amount
		)
		je.finance_book = self.finance_book

		credit_entry = {
			"account": accumulated_depreciation_account,
			"credit_in_account_currency": self.difference_amount,
			"cost_center": depreciation_cost_center or self.cost_center,
			"reference_type": "Asset",
			"reference_name": self.asset,
		}

		debit_entry = {
			"account": depreciation_expense_account,
			"debit_in_account_currency": self.difference_amount,
			"cost_center": depreciation_cost_center or self.cost_center,
			"reference_type": "Asset",
			"reference_name": self.asset,
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

	def reschedule_depreciations(self, asset_value):
		asset = frappe.get_doc("Asset", self.asset)
		country = frappe.get_value("Company", self.company, "country")

		for d in asset.finance_books:
			d.value_after_depreciation = asset_value

			current_asset_depr_schedule_doc = get_asset_depr_schedule_doc(
				asset.name, "Active", d.finance_book
			)

			new_asset_depr_schedule_doc = frappe.copy_doc(current_asset_depr_schedule_doc)
			new_asset_depr_schedule_doc.status = "Draft"
			new_asset_depr_schedule_doc.docstatus = 0

			current_asset_depr_schedule_doc.flags.should_not_cancel_depreciation_entries = True
			current_asset_depr_schedule_doc.cancel()

			if self.docstatus == 1:
				notes = _(
					"This schedule was created when Asset {0} was adjusted through Asset Value Adjustment {1}."
				).format(
					get_link_to_form(asset.doctype, asset.name),
					get_link_to_form(self.get("doctype"), self.get("name")),
				)
			elif self.docstatus == 2:
				notes = _(
					"This schedule was created when Asset {0}'s Asset Value Adjustment {1} was cancelled."
				).format(
					get_link_to_form(asset.doctype, asset.name),
					get_link_to_form(self.get("doctype"), self.get("name")),
				)
			new_asset_depr_schedule_doc.notes = notes

			new_asset_depr_schedule_doc.insert()

			depr_schedule = new_asset_depr_schedule_doc.get("depreciation_schedule")

			if d.depreciation_method in ("Straight Line", "Manual"):
				end_date = max(s.schedule_date for s in depr_schedule)
				total_days = date_diff(end_date, self.date)
				rate_per_day = flt(d.value_after_depreciation - d.expected_value_after_useful_life) / flt(
					total_days
				)
				from_date = self.date
			else:
				no_of_depreciations = len([s.name for s in depr_schedule if not s.journal_entry])

			value_after_depreciation = d.value_after_depreciation
			for data in depr_schedule:
				if not data.journal_entry:
					if d.depreciation_method in ("Straight Line", "Manual"):
						days = date_diff(data.schedule_date, from_date)
						depreciation_amount = days * rate_per_day
						from_date = data.schedule_date
					else:
						depreciation_amount = get_depreciation_amount(asset, value_after_depreciation, d)

					if depreciation_amount:
						value_after_depreciation -= flt(depreciation_amount)
						data.depreciation_amount = depreciation_amount

			d.db_update()

			new_asset_depr_schedule_doc.set_accumulated_depreciation(d, ignore_booked_entry=True)
			for asset_data in depr_schedule:
				if not asset_data.journal_entry:
					asset_data.db_update()

			new_asset_depr_schedule_doc.submit()
