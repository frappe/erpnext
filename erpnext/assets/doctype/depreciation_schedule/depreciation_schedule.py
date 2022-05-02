# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, add_months, date_diff, getdate


class DepreciationSchedule(Document):
	def validate(self):
		from erpnext.controllers.base_asset import validate_serial_no

		validate_serial_no(self)

	def before_submit(self):
		self.set_status("Active")

	def set_status(self, status):
		self.db_set("status", status)


def create_depreciation_schedules(asset, date_of_sale=None):
	purchase_value = get_purchase_amount(asset)
	enable_finance_books = get_enable_finance_books_value()

	if enable_finance_books:
		for row in asset.get("finance_books"):
			create_a_single_depreciation_schedule(asset, row, purchase_value, date_of_sale)
	else:
		create_a_single_depreciation_schedule(asset, None, purchase_value, date_of_sale)


def get_enable_finance_books_value():
	return frappe.db.get_single_value("Accounts Settings", "enable_finance_books")


def create_a_single_depreciation_schedule(asset, row=None, purchase_value=None, date_of_sale=None):
	if not purchase_value:
		purchase_value = get_purchase_amount(asset)

	depr_schedule = frappe.new_doc("Depreciation Schedule")

	if asset.doctype == "Asset":
		depr_schedule.asset = asset.name
	else:
		depr_schedule.asset = asset.asset
		depr_schedule.serial_no = asset.serial_no

	depr_schedule.creation_date = getdate()

	if row:
		depr_schedule.finance_book = row.finance_book

	set_depreciation_details_from_template(depr_schedule, asset, row)
	make_depreciation_schedule(depr_schedule, asset, purchase_value, date_of_sale)
	set_accumulated_depreciation(depr_schedule)

	depr_schedule.save()


def get_purchase_amount(asset):
	if asset.doctype == "Asset":
		return asset.gross_purchase_amount
	else:
		purchase_value = frappe.get_value("Asset", asset.asset, "gross_purchase_amount")

		return purchase_value


def set_depreciation_details_from_template(depr_schedule, asset, row):
	template_values = fetch_template_values(asset, row)

	depr_schedule.depreciation_method = template_values["depreciation_method"]
	depr_schedule.frequency_of_depreciation = template_values["frequency_of_depreciation"]
	depr_schedule.rate_of_depreciation = template_values["rate_of_depreciation"]

	if template_values["asset_life_unit"] == "Months":
		depr_schedule.asset_life_in_months = template_values["asset_life"]
	else:
		depr_schedule.asset_life_in_months = template_values["asset_life"] * 12


def fetch_template_values(asset, row):
	depreciation_template = get_depr_template(asset, row)

	return frappe.get_value(
		"Depreciation Template",
		depreciation_template,
		[
			"depreciation_method",
			"frequency_of_depreciation",
			"asset_life",
			"asset_life_unit",
			"rate_of_depreciation",
		],
		as_dict=1,
	)


def get_depr_template(asset, row):
	if row:
		return row.depreciation_template
	else:
		return asset.depreciation_template


def make_depreciation_schedule(depr_schedule, asset, purchase_value, date_of_sale):
	depreciable_value = purchase_value - asset.salvage_value
	frequency_of_depr = get_frequency_of_depreciation_in_months(
		depr_schedule.frequency_of_depreciation
	)

	if depr_schedule.depreciation_method == "Straight Line":
		make_depreciation_schedule_for_slm(
			depr_schedule, asset, frequency_of_depr, depreciable_value, date_of_sale
		)

	elif depr_schedule.depreciation_method in ["Double Declining Balance", "Written Down Value"]:
		make_depreciation_schedule_for_ddb_and_wdv(
			depr_schedule, asset, frequency_of_depr, purchase_value, depreciable_value, date_of_sale
		)


def get_frequency_of_depreciation_in_months(frequency_of_depreciation):
	frequency_in_months = {
		"Monthly": 1,
		"Every 2 months": 2,
		"Quarterly": 3,
		"Every 4 months": 4,
		"Every 5 months": 5,
		"Half-Yearly": 6,
		"Every 7 months": 7,
		"Every 8 months": 8,
		"Every 9 months": 9,
		"Every 10 months": 10,
		"Every 11 months": 11,
		"Yearly": 12,
	}

	return frequency_in_months[frequency_of_depreciation]


def make_depreciation_schedule_for_slm(
	depr_schedule, asset, frequency_of_depr, depreciable_value, date_of_sale
):
	depr_in_one_day = get_depreciation_in_one_day(
		asset.available_for_use_date, depr_schedule.asset_life_in_months, depreciable_value
	)

	depr_start_date = get_depreciation_start_date(
		asset.available_for_use_date, asset.opening_accumulated_depreciation, depr_in_one_day
	)
	depr_end_date = get_depreciation_end_date(
		asset.available_for_use_date, depr_schedule.asset_life_in_months, date_of_sale
	)

	schedule_date = asset.depreciation_posting_start_date

	while schedule_date < depr_end_date:
		depr_amount = get_depr_amount_for_slm(schedule_date, depr_start_date, depr_in_one_day)
		create_depreciation_entry(depr_schedule, schedule_date, depr_amount)

		depr_start_date = add_days(schedule_date, 1)
		schedule_date = add_months(schedule_date, frequency_of_depr)

	# for the final row
	depr_amount = get_depr_amount_for_slm(schedule_date, depr_start_date, depr_in_one_day)
	create_depreciation_entry(depr_schedule, schedule_date, depr_amount)


