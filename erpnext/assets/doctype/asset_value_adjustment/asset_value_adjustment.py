# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, getdate, cint, date_diff
from erpnext.assets.doctype.asset.depreciation import get_depreciation_accounts
from frappe.model.document import Document

class AssetValueAdjustment(Document):
	def validate(self):
		self.set_difference_amount()
		self.set_current_asset_value()

	def on_submit(self):
		self.make_depreciation_entry()
		self.reschedule_depreciations(self.new_asset_value)

	def on_cancel(self):
		if self.journal_entry:
			frappe.throw(_("Cancel the journal entry {0} first").format(self.journal_entry))

		self.reschedule_depreciations(self.current_asset_value)

	def set_difference_amount(self):
		self.difference_amount = flt(self.current_asset_value - self.new_asset_value)

	def set_current_asset_value(self):
		if not self.current_asset_value and self.asset:
			self.current_asset_value = get_current_asset_value(self.asset, self.finance_book)

	def make_depreciation_entry(self):
		asset = frappe.get_doc("Asset", self.asset)
		fixed_asset_account, accumulated_depreciation_account, depreciation_expense_account = \
			get_depreciation_accounts(asset)

		depreciation_cost_center, depreciation_series = frappe.get_cached_value('Company',  asset.company, 
			["depreciation_cost_center", "series_for_depreciation_entry"])

		je = frappe.new_doc("Journal Entry")
		je.voucher_type = "Depreciation Entry"
		je.naming_series = depreciation_series
		je.posting_date = self.date
		je.company = self.company
		je.remark = "Depreciation Entry against {0} worth {1}".format(self.asset, self.difference_amount)

		je.append("accounts", {
			"account": accumulated_depreciation_account,
			"credit_in_account_currency": self.difference_amount,
			"cost_center": depreciation_cost_center or self.cost_center
		})

		je.append("accounts", {
			"account": depreciation_expense_account,
			"debit_in_account_currency": self.difference_amount,
			"cost_center": depreciation_cost_center or self.cost_center
		})

		je.flags.ignore_permissions = True
		je.submit()

		self.db_set("journal_entry", je.name)

	def reschedule_depreciations(self, asset_value):
		asset = frappe.get_doc('Asset', self.asset)

		for d in asset.finance_books:
			d.value_after_depreciation = asset_value

			if d.depreciation_method in ("Straight Line", "Manual"):
				end_date = max([s.schedule_date for s in asset.schedules if cint(s.finance_book_id) == d.idx])
				total_days = date_diff(end_date, self.date)
				rate_per_day = flt(d.value_after_depreciation) / flt(total_days)
				from_date = self.date
			else:
				no_of_depreciations = len([e.name for e in asset.schedules
					if (cint(s.finance_book_id) == d.idx and not e.journal_entry)])

			value_after_depreciation = d.value_after_depreciation
			for data in asset.schedules:
				if cint(data.finance_book_id) == d.idx and not data.journal_entry:
					if d.depreciation_method in ("Straight Line", "Manual"):
						days = date_diff(data.schedule_date, from_date)
						depreciation_amount = days * rate_per_day
						from_date = data.schedule_date
					else:
						depreciation_amount = asset.get_depreciation_amount(value_after_depreciation,
							no_of_depreciations, d)

					if depreciation_amount:
						value_after_depreciation -= flt(depreciation_amount)
						data.depreciation_amount = depreciation_amount

			d.db_update()

		asset.set_accumulated_depreciation(ignore_booked_entry=True)
		for asset_data in asset.schedules:
			if not asset_data.journal_entry:
				asset_data.db_update()

@frappe.whitelist()
def get_current_asset_value(asset, finance_book=None):
	cond = {'parent': asset, 'parenttype': 'Asset'}
	if finance_book:
		cond.update({'finance_book': finance_book})

	return frappe.db.get_value('Asset Finance Book', cond, 'value_after_depreciation')
