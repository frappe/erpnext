# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import (
	add_days,
	add_months,
	cint,
	date_diff,
	flt,
	get_last_day,
	is_last_day_of_the_month,
)

import erpnext


class AssetDepreciationSchedule(Document):
	pass


def make_draft_asset_depreciation_schedules(asset_doc, date_of_disposal=None, date_of_return=None):
	for row in asset_doc.get("finance_books"):
		asset_depr_schedule = frappe.new_doc("Asset Depreciation Schedule")

		prepare_draft_asset_depreciation_schedule_data(
			asset_depr_schedule, asset_doc, row, date_of_disposal, date_of_return
		)

		asset_depr_schedule.insert()


def update_draft_asset_depreciation_schedules(
	asset_doc, date_of_disposal=None, date_of_return=None
):
	for row in asset_doc.get("finance_books"):
		asset_depr_schedule_name = get_asset_depreciation_schedule(asset_doc.name, row.finance_book)

		if not asset_depr_schedule_name:
			return

		asset_depr_schedule = frappe.get_doc("Asset Depreciation Schedule", asset_depr_schedule_name)

		prepare_draft_asset_depreciation_schedule_data(
			asset_depr_schedule, asset_doc, row, date_of_disposal, date_of_return
		)

		asset_depr_schedule.save()


def prepare_draft_asset_depreciation_schedule_data(
	asset_depr_schedule, asset_doc, row, date_of_disposal, date_of_return
):
	set_draft_asset_depreciation_schedule_details(asset_depr_schedule, asset_doc.name, row)
	make_depreciation_schedule(asset_depr_schedule, asset_doc, row, date_of_disposal)
	set_accumulated_depreciation(
		asset_depr_schedule, asset_doc, row, date_of_disposal, date_of_return
	)


def set_draft_asset_depreciation_schedule_details(asset_depr_schedule, asset, row):
	asset_depr_schedule.asset = asset
	asset_depr_schedule.finance_book = row.finance_book
	asset_depr_schedule.depreciation_method = row.depreciation_method
	asset_depr_schedule.total_number_of_depreciations = row.total_number_of_depreciations
	asset_depr_schedule.frequency_of_depreciation = row.frequency_of_depreciation
	asset_depr_schedule.rate_of_depreciation = row.rate_of_depreciation
	asset_depr_schedule.expected_value_after_useful_life = row.expected_value_after_useful_life
	asset_depr_schedule.status = "Draft"


def convert_draft_asset_depreciation_schedules_into_active(asset_doc):
	for row in asset_doc.get("finance_books"):
		asset_depr_schedule_name = get_asset_depreciation_schedule(asset_doc.name, row.finance_book)

		if not asset_depr_schedule_name:
			return

		asset_depr_schedule = frappe.get_doc("Asset Depreciation Schedule", asset_depr_schedule_name)

		asset_depr_schedule.status = "Active"

		asset_depr_schedule.submit()


def make_new_active_asset_depreciation_schedules_from_existing(
	asset_doc, date_of_disposal=None, date_of_return=None, notes=None
):
	for row in asset_doc.get("finance_books"):
		old_asset_depr_schedule_name = get_asset_depreciation_schedule(asset_doc.name, row.finance_book)

		if not old_asset_depr_schedule_name:
			return

		old_asset_depr_schedule = frappe.get_doc(
			"Asset Depreciation Schedule", old_asset_depr_schedule_name
		)

		asset_depr_schedule = frappe.copy_doc(old_asset_depr_schedule, ignore_no_copy=False)

		make_depreciation_schedule(asset_depr_schedule, asset_doc, row, date_of_disposal)
		set_accumulated_depreciation(
			asset_depr_schedule, asset_doc, row, date_of_disposal, date_of_return
		)

		asset_depr_schedule.notes = notes

		asset_depr_schedule.submit()


def make_temp_asset_depreciation_schedule(
	asset_doc, row, date_of_disposal=None, date_of_return=None
):
	asset_depr_schedule = frappe.new_doc("Asset Depreciation Schedule")

	prepare_draft_asset_depreciation_schedule_data(
		asset_depr_schedule, asset_doc, row, date_of_disposal, date_of_return
	)

	return asset_depr_schedule


def get_asset_depreciation_schedule(asset, finance_book):
	return frappe.db.get_value(
		doctype="Asset Depreciation Schedule",
		filters=[
			["asset", "=", asset],
			["finance_book", "=", finance_book],
			["docstatus", "<", 2],
		],
	)


def make_depreciation_schedule(asset_depr_schedule, asset_doc, row, date_of_disposal):
	if row.depreciation_method != "Manual" and not asset_depr_schedule.get("depreciation_schedule"):
		asset_depr_schedule.depreciation_schedule = []

	if not asset_doc.available_for_use_date:
		return

	start = clear_depreciation_schedule(asset_depr_schedule)

	_make_depreciation_schedule(asset_depr_schedule, asset_doc, row, start, date_of_disposal)


