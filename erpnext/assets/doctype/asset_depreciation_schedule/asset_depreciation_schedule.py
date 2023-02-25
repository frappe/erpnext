# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, add_months, cint, flt, get_last_day, is_last_day_of_the_month


class AssetDepreciationSchedule(Document):
	def before_save(self):
		if not self.finance_book_id:
			self.prepare_draft_asset_depr_schedule_data_from_asset_name_and_fb_name(
				self.asset, self.finance_book
			)

	def validate(self):
		self.validate_another_asset_depr_schedule_does_not_exist()

	def validate_another_asset_depr_schedule_does_not_exist(self):
		finance_book_filter = ["finance_book", "is", "not set"]
		if self.finance_book:
			finance_book_filter = ["finance_book", "=", self.finance_book]

		asset_depr_schedule = frappe.db.exists(
			"Asset Depreciation Schedule",
			[
				["asset", "=", self.asset],
				finance_book_filter,
				["docstatus", "<", 2],
			],
		)

		if asset_depr_schedule and asset_depr_schedule != self.name:
			if self.finance_book:
				frappe.throw(
					_(
						"Asset Depreciation Schedule {0} for Asset {1} and Finance Book {2} already exists."
					).format(asset_depr_schedule, self.asset, self.finance_book)
				)
			else:
				frappe.throw(
					_("Asset Depreciation Schedule {0} for Asset {1} already exists.").format(
						asset_depr_schedule, self.asset
					)
				)

	def on_submit(self):
		self.db_set("status", "Active")

	def before_cancel(self):
		if not self.flags.should_not_cancel_depreciation_entries:
			self.cancel_depreciation_entries()

	def cancel_depreciation_entries(self):
		for d in self.get("depreciation_schedule"):
			if d.journal_entry:
				frappe.get_doc("Journal Entry", d.journal_entry).cancel()

	def on_cancel(self):
		self.db_set("status", "Cancelled")

	def prepare_draft_asset_depr_schedule_data_from_asset_name_and_fb_name(self, asset_name, fb_name):
		asset_doc = frappe.get_doc("Asset", asset_name)

		finance_book_filter = ["finance_book", "is", "not set"]
		if fb_name:
			finance_book_filter = ["finance_book", "=", fb_name]

		asset_finance_book_name = frappe.db.get_value(
			doctype="Asset Finance Book",
			filters=[["parent", "=", asset_name], finance_book_filter],
		)
		asset_finance_book_doc = frappe.get_doc("Asset Finance Book", asset_finance_book_name)

		self.prepare_draft_asset_depr_schedule_data(asset_doc, asset_finance_book_doc)

	def prepare_draft_asset_depr_schedule_data(
		self,
		asset_doc,
		row,
		date_of_disposal=None,
		date_of_return=None,
		update_asset_finance_book_row=True,
	):
		self.set_draft_asset_depr_schedule_details(asset_doc, row)
		self.make_depr_schedule(asset_doc, row, date_of_disposal, update_asset_finance_book_row)
		self.set_accumulated_depreciation(row, date_of_disposal, date_of_return)

	def set_draft_asset_depr_schedule_details(self, asset_doc, row):
		self.asset = asset_doc.name
		self.finance_book = row.finance_book
		self.finance_book_id = row.idx
		self.opening_accumulated_depreciation = asset_doc.opening_accumulated_depreciation
		self.depreciation_method = row.depreciation_method
		self.total_number_of_depreciations = row.total_number_of_depreciations
		self.frequency_of_depreciation = row.frequency_of_depreciation
		self.rate_of_depreciation = row.rate_of_depreciation
		self.expected_value_after_useful_life = row.expected_value_after_useful_life
		self.status = "Draft"

	def make_depr_schedule(
		self, asset_doc, row, date_of_disposal, update_asset_finance_book_row=True
	):
		if row.depreciation_method != "Manual" and not self.get("depreciation_schedule"):
			self.depreciation_schedule = []

		if not asset_doc.available_for_use_date:
			return

		start = self.clear_depr_schedule()

		self._make_depr_schedule(asset_doc, row, start, date_of_disposal, update_asset_finance_book_row)

	def clear_depr_schedule(self):
		start = 0
		num_of_depreciations_completed = 0
		depr_schedule = []

		for schedule in self.get("depreciation_schedule"):
			if schedule.journal_entry:
				num_of_depreciations_completed += 1
				depr_schedule.append(schedule)
			else:
				start = num_of_depreciations_completed
				break

		self.depreciation_schedule = depr_schedule

		return start

	def _make_depr_schedule(
		self, asset_doc, row, start, date_of_disposal, update_asset_finance_book_row
	):
		asset_doc.validate_asset_finance_books(row)

		value_after_depreciation = _get_value_after_depreciation_for_making_schedule(asset_doc, row)
		row.value_after_depreciation = value_after_depreciation

		if update_asset_finance_book_row:
			row.db_update()

		number_of_pending_depreciations = cint(row.total_number_of_depreciations) - cint(
			asset_doc.number_of_depreciations_booked
		)

		has_pro_rata = asset_doc.check_is_pro_rata(row)
		if has_pro_rata:
			number_of_pending_depreciations += 1

		skip_row = False
		should_get_last_day = is_last_day_of_the_month(row.depreciation_start_date)

		for n in range(start, number_of_pending_depreciations):
			# If depreciation is already completed (for double declining balance)
			if skip_row:
				continue

			depreciation_amount = asset_doc.get_depreciation_amount(value_after_depreciation, row)

			if not has_pro_rata or n < cint(number_of_pending_depreciations) - 1:
				schedule_date = add_months(
					row.depreciation_start_date, n * cint(row.frequency_of_depreciation)
				)

				if should_get_last_day:
					schedule_date = get_last_day(schedule_date)

				# schedule date will be a year later from start date
				# so monthly schedule date is calculated by removing 11 months from it
				monthly_schedule_date = add_months(schedule_date, -row.frequency_of_depreciation + 1)

			# if asset is being sold or scrapped
			if date_of_disposal:
				from_date = asset_doc.available_for_use_date
				if self.depreciation_schedule:
					from_date = self.depreciation_schedule[-1].schedule_date

				depreciation_amount, days, months = asset_doc.get_pro_rata_amt(
					row, depreciation_amount, from_date, date_of_disposal
				)

				if depreciation_amount > 0:
					self.add_depr_schedule_row(
						date_of_disposal,
						depreciation_amount,
						row.depreciation_method,
					)

				break

			# For first row
			if has_pro_rata and not asset_doc.opening_accumulated_depreciation and n == 0:
				from_date = add_days(
					asset_doc.available_for_use_date, -1
				)  # needed to calc depr amount for available_for_use_date too
				depreciation_amount, days, months = asset_doc.get_pro_rata_amt(
					row, depreciation_amount, from_date, row.depreciation_start_date
				)

				# For first depr schedule date will be the start date
				# so monthly schedule date is calculated by removing
				# month difference between use date and start date
				monthly_schedule_date = add_months(row.depreciation_start_date, -months + 1)

			# For last row
			elif has_pro_rata and n == cint(number_of_pending_depreciations) - 1:
				if not asset_doc.flags.increase_in_asset_life:
					# In case of increase_in_asset_life, the asset.to_date is already set on asset_repair submission
					asset_doc.to_date = add_months(
						asset_doc.available_for_use_date,
						(n + asset_doc.number_of_depreciations_booked) * cint(row.frequency_of_depreciation),
					)

				depreciation_amount_without_pro_rata = depreciation_amount

				depreciation_amount, days, months = asset_doc.get_pro_rata_amt(
					row, depreciation_amount, schedule_date, asset_doc.to_date
				)

				depreciation_amount = self.get_adjusted_depreciation_amount(
					depreciation_amount_without_pro_rata, depreciation_amount
				)

				monthly_schedule_date = add_months(schedule_date, 1)
				schedule_date = add_days(schedule_date, days)
				last_schedule_date = schedule_date

			if not depreciation_amount:
				continue
			value_after_depreciation -= flt(
				depreciation_amount, asset_doc.precision("gross_purchase_amount")
			)

			# Adjust depreciation amount in the last period based on the expected value after useful life
			if row.expected_value_after_useful_life and (
				(
					n == cint(number_of_pending_depreciations) - 1
					and value_after_depreciation != row.expected_value_after_useful_life
				)
				or value_after_depreciation < row.expected_value_after_useful_life
			):
				depreciation_amount += value_after_depreciation - row.expected_value_after_useful_life
				skip_row = True

			if depreciation_amount > 0:
				self.add_depr_schedule_row(
					schedule_date,
					depreciation_amount,
					row.depreciation_method,
				)

	# to ensure that final accumulated depreciation amount is accurate
	def get_adjusted_depreciation_amount(
		self, depreciation_amount_without_pro_rata, depreciation_amount_for_last_row
	):
		if not self.opening_accumulated_depreciation:
			depreciation_amount_for_first_row = self.get_depreciation_amount_for_first_row()

			if (
				depreciation_amount_for_first_row + depreciation_amount_for_last_row
				!= depreciation_amount_without_pro_rata
			):
				depreciation_amount_for_last_row = (
					depreciation_amount_without_pro_rata - depreciation_amount_for_first_row
				)

		return depreciation_amount_for_last_row

	def get_depreciation_amount_for_first_row(self):
		return self.get("depreciation_schedule")[0].depreciation_amount

	def add_depr_schedule_row(
		self,
		schedule_date,
		depreciation_amount,
		depreciation_method,
	):
		self.append(
			"depreciation_schedule",
			{
				"schedule_date": schedule_date,
				"depreciation_amount": depreciation_amount,
				"depreciation_method": depreciation_method,
			},
		)

	def set_accumulated_depreciation(
		self,
		row,
		date_of_disposal=None,
		date_of_return=None,
		ignore_booked_entry=False,
	):
		straight_line_idx = [
			d.idx for d in self.get("depreciation_schedule") if d.depreciation_method == "Straight Line"
		]

		accumulated_depreciation = flt(self.opening_accumulated_depreciation)
		value_after_depreciation = flt(row.value_after_depreciation)

		for i, d in enumerate(self.get("depreciation_schedule")):
			if ignore_booked_entry and d.journal_entry:
				continue

			depreciation_amount = flt(d.depreciation_amount, d.precision("depreciation_amount"))
			value_after_depreciation -= flt(depreciation_amount)

			# for the last row, if depreciation method = Straight Line
			if (
				straight_line_idx
				and i == max(straight_line_idx) - 1
				and not date_of_disposal
				and not date_of_return
			):
				depreciation_amount += flt(
					value_after_depreciation - flt(row.expected_value_after_useful_life),
					d.precision("depreciation_amount"),
				)

			d.depreciation_amount = depreciation_amount
			accumulated_depreciation += d.depreciation_amount
			d.accumulated_depreciation_amount = flt(
				accumulated_depreciation, d.precision("accumulated_depreciation_amount")
			)


