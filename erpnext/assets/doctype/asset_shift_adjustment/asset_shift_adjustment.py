# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from erpnext.assets.doctype.asset_depreciation_schedule.asset_depreciation_schedule import (
	get_asset_depr_schedule_doc,
	get_asset_shift_factor_name_map,
	get_temp_asset_depr_schedule_doc,
)


class AssetShiftAdjustment(Document):
	def validate(self):
		self.create_depr_schedule()
		self.validate_depr_schedule()
		self.update_depr_schedule()

	def create_depr_schedule(self):
		if self.depreciation_schedule:
			return

		asset_depr_schedule_doc = get_asset_depr_schedule_doc(self.asset, "Active", self.finance_book)

		if asset_depr_schedule_doc:
			if asset_depr_schedule_doc.depreciation_method == "Shift":
				for schedule in asset_depr_schedule_doc.get("depreciation_schedule"):
					self.append(
						"depreciation_schedule",
						{
							"schedule_date": schedule.schedule_date,
							"depreciation_amount": schedule.depreciation_amount,
							"accumulated_depreciation_amount": schedule.accumulated_depreciation_amount,
							"journal_entry": schedule.journal_entry,
							"shift": schedule.shift,
						},
					)
			else:
				frappe.throw(
					_(
						"Asset Depreciation Schedule for Asset {0} and Finance Book {1} is not using shift method"
					).format(self.asset, self.finance_book)
				)
		else:
			frappe.throw(
				_("Asset Depreciation Schedule not found for Asset {0} and Finance Book {1}").format(
					self.asset, self.finance_book
				)
			)

	def validate_depr_schedule(self):
		if self.get("__islocal"):
			return

		self.asset_depr_schedule_doc = get_asset_depr_schedule_doc(
			self.asset, "Active", self.finance_book
		)

		for i, sch in enumerate(self.depreciation_schedule):
			if (
				sch.journal_entry and self.asset_depr_schedule_doc.depreciation_schedule[i].shift != sch.shift
			):
				frappe.throw(
					_(
						"Row {0}: Shift type cannot be changed since the depreciation has already been processed"
					).format(i)
				)

		self.validate_shift_factors_sum(self.depreciation_schedule)

	def update_depr_schedule(self):
		if self.get("__islocal"):
			return

		asset_doc = frappe.get_doc("Asset", self.asset)
		fb_row = asset_doc.finance_books[self.asset_depr_schedule_doc.finance_book_id - 1]

		temp_depr_schedule = get_temp_asset_depr_schedule_doc(
			asset_doc, fb_row, new_depr_schedule=self.depreciation_schedule, shift_adjustment=True
		).get("depreciation_schedule")

		if temp_depr_schedule:
			self.validate_shift_factors_sum(temp_depr_schedule)

			self.depreciation_schedule = []

			for schedule in temp_depr_schedule:
				self.append(
					"depreciation_schedule",
					{
						"schedule_date": schedule.schedule_date,
						"depreciation_amount": schedule.depreciation_amount,
						"accumulated_depreciation_amount": schedule.accumulated_depreciation_amount,
						"journal_entry": schedule.journal_entry,
						"shift": schedule.shift,
					},
				)
		else:
			frappe.throw(_("Updation of shifts failed"))

	def validate_shift_factors_sum(self, new_depr_schedule):
		asset_shift_factor_name_map = get_asset_shift_factor_name_map()

		shift_factors_sum = sum(
			flt(self.asset_depr_schedule_doc.get(asset_shift_factor_name_map.get(schedule.shift)))
			for schedule in self.asset_depr_schedule_doc.depreciation_schedule
		)

		new_shift_factors_sum = sum(
			flt(self.asset_depr_schedule_doc.get(asset_shift_factor_name_map.get(schedule.shift)))
			for schedule in new_depr_schedule
		)

		if new_shift_factors_sum != shift_factors_sum:
			inequality = "lesser" if new_shift_factors_sum < shift_factors_sum else "greater"

			frappe.throw(
				_("Sum of all shift factors ({0}) cannot be {1} than the original sum ({2})").format(
					new_shift_factors_sum, inequality, shift_factors_sum
				)
			)