def clear_depreciation_schedule(asset_depr_schedule):
	start = []
	num_of_depreciations_completed = 0
	depr_schedule = []

	for schedule in asset_depr_schedule.get("depreciation_schedule"):
		if len(start) != 0:
			break

		if schedule.journal_entry:
			num_of_depreciations_completed += 1
			depr_schedule.append(schedule)
		else:
			start.append(num_of_depreciations_completed)
			num_of_depreciations_completed = 0

	# to update start when all the schedule rows corresponding to the FB are linked with JEs
	if len(start) == 0:
		start.append(num_of_depreciations_completed)

	# when the Depreciation Schedule is being created for the first time
	if start == []:
		start = [0]
	else:
		asset_depr_schedule.depreciation_schedule = depr_schedule

	return start


def _make_depreciation_schedule(asset_depr_schedule, asset_doc, row, start, date_of_disposal):
	asset_doc.validate_asset_finance_books(row)

	value_after_depreciation = asset_doc._get_value_after_depreciation(row)
	row.value_after_depreciation = value_after_depreciation

	number_of_pending_depreciations = cint(row.total_number_of_depreciations) - cint(
		asset_doc.number_of_depreciations_booked
	)

	has_pro_rata = asset_doc.check_is_pro_rata(row)
	if has_pro_rata:
		number_of_pending_depreciations += 1

	skip_row = False
	should_get_last_day = is_last_day_of_the_month(row.depreciation_start_date)

	for n in range(start[row.idx - 1], number_of_pending_depreciations):
		# If depreciation is already completed (for double declining balance)
		if skip_row:
			continue

		depreciation_amount = get_depreciation_amount(asset_doc, value_after_depreciation, row)

		if not has_pro_rata or n < cint(number_of_pending_depreciations) - 1:
			schedule_date = add_months(row.depreciation_start_date, n * cint(row.frequency_of_depreciation))

			if should_get_last_day:
				schedule_date = get_last_day(schedule_date)

			# schedule date will be a year later from start date
			# so monthly schedule date is calculated by removing 11 months from it
			monthly_schedule_date = add_months(schedule_date, -row.frequency_of_depreciation + 1)

		# if asset is being sold or scrapped
		if date_of_disposal:
			from_date = asset_doc.get_from_date(row.finance_book)
			depreciation_amount, days, months = asset_doc.get_pro_rata_amt(
				row, depreciation_amount, from_date, date_of_disposal
			)

			if depreciation_amount > 0:
				add_depr_schedule_row(
					asset_depr_schedule,
					date_of_disposal,
					depreciation_amount,
					row.depreciation_method,
					row.finance_book,
					row.idx,
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

			depreciation_amount = asset_doc.get_adjusted_depreciation_amount(
				depreciation_amount_without_pro_rata, depreciation_amount, row.finance_book
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
			add_depr_schedule_row(
				asset_depr_schedule,
				schedule_date,
				depreciation_amount,
				row.depreciation_method,
				row.finance_book,
				row.idx,
			)


@erpnext.allow_regional
def get_depreciation_amount(asset_doc, depreciable_value, row):
	if row.depreciation_method in ("Straight Line", "Manual"):
		# if the Depreciation Schedule is being prepared for the first time
		if not asset_doc.flags.increase_in_asset_life:
			depreciation_amount = (
				flt(asset_doc.gross_purchase_amount) - flt(row.expected_value_after_useful_life)
			) / flt(row.total_number_of_depreciations)

		# if the Depreciation Schedule is being modified after Asset Repair
		else:
			depreciation_amount = (
				flt(row.value_after_depreciation) - flt(row.expected_value_after_useful_life)
			) / (date_diff(asset_doc.to_date, asset_doc.available_for_use_date) / 365)
	else:
		depreciation_amount = flt(depreciable_value * (flt(row.rate_of_depreciation) / 100))

	return depreciation_amount


def add_depr_schedule_row(
	asset_depr_schedule,
	schedule_date,
	depreciation_amount,
	depreciation_method,
	finance_book,
	finance_book_id,
):
	asset_depr_schedule.append(
		"depreciation_schedule",
		{
			"schedule_date": schedule_date,
			"depreciation_amount": depreciation_amount,
			"depreciation_method": depreciation_method,
			"finance_book": finance_book,
			"finance_book_id": finance_book_id,
		},
	)


def set_accumulated_depreciation(
	asset_depr_schedule,
	asset_doc,
	row,
	date_of_disposal=None,
	date_of_return=None,
	ignore_booked_entry=False,
):
	straight_line_idx = [
		d.idx
		for d in asset_depr_schedule.get("depreciation_schedule")
		if d.depreciation_method == "Straight Line"
	]
	finance_books = []

	for i, d in enumerate(asset_depr_schedule.get("depreciation_schedule")):
		if ignore_booked_entry and d.journal_entry:
			continue

		if int(d.finance_book_id) not in finance_books:
			accumulated_depreciation = flt(asset_doc.opening_accumulated_depreciation)
			value_after_depreciation = flt(asset_doc.get_value_after_depreciation(d.finance_book_id))
			finance_books.append(int(d.finance_book_id))

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
