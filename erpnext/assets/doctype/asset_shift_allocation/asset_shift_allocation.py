# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import (
	add_months,
	cint,
	flt,
	get_last_day,
	get_link_to_form,
	is_last_day_of_the_month,
)

from erpnext.assets.doctype.asset_activity.asset_activity import add_asset_activity
from erpnext.assets.doctype.asset_depreciation_schedule.asset_depreciation_schedule import (
	get_asset_depr_schedule_doc,
	get_asset_shift_factors_map,
	get_temp_depr_schedule_doc,
)


class AssetShiftAllocation(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.assets.doctype.depreciation_schedule.depreciation_schedule import DepreciationSchedule

		amended_from: DF.Link | None
		asset: DF.Link
		depreciation_schedule: DF.Table[DepreciationSchedule]
		finance_book: DF.Link | None
		naming_series: DF.Literal["ACC-ASA-.YYYY.-"]
	# end: auto-generated types

	def validate(self):
		self.asset_depr_schedule_doc = get_asset_depr_schedule_doc(self.asset, "Active", self.finance_book)
		if self.get("depreciation_schedule") and self.docstatus == 0:
			self.validate_invalid_shift_change()
			self.update_depr_schedule()

	def after_insert(self):
		self.fetch_and_set_depr_schedule()

	def on_submit(self):
		self.create_new_asset_depr_schedule()

	def validate_invalid_shift_change(self):
		for i, sch in enumerate(self.depreciation_schedule):
			if sch.journal_entry and self.asset_depr_schedule_doc.depreciation_schedule[i].shift != sch.shift:
				frappe.throw(
					_(
						"Row {0}: Shift cannot be changed since the depreciation has already been processed"
					).format(i)
				)

	def update_depr_schedule(self):
		self.adjust_depr_shifts()

		asset_doc = frappe.get_doc("Asset", self.asset)
		fb_row = self.get_finance_book_row(asset_doc)

		temp_depr_schedule_doc = get_temp_depr_schedule_doc(
			asset_doc, fb_row, updated_depr_schedule=self.depreciation_schedule
		)

		# Update the depreciation schedule with the new shifts
		self.depreciation_schedule = []
		self.modify_depr_schedule(temp_depr_schedule_doc.get("depreciation_schedule"))

	def adjust_depr_shifts(self):
		"""
		Adjust the shifts in the depreciation schedule based on the new shifts
		"""
		shift_factors_map = get_asset_shift_factors_map()
		reverse_shift_factors_map = {v: k for k, v in shift_factors_map.items()}
		factor_diff = self.calculate_shift_factor_diff(shift_factors_map)

		# Case 1: Reduce shifts if there is an excess factor
		if factor_diff > 0:
			self.reduce_depr_shifts(factor_diff, shift_factors_map, reverse_shift_factors_map)

		# Case 2: Add shifts if there is a missing factor
		elif factor_diff < 0:
			self.add_depr_shifts(factor_diff, shift_factors_map, reverse_shift_factors_map)

	def calculate_shift_factor_diff(self, shift_factors_map):
		original_shift_sum = sum(
			shift_factors_map.get(schedule.shift, 0)
			for schedule in self.asset_depr_schedule_doc.depreciation_schedule
		)
		new_shift_sum = sum(
			shift_factors_map.get(schedule.shift, 0) for schedule in self.depreciation_schedule
		)
		return new_shift_sum - original_shift_sum

	def reduce_depr_shifts(self, factor_diff, shift_factors_map, reverse_shift_factors_map):
		for i, schedule in reversed(list(enumerate(self.depreciation_schedule))):
			if factor_diff <= 0:
				break

			current_factor = shift_factors_map.get(schedule.shift, 0)
			if current_factor <= factor_diff:
				self.depreciation_schedule.pop(i)
				factor_diff -= current_factor
			else:
				new_factor = current_factor - factor_diff
				self.depreciation_schedule[i].shift = reverse_shift_factors_map.get(new_factor)
				factor_diff = 0

	def add_depr_shifts(self, factor_diff, shift_factors_map, reverse_shift_factors_map):
		factor_diff = abs(factor_diff)
		shift_factors = sorted(shift_factors_map.values(), reverse=True)

		while factor_diff > 0:
			for factor in shift_factors:
				if factor <= factor_diff:
					self.add_schedule_row(factor, reverse_shift_factors_map)
					factor_diff -= factor
					break
			else:
				frappe.throw(
					_("Could not find a suitable shift to match the difference: {0}").format(factor_diff)
				)

	def add_schedule_row(self, factor, reverse_shift_factors_map):
		schedule_date = add_months(
			self.depreciation_schedule[-1].schedule_date,
			cint(self.asset_depr_schedule_doc.frequency_of_depreciation),
		)
		if is_last_day_of_the_month(self.depreciation_schedule[-1].schedule_date):
			schedule_date = get_last_day(schedule_date)

		self.append(
			"depreciation_schedule",
			{
				"schedule_date": schedule_date,
				"shift": reverse_shift_factors_map.get(factor),
			},
		)

	def get_finance_book_row(self, asset_doc):
		idx = 0
		for d in asset_doc.get("finance_books"):
			if d.finance_book == self.finance_book:
				idx = d.idx
				break

		return asset_doc.get("finance_books")[idx - 1]

	def modify_depr_schedule(self, temp_depr_schedule):
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

	def fetch_and_set_depr_schedule(self):
		if self.asset_depr_schedule_doc:
			if self.asset_depr_schedule_doc.shift_based:
				self.modify_depr_schedule(self.asset_depr_schedule_doc.depreciation_schedule)

				self.flags.ignore_validate = True
				self.save()
			else:
				frappe.throw(
					_(
						"Asset Depreciation Schedule for Asset {0} and Finance Book {1} is not using shift based depreciation"
					).format(self.asset, self.finance_book)
				)
		else:
			frappe.throw(
				_("Asset Depreciation Schedule not found for Asset {0} and Finance Book {1}").format(
					self.asset, self.finance_book
				)
			)

	def create_new_asset_depr_schedule(self):
		new_asset_depr_schedule_doc = frappe.copy_doc(self.asset_depr_schedule_doc)

		new_asset_depr_schedule_doc.depreciation_schedule = []

		for schedule in self.depreciation_schedule:
			new_asset_depr_schedule_doc.append(
				"depreciation_schedule",
				{
					"schedule_date": schedule.schedule_date,
					"depreciation_amount": schedule.depreciation_amount,
					"accumulated_depreciation_amount": schedule.accumulated_depreciation_amount,
					"journal_entry": schedule.journal_entry,
					"shift": schedule.shift,
				},
			)

		notes = _(
			"This schedule was created when Asset {0}'s shifts were adjusted through Asset Shift Allocation {1}."
		).format(
			get_link_to_form("Asset", self.asset),
			get_link_to_form(self.doctype, self.name),
		)

		new_asset_depr_schedule_doc.notes = notes

		self.asset_depr_schedule_doc.flags.should_not_cancel_depreciation_entries = True
		self.asset_depr_schedule_doc.cancel()

		new_asset_depr_schedule_doc.submit()

		add_asset_activity(
			self.asset,
			_("Asset's depreciation schedule updated after Asset Shift Allocation {0}").format(
				get_link_to_form(self.doctype, self.name)
			),
		)
