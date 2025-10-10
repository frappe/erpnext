import frappe
from frappe import _
from frappe.utils import (
	add_days,
	add_months,
	add_years,
	cint,
	date_diff,
	flt,
	get_last_day,
	getdate,
	is_last_day_of_the_month,
	month_diff,
	nowdate,
)

import erpnext
from erpnext.accounts.utils import get_fiscal_year
from erpnext.assets.doctype.asset_depreciation_schedule.depreciation_methods import (
	StraightLineMethod,
	WDVMethod,
)


class DepreciationScheduleController(StraightLineMethod, WDVMethod):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

	def create_depreciation_schedule(self, fb_row=None, disposal_date=None):
		self.disposal_date = disposal_date
		self.asset_doc = frappe.get_doc("Asset", self.asset)

		self.get_finance_book_row(fb_row)
		self.fetch_asset_details()
		self.clear()
		self.create()
		self.set_accumulated_depreciation()

	def clear(self):
		self.first_non_depreciated_row_idx = 0
		num_of_depreciations_completed = 0
		depr_schedule = []

		self.schedules_before_clearing = self.get("depreciation_schedule")
		for schedule in self.get("depreciation_schedule"):
			if schedule.journal_entry:
				num_of_depreciations_completed += 1
				depr_schedule.append(schedule)
			else:
				self.first_non_depreciated_row_idx = num_of_depreciations_completed
				break

		self.depreciation_schedule = depr_schedule

	def create(self):
		self.initialize_variables()
		for row_idx in range(self.first_non_depreciated_row_idx, self.final_number_of_depreciations):
			# If depreciation is already completed (for double declining balance)
			if self.skip_row:
				continue

			self.has_fiscal_year_changed(row_idx)
			if self.fiscal_year_changed:
				self.yearly_opening_wdv = self.pending_depreciation_amount

			self.get_prev_depreciation_amount(row_idx)

			self.schedule_date = self.get_next_schedule_date(row_idx)

			self.depreciation_amount = self.get_depreciation_amount(row_idx)

			# if asset is being sold or scrapped
			if self.disposal_date and getdate(self.schedule_date) >= getdate(self.disposal_date):
				self.set_depreciation_amount_for_disposal(row_idx)
				break

			if row_idx == 0:
				self.set_depreciation_amount_for_first_row(row_idx)
			elif (
				self.has_pro_rata and row_idx == cint(self.final_number_of_depreciations) - 1
			):  # for the last row
				self.set_depreciation_amount_for_last_row(row_idx)

			self.depreciation_amount = flt(
				self.depreciation_amount, self.asset_doc.precision("net_purchase_amount")
			)
			if not self.depreciation_amount:
				break

			self.pending_depreciation_amount = flt(
				self.pending_depreciation_amount - self.depreciation_amount,
				self.asset_doc.precision("net_purchase_amount"),
			)

			self.adjust_depr_amount_for_salvage_value(row_idx)

			if flt(self.depreciation_amount, self.asset_doc.precision("net_purchase_amount")) > 0:
				self.add_depr_schedule_row(row_idx)

	def initialize_variables(self):
		self.pending_depreciation_amount = self.fb_row.value_after_depreciation
		self.should_get_last_day = is_last_day_of_the_month(self.fb_row.depreciation_start_date)
		self.skip_row = False
		self.depreciation_amount = 0
		self.prev_per_day_depr = True
		self.prev_depreciation_amount = 0
		self.current_fiscal_year_end_date = None
		self.yearly_opening_wdv = self.pending_depreciation_amount
		self.get_number_of_pending_months()
		self.get_final_number_of_depreciations()
		self.is_wdv_or_dd_non_yearly_pro_rata()
		self.get_total_pending_days_or_years()

	def get_final_number_of_depreciations(self):
		self.final_number_of_depreciations = cint(self.fb_row.total_number_of_depreciations) - cint(
			self.opening_number_of_booked_depreciations
		)

		self._check_is_pro_rata()
		if self.has_pro_rata:
			self.final_number_of_depreciations += 1

		self.set_final_number_of_depreciations_considering_increase_in_asset_life()

	def set_final_number_of_depreciations_considering_increase_in_asset_life(self):
		# final schedule date after increasing asset life
		self.final_schedule_date = add_months(
			self.asset_doc.available_for_use_date,
			(self.fb_row.total_number_of_depreciations * cint(self.fb_row.frequency_of_depreciation))
			+ cint(self.fb_row.increase_in_asset_life),
		)

		number_of_pending_depreciations = cint(self.fb_row.total_number_of_depreciations) - cint(
			self.asset_doc.opening_number_of_booked_depreciations
		)
		schedule_date = add_months(
			self.fb_row.depreciation_start_date,
			number_of_pending_depreciations * cint(self.fb_row.frequency_of_depreciation),
		)

		if self.final_schedule_date > getdate(schedule_date):
			months = month_diff(self.final_schedule_date, schedule_date)
			self.final_number_of_depreciations += months // cint(self.fb_row.frequency_of_depreciation) + 1

	def is_wdv_or_dd_non_yearly_pro_rata(self):
		if (
			self.fb_row.depreciation_method in ("Written Down Value", "Double Declining Balance")
			and cint(self.fb_row.frequency_of_depreciation) != 12
		):
			self._check_is_pro_rata()

	def _check_is_pro_rata(self):
		self.has_pro_rata = False

		# if not existing asset, from_date = available_for_use_date
		# otherwise, if opening_number_of_booked_depreciations = 2, available_for_use_date = 01/01/2020 and frequency_of_depreciation = 12
		# from_date = 01/01/2022
		if self.fb_row.depreciation_method in ("Straight Line", "Manual"):
			prev_depreciation_start_date = get_last_day(
				add_months(
					self.fb_row.depreciation_start_date,
					(self.fb_row.frequency_of_depreciation * -1)
					* self.asset_doc.opening_number_of_booked_depreciations,
				)
			)
			from_date = self.asset_doc.available_for_use_date
			days = date_diff(prev_depreciation_start_date, from_date) + 1
			total_days = self.get_total_days(prev_depreciation_start_date)
		else:
			from_date = self._get_modified_available_for_use_date_for_existing_assets()
			days = date_diff(self.fb_row.depreciation_start_date, from_date) + 1
			total_days = self.get_total_days(self.fb_row.depreciation_start_date)

		if days <= 0:
			frappe.throw(
				_(
					"""Error: This asset already has {0} depreciation periods booked.
					The `depreciation start` date must be at least {1} periods after the `available for use` date.
					Please correct the dates accordingly."""
				).format(
					self.asset_doc.opening_number_of_booked_depreciations,
					self.asset_doc.opening_number_of_booked_depreciations,
				)
			)
		if days < total_days:
			self.has_pro_rata = True
			self.has_wdv_or_dd_non_yearly_pro_rata = True

	def _get_modified_available_for_use_date_for_existing_assets(self):
		"""
		if Asset has opening booked depreciations = 3,
		frequency of depreciation = 3,
		available for use date = 17-07-2023,
		depreciation start date = 30-06-2024
		then from date should be 01-04-2024
		"""
		if self.asset_doc.opening_number_of_booked_depreciations > 0:
			from_date = add_days(
				add_months(self.fb_row.depreciation_start_date, (self.fb_row.frequency_of_depreciation * -1)),
				1,
			)
			return from_date
		else:
			return self.asset_doc.available_for_use_date

	def get_total_days(self, date):
		period_start_date = add_months(date, cint(self.fb_row.frequency_of_depreciation) * -1)
		if is_last_day_of_the_month(date):
			period_start_date = get_last_day(period_start_date)
		return date_diff(date, period_start_date)

	def _get_pro_rata_amt(self, from_date, to_date, original_schedule_date=None):
		days = date_diff(to_date, from_date) + 1
		months = month_diff(to_date, from_date)
		total_days = self.get_total_days(original_schedule_date or to_date)
		return (self.depreciation_amount * flt(days)) / flt(total_days), days, months

	def get_number_of_pending_months(self):
		total_months = cint(self.fb_row.total_number_of_depreciations) * cint(
			self.fb_row.frequency_of_depreciation
		) + cint(self.fb_row.increase_in_asset_life)
		last_depr_date = self.get_last_booked_depreciation_date()
		depr_booked_for_months = self.get_booked_depr_for_months_count(last_depr_date)

		self.pending_months = total_months - depr_booked_for_months

	def get_last_booked_depreciation_date(self):
		last_depr_date = None
		if self.first_non_depreciated_row_idx > 0:
			last_depr_date = self.depreciation_schedule[self.first_non_depreciated_row_idx - 1].schedule_date
		elif self.asset_doc.opening_number_of_booked_depreciations > 0:
			last_depr_date = add_months(
				self.fb_row.depreciation_start_date, -1 * self.fb_row.frequency_of_depreciation
			)
		return last_depr_date

	def get_booked_depr_for_months_count(self, last_depr_date):
		depr_booked_for_months = 0
		if last_depr_date:
			asset_used_for_months = self.fb_row.frequency_of_depreciation * (
				1 + self.asset_doc.opening_number_of_booked_depreciations
			)
			computed_available_for_use_date = add_days(
				add_months(self.fb_row.depreciation_start_date, -1 * asset_used_for_months), 1
			)
			if getdate(computed_available_for_use_date) < getdate(self.asset_doc.available_for_use_date):
				computed_available_for_use_date = self.asset_doc.available_for_use_date
			depr_booked_for_months = (date_diff(last_depr_date, computed_available_for_use_date) + 1) / (
				365 / 12
			)
		return depr_booked_for_months

	def get_total_pending_days_or_years(self):
		if cint(frappe.get_single_value("Accounts Settings", "calculate_depr_using_total_days")):
			last_depr_date = self.get_last_booked_depreciation_date()
			if last_depr_date:
				self.total_pending_days = date_diff(self.final_schedule_date, last_depr_date) - 1
			else:
				self.total_pending_days = date_diff(
					self.final_schedule_date, self.asset_doc.available_for_use_date
				)
		else:
			self.total_pending_years = self.pending_months / 12

	def has_fiscal_year_changed(self, row_idx):
		self.fiscal_year_changed = False

		schedule_date = get_last_day(
			add_months(
				self.fb_row.depreciation_start_date, row_idx * cint(self.fb_row.frequency_of_depreciation)
			)
		)

		if not self.current_fiscal_year_end_date:
			self.current_fiscal_year_end_date = get_fiscal_year(self.fb_row.depreciation_start_date)[2]
			self.fiscal_year_changed = True
		elif getdate(schedule_date) > getdate(self.current_fiscal_year_end_date):
			self.current_fiscal_year_end_date = add_years(self.current_fiscal_year_end_date, 1)
			self.fiscal_year_changed = True

	def get_prev_depreciation_amount(self, row_idx):
		if row_idx > 1:
			self.prev_depreciation_amount = 0
			if len(self.get("depreciation_schedule")) > row_idx - 1:
				self.prev_depreciation_amount = self.get("depreciation_schedule")[
					row_idx - 1
				].depreciation_amount

	def get_next_schedule_date(self, row_idx):
		schedule_date = add_months(
			self.fb_row.depreciation_start_date, row_idx * cint(self.fb_row.frequency_of_depreciation)
		)
		if self.should_get_last_day:
			schedule_date = get_last_day(schedule_date)

		return schedule_date

	def set_depreciation_amount_for_disposal(self, row_idx):
		if self.depreciation_schedule:  # if there are already booked depreciations
			from_date = add_days(self.depreciation_schedule[-1].schedule_date, 1)
		else:
			from_date = self._get_modified_available_for_use_date_for_existing_assets()
			if is_last_day_of_the_month(getdate(self.asset_doc.available_for_use_date)):
				from_date = get_last_day(from_date)

		self.depreciation_amount, days, months = self._get_pro_rata_amt(
			from_date,
			self.disposal_date,
			original_schedule_date=self.schedule_date,
		)

		self.depreciation_amount = flt(
			self.depreciation_amount, self.asset_doc.precision("net_purchase_amount")
		)
		if self.depreciation_amount > 0:
			self.schedule_date = self.disposal_date
			self.add_depr_schedule_row(row_idx)

	def set_depreciation_amount_for_first_row(self, row_idx):
		"""
		For the first row, if available for use date is mid of the month, then pro rata amount is needed
		"""
		pro_rata_amount_applicable = False
		if (
			self.has_pro_rata
			and not self.opening_accumulated_depreciation
			and not self.flags.wdv_it_act_applied
		):  # if not existing asset
			from_date = self.asset_doc.available_for_use_date
			pro_rata_amount_applicable = True
		elif self.has_pro_rata and self.opening_accumulated_depreciation:  # if existing asset
			from_date = self._get_modified_available_for_use_date_for_existing_assets()
			pro_rata_amount_applicable = True

		if pro_rata_amount_applicable:
			self.depreciation_amount, days, months = self._get_pro_rata_amt(
				from_date,
				self.fb_row.depreciation_start_date,
			)

			self.validate_depreciation_amount_for_low_value_assets()

	def set_depreciation_amount_for_last_row(self, row_idx):
		if not self.fb_row.increase_in_asset_life:
			self.final_schedule_date = add_months(
				self.asset_doc.available_for_use_date,
				(row_idx + self.opening_number_of_booked_depreciations)
				* cint(self.fb_row.frequency_of_depreciation),
			)
			if is_last_day_of_the_month(getdate(self.asset_doc.available_for_use_date)):
				self.final_schedule_date = get_last_day(self.final_schedule_date)

		if self.opening_accumulated_depreciation:
			self.depreciation_amount, days, months = self._get_pro_rata_amt(
				self.schedule_date,
				self.final_schedule_date,
			)
		else:
			if not self.fb_row.increase_in_asset_life:
				self.depreciation_amount -= self.get("depreciation_schedule")[0].depreciation_amount
			days = date_diff(self.final_schedule_date, self.schedule_date) + 1

		self.schedule_date = add_days(self.schedule_date, days - 1)

	def adjust_depr_amount_for_salvage_value(self, row_idx):
		"""
		Adjust depreciation amount in the last period based on the expected value after useful life
		"""
		if (
			row_idx == cint(self.final_number_of_depreciations) - 1
			and flt(self.pending_depreciation_amount) != flt(self.fb_row.expected_value_after_useful_life)
		) or flt(self.pending_depreciation_amount) < flt(self.fb_row.expected_value_after_useful_life):
			self.depreciation_amount += flt(self.pending_depreciation_amount) - flt(
				self.fb_row.expected_value_after_useful_life
			)
			self.depreciation_amount = flt(
				self.depreciation_amount, self.precision("value_after_depreciation")
			)
			self.skip_row = True

	def validate_depreciation_amount_for_low_value_assets(self):
		"""
		If net purchase amount is too low, then depreciation amount
		can come zero sometimes based on the frequency and number of depreciations.
		"""
		if flt(self.depreciation_amount, self.asset_doc.precision("net_purchase_amount")) <= 0:
			frappe.throw(
				_("Net Purchase Amount {0} cannot be depreciated over {1} cycles.").format(
					frappe.bold(self.asset_doc.net_purchase_amount),
					frappe.bold(self.fb_row.total_number_of_depreciations),
				)
			)

	def add_depr_schedule_row(self, row_idx):
		shift = None
		if self.shift_based:
			shift = (
				self.schedules_before_clearing[row_idx].shift
				if (self.schedules_before_clearing and len(self.schedules_before_clearing) > row_idx)
				else frappe.get_cached_value("Asset Shift Factor", {"default": 1}, "shift_name")
			)

		self.append(
			"depreciation_schedule",
			{
				"schedule_date": self.schedule_date,
				"depreciation_amount": self.depreciation_amount,
				"shift": shift,
			},
		)

	def set_accumulated_depreciation(self):
		accumulated_depreciation = flt(self.opening_accumulated_depreciation)
		for d in self.get("depreciation_schedule"):
			if d.journal_entry:
				accumulated_depreciation = d.accumulated_depreciation_amount
				continue

			accumulated_depreciation += d.depreciation_amount
			d.accumulated_depreciation_amount = flt(
				accumulated_depreciation, d.precision("accumulated_depreciation_amount")
			)

	def get_depreciation_amount(self, row_idx):
		if self.fb_row.depreciation_method in ("Straight Line", "Manual"):
			return self.get_straight_line_depr_amount(row_idx)
		else:
			return self.get_wdv_or_dd_depr_amount(row_idx)

	def _get_total_days(self, depreciation_start_date, row_idx):
		from_date = add_months(depreciation_start_date, (row_idx - 1) * self.frequency_of_depreciation)
		to_date = add_months(from_date, self.frequency_of_depreciation)
		if is_last_day_of_the_month(depreciation_start_date):
			to_date = get_last_day(to_date)
			from_date = add_days(get_last_day(from_date), 1)
		return from_date, date_diff(to_date, from_date) + 1

	def get_total_days_in_current_depr_year(self):
		fy_start_date, fy_end_date = self.get_fiscal_year(self.schedule_date)
		return date_diff(fy_end_date, fy_start_date) + 1

	def get_fiscal_year(self, date):
		fy = get_fiscal_year(date, as_dict=True, raise_on_missing=False)
		if fy:
			fy_start_date = fy.year_start_date
			fy_end_date = fy.year_end_date
		else:
			current_fy = get_fiscal_year(nowdate(), as_dict=True)
			# get fiscal year start date of the year in which the schedule date falls
			months = month_diff(date, current_fy.year_start_date)
			if months % 12:
				years = months // 12
			else:
				years = months // 12 - 1

			fy_start_date = add_years(current_fy.year_start_date, years)
			fy_end_date = add_days(add_years(fy_start_date, 1), -1)

		return fy_start_date, fy_end_date
