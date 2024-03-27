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
	get_temp_asset_depr_schedule_doc,
)


class AssetShiftAllocation(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.assets.doctype.depreciation_schedule.depreciation_schedule import (
			DepreciationSchedule,
		)

		amended_from: DF.Link | None
		asset: DF.Link
		depreciation_schedule: DF.Table[DepreciationSchedule]
		finance_book: DF.Link | None
		naming_series: DF.Literal["ACC-ASA-.YYYY.-"]
	# end: auto-generated types

	def after_insert(self):
		self.fetch_and_set_depr_schedule()

	def validate(self):
		self.asset_depr_schedule_doc = get_asset_depr_schedule_doc(self.asset, "Active", self.finance_book)

		self.validate_invalid_shift_change()
		self.update_depr_schedule()

	def on_submit(self):
		self.create_new_asset_depr_schedule()

	def fetch_and_set_depr_schedule(self):
		if self.asset_depr_schedule_doc:
			if self.asset_depr_schedule_doc.shift_based:
				for schedule in self.asset_depr_schedule_doc.get("depreciation_schedule"):
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

	def validate_invalid_shift_change(self):
		if not self.get("depreciation_schedule") or self.docstatus == 1:
			return

		for i, sch in enumerate(self.depreciation_schedule):
			if sch.journal_entry and self.asset_depr_schedule_doc.depreciation_schedule[i].shift != sch.shift:
				frappe.throw(
					_(
						"Row {0}: Shift cannot be changed since the depreciation has already been processed"
					).format(i)
				)

	def update_depr_schedule(self):
		if not self.get("depreciation_schedule") or self.docstatus == 1:
			return

		self.allocate_shift_diff_in_depr_schedule()

		asset_doc = frappe.get_doc("Asset", self.asset)
		fb_row = asset_doc.finance_books[self.asset_depr_schedule_doc.finance_book_id - 1]

		asset_doc.flags.shift_allocation = True

		temp_depr_schedule = get_temp_asset_depr_schedule_doc(
			asset_doc, fb_row, new_depr_schedule=self.depreciation_schedule
		).get("depreciation_schedule")

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

	def allocate_shift_diff_in_depr_schedule(self):
		asset_shift_factors_map = get_asset_shift_factors_map()
		reverse_asset_shift_factors_map = {asset_shift_factors_map[k]: k for k in asset_shift_factors_map}

		original_shift_factors_sum = sum(
			flt(asset_shift_factors_map.get(schedule.shift))
			for schedule in self.asset_depr_schedule_doc.depreciation_schedule
		)

		new_shift_factors_sum = sum(
			flt(asset_shift_factors_map.get(schedule.shift)) for schedule in self.depreciation_schedule
		)

		diff = new_shift_factors_sum - original_shift_factors_sum

		if diff > 0:
			for i, schedule in reversed(list(enumerate(self.depreciation_schedule))):
				if diff <= 0:
					break

				shift_factor = flt(asset_shift_factors_map.get(schedule.shift))

				if shift_factor <= diff:
					self.depreciation_schedule.pop()
					diff -= shift_factor
				else:
					try:
						self.depreciation_schedule[i].shift = reverse_asset_shift_factors_map.get(
							shift_factor - diff
						)
						diff = 0
					except Exception:
						frappe.throw(
							_("Could not auto update shifts. Shift with shift factor {0} needed.")
						).format(shift_factor - diff)
		elif diff < 0:
			shift_factors = list(asset_shift_factors_map.values())
			desc_shift_factors = sorted(shift_factors, reverse=True)
			depr_schedule_len_diff = self.asset_depr_schedule_doc.total_number_of_depreciations - len(
				self.depreciation_schedule
			)
			subsets_result = []

			if depr_schedule_len_diff > 0:
				num_rows_to_add = depr_schedule_len_diff

				while not subsets_result and num_rows_to_add > 0:
					find_subsets_with_sum(shift_factors, num_rows_to_add, abs(diff), [], subsets_result)
					if subsets_result:
						break
					num_rows_to_add -= 1

				if subsets_result:
					for i in range(num_rows_to_add):
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
								"shift": reverse_asset_shift_factors_map.get(subsets_result[0][i]),
							},
						)

			if depr_schedule_len_diff <= 0 or not subsets_result:
				for i, schedule in reversed(list(enumerate(self.depreciation_schedule))):
					diff = abs(diff)

					if diff <= 0:
						break

					shift_factor = flt(asset_shift_factors_map.get(schedule.shift))

					if shift_factor <= diff:
						for sf in desc_shift_factors:
							if sf - shift_factor <= diff:
								self.depreciation_schedule[i].shift = reverse_asset_shift_factors_map.get(sf)
								diff -= sf - shift_factor
								break
					else:
						try:
							self.depreciation_schedule[i].shift = reverse_asset_shift_factors_map.get(
								shift_factor + diff
							)
							diff = 0
						except Exception:
							frappe.throw(
								_("Could not auto update shifts. Shift with shift factor {0} needed.")
							).format(shift_factor + diff)

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


def find_subsets_with_sum(numbers, k, target_sum, current_subset, result):
	if k == 0 and target_sum == 0:
		result.append(current_subset.copy())
		return
	if k <= 0 or target_sum <= 0 or not numbers:
		return

	# Include the current number in the subset
	find_subsets_with_sum(numbers, k - 1, target_sum - numbers[0], [*current_subset, numbers[0]], result)

	# Exclude the current number from the subset
	find_subsets_with_sum(numbers[1:], k, target_sum, current_subset, result)