def _get_value_after_depreciation_for_making_schedule(asset_doc, fb_row):
	if asset_doc.docstatus == 1 and fb_row.value_after_depreciation:
		value_after_depreciation = flt(fb_row.value_after_depreciation)
	else:
		value_after_depreciation = flt(asset_doc.gross_purchase_amount) - flt(
			asset_doc.opening_accumulated_depreciation
		)

	return value_after_depreciation


def make_draft_asset_depr_schedules_if_not_present(asset_doc):
	for row in asset_doc.get("finance_books"):
		draft_asset_depr_schedule_name = get_asset_depr_schedule_name(
			asset_doc.name, "Draft", row.finance_book
		)

		active_asset_depr_schedule_name = get_asset_depr_schedule_name(
			asset_doc.name, "Active", row.finance_book
		)

		if not draft_asset_depr_schedule_name and not active_asset_depr_schedule_name:
			make_draft_asset_depr_schedule(asset_doc, row)


def make_draft_asset_depr_schedules(asset_doc):
	for row in asset_doc.get("finance_books"):
		make_draft_asset_depr_schedule(asset_doc, row)


def make_draft_asset_depr_schedule(asset_doc, row):
	asset_depr_schedule_doc = frappe.new_doc("Asset Depreciation Schedule")

	asset_depr_schedule_doc.prepare_draft_asset_depr_schedule_data(asset_doc, row)

	asset_depr_schedule_doc.insert()


