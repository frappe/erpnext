# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_months, cint, flt, get_last_day

from erpnext.assets.doctype.asset.asset import get_asset_shift_factors_map
from erpnext.assets.doctype.asset.depreciation import is_last_day_of_the_month


class AssetShiftAllocation(Document):
	def after_insert(self):
		self.fetch_and_set_depr_schedule()

	def validate(self):
		self.asset_doc = frappe.get_doc("Asset", self.asset)

		self.validate_invalid_shift_change()
		self.update_depr_schedule()

	def on_submit(self):
		self.update_asset_schedule()

	def fetch_and_set_depr_schedule(self):
		if len(self.asset_doc.finance_books) != 1:
			frappe.throw(_("Only assets with one finance book allowed in v14."))

		if not any(fb.get("shift_based") for fb in self.asset_doc.finance_books):
			frappe.throw(_("Asset {0} is not using shift based depreciation").format(self.asset))

		for schedule in self.asset_doc.get("schedules"):
			self.append(
				"depreciation_schedule",
				{
					"schedule_date": schedule.schedule_date,
					"depreciation_amount": schedule.depreciation_amount,
					"accumulated_depreciation_amount": schedule.accumulated_depreciation_amount,
					"journal_entry": schedule.journal_entry,
					"shift": schedule.shift,
					"depreciation_method": self.asset_doc.finance_books[0].depreciation_method,
					"finance_book": self.asset_doc.finance_books[0].finance_book,
					"finance_book_id": self.asset_doc.finance_books[0].idx,
				},
			)

		self.flags.ignore_validate = True
		self.save()

	def validate_invalid_shift_change(self):
		if not self.get("depreciation_schedule") or self.docstatus == 1:
			return

		for i, sch in enumerate(self.depreciation_schedule):
			if sch.journal_entry and self.asset_doc.schedules[i].shift != sch.shift:
				frappe.throw(
					_(
						"Row {0}: Shift cannot be changed since the depreciation has already been processed"
					).format(i)
				)

	def update_depr_schedule(self):
		if not self.get("depreciation_schedule") or self.docstatus == 1:
			return

		self.allocate_shift_diff_in_depr_schedule()

		temp_asset_doc = frappe.copy_doc(self.asset_doc)

		temp_asset_doc.flags.shift_allocation = True

		temp_asset_doc.schedules = []

		for schedule in self.depreciation_schedule:
			temp_asset_doc.append(
				"schedules",
				{
					"schedule_date": schedule.schedule_date,
					"depreciation_amount": schedule.depreciation_amount,
					"accumulated_depreciation_amount": schedule.accumulated_depreciation_amount,
					"journal_entry": schedule.journal_entry,
					"shift": schedule.shift,
					"depreciation_method": self.asset_doc.finance_books[0].depreciation_method,
					"finance_book": self.asset_doc.finance_books[0].finance_book,
					"finance_book_id": self.asset_doc.finance_books[0].idx,
				},
			)

		temp_asset_doc.prepare_depreciation_data()

		self.depreciation_schedule = []

		for schedule in temp_asset_doc.get("schedules"):
			self.append(
				"depreciation_schedule",
				{
					"schedule_date": schedule.schedule_date,
					"depreciation_amount": schedule.depreciation_amount,
					"accumulated_depreciation_amount": schedule.accumulated_depreciation_amount,
					"journal_entry": schedule.journal_entry,
					"shift": schedule.shift,
					"depreciation_method": self.asset_doc.finance_books[0].depreciation_method,
					"finance_book": self.asset_doc.finance_books[0].finance_book,
					"finance_book_id": self.asset_doc.finance_books[0].idx,
				},
			)

	def allocate_shift_diff_in_depr_schedule(self):
		asset_shift_factors_map = get_asset_shift_factors_map()
		reverse_asset_shift_factors_map = {
			asset_shift_factors_map[k]: k for k in asset_shift_factors_map
		}

		original_shift_factors_sum = sum(
			flt(asset_shift_factors_map.get(schedule.shift)) for schedule in self.asset_doc.schedules
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
						frappe.throw(_("Could not auto update shifts. Shift with shift factor {0} needed.")).format(
							shift_factor - diff
						)
		elif diff < 0:
			shift_factors = list(asset_shift_factors_map.values())
			desc_shift_factors = sorted(shift_factors, reverse=True)
			depr_schedule_len_diff = self.asset_doc.total_number_of_depreciations - len(
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
							cint(self.asset_doc.frequency_of_depreciation),
						)

						if is_last_day_of_the_month(self.depreciation_schedule[-1].schedule_date):
							schedule_date = get_last_day(schedule_date)

						self.append(
							"depreciation_schedule",
							{
								"schedule_date": schedule_date,
								"shift": reverse_asset_shift_factors_map.get(subsets_result[0][i]),
								"depreciation_method": self.asset_doc.finance_books[0].depreciation_method,
								"finance_book": self.asset_doc.finance_books[0].finance_book,
								"finance_book_id": self.asset_doc.finance_books[0].idx,
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
							frappe.throw(_("Could not auto update shifts. Shift with shift factor {0} needed.")).format(
								shift_factor + diff
							)

	def update_asset_schedule(self):
		self.asset_doc.flags.shift_allocation = True

		self.asset_doc.schedules = []

		for schedule in self.depreciation_schedule:
			self.asset_doc.append(
				"schedules",
				{
					"schedule_date": schedule.schedule_date,
					"depreciation_amount": schedule.depreciation_amount,
					"accumulated_depreciation_amount": schedule.accumulated_depreciation_amount,
					"journal_entry": schedule.journal_entry,
					"shift": schedule.shift,
					"depreciation_method": self.asset_doc.finance_books[0].depreciation_method,
					"finance_book": self.asset_doc.finance_books[0].finance_book,
					"finance_book_id": self.asset_doc.finance_books[0].idx,
				},
			)

		self.asset_doc.flags.ignore_validate_update_after_submit = True
		self.asset_doc.prepare_depreciation_data()
		self.asset_doc.save()


def find_subsets_with_sum(numbers, k, target_sum, current_subset, result):
	if k == 0 and target_sum == 0:
		result.append(current_subset.copy())
		return
	if k <= 0 or target_sum <= 0 or not numbers:
		return

	# Include the current number in the subset
	find_subsets_with_sum(
		numbers, k - 1, target_sum - numbers[0], current_subset + [numbers[0]], result
	)

	# Exclude the current number from the subset
	find_subsets_with_sum(numbers[1:], k, target_sum, current_subset, result)