def make_depreciation_schedule_for_ddb_and_wdv(
	depr_schedule, asset, frequency_of_depr, purchase_value, depreciable_value, date_of_sale
):
	set_rate_of_depreciation(depr_schedule)

	beginning_book_value = get_beginning_book_value(
		depr_schedule.depreciation_method, purchase_value, depreciable_value
	)
	ending_book_value = beginning_book_value
	validate_beginning_book_value(beginning_book_value, asset.salvage_value)

	schedule_date = asset.depreciation_posting_start_date
	final_schedule_date = get_final_schedule_date(
		depr_schedule.asset_life_in_months, asset.available_for_use_date, date_of_sale
	)

	while beginning_book_value >= asset.salvage_value:
		if schedule_date <= final_schedule_date:
			# beginning book value for each depreciation is the ending book value of the previous one
			beginning_book_value = ending_book_value
			depr_amount = depr_schedule.rate_of_depreciation * beginning_book_value

			create_depreciation_entry(depr_schedule, schedule_date, depr_amount)

			ending_book_value = beginning_book_value - depr_amount

			# for the next depreciation
			schedule_date = add_months(schedule_date, frequency_of_depr)
		else:
			adjust_final_depreciation_amount(
				depr_schedule, ending_book_value, beginning_book_value, asset.salvage_value
			)
			break


def get_depreciation_start_date(available_for_use_date, opening_accumulated_depr, depr_in_one_day):
	if not opening_accumulated_depr:
		return available_for_use_date
	else:
		days_of_depr_booked = int(opening_accumulated_depr / depr_in_one_day)
		return add_days(available_for_use_date, days_of_depr_booked)


def get_depreciation_end_date(available_for_use_date, asset_life, date_of_sale):
	if date_of_sale:
		return date_of_sale

	day_after_depr_end_date = add_months(available_for_use_date, asset_life)
	depr_end_date = add_days(day_after_depr_end_date, -1)

	return depr_end_date


def get_depreciation_in_one_day(available_for_use_date, asset_life, depreciable_value):
	depr_end_date = add_months(available_for_use_date, asset_life)
	asset_life_in_days = date_diff(depr_end_date, available_for_use_date)

	return depreciable_value / asset_life_in_days


def get_depr_amount_for_slm(schedule_date, depr_start_date, depr_in_one_day):
	depr_period = date_diff(schedule_date, depr_start_date) + 1
	depr_amount = depr_in_one_day * depr_period

	return depr_amount


def create_depreciation_entry(depr_schedule, schedule_date, depr_amount):
	if depr_amount > 0:
		depr_schedule.append(
			"depreciation_schedule", {"schedule_date": schedule_date, "depreciation_amount": depr_amount}
		)


def set_rate_of_depreciation(depr_schedule):
	if depr_schedule.depreciation_method == "Double Declining Balance":
		depr_schedule.rate_of_depreciation = get_rate_of_depr_for_ddb(depr_schedule.asset_life_in_months)
	else:
		depr_schedule.rate_of_depreciation /= 100


def get_beginning_book_value(depreciation_method, purchase_value, depreciable_value):
	if depreciation_method == "Double Declining Balance":
		return purchase_value
	else:
		return depreciable_value


def get_rate_of_depr_for_ddb(asset_life_in_months):
	asset_life_in_years = asset_life_in_months / 12
	rate_of_depr = 2 / asset_life_in_years

	return rate_of_depr


def validate_beginning_book_value(beginning_book_value, salvage_value):
	if beginning_book_value <= salvage_value:
		frappe.throw(_("Salvage Value cannot be greater than or equal to Gross Purchase Amount."))


def get_final_schedule_date(asset_life_in_months, available_for_use_date, date_of_sale):
	depr_end_date = get_depreciation_end_date(
		available_for_use_date, asset_life_in_months, date_of_sale
	)
	final_schedule_date = add_days(depr_end_date, 1)

	return final_schedule_date


def adjust_final_depreciation_amount(
	depr_schedule, ending_book_value, beginning_book_value, salvage_value
):
	if ending_book_value != salvage_value:
		depr_schedule.depreciation_schedule[-1].depreciation_amount = (
			beginning_book_value - salvage_value
		)


def set_accumulated_depreciation(depr_schedule):
	accumulated_depr_amount = 0

	for schedule in depr_schedule.depreciation_schedule:
		accumulated_depr_amount += schedule.depreciation_amount
		schedule.accumulated_depreciation_amount = accumulated_depr_amount


def delete_existing_schedules(asset, finance_book=None):
	asset, serial_no = get_asset_and_serial_no(asset)

	filters = {"asset": asset, "serial_no": serial_no, "status": "Draft"}

	if finance_book:
		filters.update({"finance_book": finance_book.finance_book})

	depr_schedules = frappe.get_all("Depreciation Schedule", filters=filters, pluck="name")

	if depr_schedules:
		frappe.db.delete("Depreciation Schedule", {"name": ["in", depr_schedules]})


def get_asset_and_serial_no(asset):
	if asset.doctype == "Asset":
		return asset.name, ""
	else:
		return asset.asset, asset.serial_no