def update_draft_asset_depr_schedules(asset_doc):
	for row in asset_doc.get("finance_books"):
		asset_depr_schedule_doc = get_asset_depr_schedule_doc(asset_doc.name, "Draft", row.finance_book)

		if not asset_depr_schedule_doc:
			continue

		asset_depr_schedule_doc.prepare_draft_asset_depr_schedule_data(asset_doc, row)

		asset_depr_schedule_doc.save()


def convert_draft_asset_depr_schedules_into_active(asset_doc):
	for row in asset_doc.get("finance_books"):
		asset_depr_schedule_doc = get_asset_depr_schedule_doc(asset_doc.name, "Draft", row.finance_book)

		if not asset_depr_schedule_doc:
			continue

		asset_depr_schedule_doc.submit()


def cancel_asset_depr_schedules(asset_doc):
	for row in asset_doc.get("finance_books"):
		asset_depr_schedule_doc = get_asset_depr_schedule_doc(asset_doc.name, "Active", row.finance_book)

		if not asset_depr_schedule_doc:
			continue

		asset_depr_schedule_doc.cancel()


def make_new_active_asset_depr_schedules_and_cancel_current_ones(
	asset_doc, notes, date_of_disposal=None, date_of_return=None
):
	for row in asset_doc.get("finance_books"):
		current_asset_depr_schedule_doc = get_asset_depr_schedule_doc(
			asset_doc.name, "Active", row.finance_book
		)

		if not current_asset_depr_schedule_doc:
			frappe.throw(
				_("Asset Depreciation Schedule not found for Asset {0} and Finance Book {1}").format(
					asset_doc.name, row.finance_book
				)
			)

		new_asset_depr_schedule_doc = frappe.copy_doc(current_asset_depr_schedule_doc)

		new_asset_depr_schedule_doc.make_depr_schedule(asset_doc, row, date_of_disposal)
		new_asset_depr_schedule_doc.set_accumulated_depreciation(row, date_of_disposal, date_of_return)

		new_asset_depr_schedule_doc.notes = notes

		current_asset_depr_schedule_doc.flags.should_not_cancel_depreciation_entries = True
		current_asset_depr_schedule_doc.cancel()

		new_asset_depr_schedule_doc.submit()


def get_temp_asset_depr_schedule_doc(
	asset_doc, row, date_of_disposal=None, date_of_return=None, update_asset_finance_book_row=False
):
	asset_depr_schedule_doc = frappe.new_doc("Asset Depreciation Schedule")

	asset_depr_schedule_doc.prepare_draft_asset_depr_schedule_data(
		asset_doc,
		row,
		date_of_disposal,
		date_of_return,
		update_asset_finance_book_row,
	)

	return asset_depr_schedule_doc


@frappe.whitelist()
def get_depr_schedule(asset_name, status, finance_book=None):
	asset_depr_schedule_doc = get_asset_depr_schedule_doc(asset_name, status, finance_book)

	if not asset_depr_schedule_doc:
		return

	return asset_depr_schedule_doc.get("depreciation_schedule")


def get_asset_depr_schedule_doc(asset_name, status, finance_book=None):
	asset_depr_schedule_name = get_asset_depr_schedule_name(asset_name, status, finance_book)

	if not asset_depr_schedule_name:
		return

	asset_depr_schedule_doc = frappe.get_doc("Asset Depreciation Schedule", asset_depr_schedule_name)

	return asset_depr_schedule_doc


def get_asset_depr_schedule_name(asset_name, status, finance_book=None):
	finance_book_filter = ["finance_book", "is", "not set"]
	if finance_book:
		finance_book_filter = ["finance_book", "=", finance_book]

	return frappe.db.get_value(
		doctype="Asset Depreciation Schedule",
		filters=[
			["asset", "=", asset_name],
			finance_book_filter,
			["status", "=", status],
		],
	)
