# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import (
	flt,
	get_first_day,
	get_link_to_form,
	getdate,
)

import erpnext
from erpnext.assets.doctype.asset_depreciation_schedule.deppreciation_schedule_controller import (
	DepreciationScheduleController,
)


class AssetDepreciationSchedule(DepreciationScheduleController):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.assets.doctype.depreciation_schedule.depreciation_schedule import DepreciationSchedule

		amended_from: DF.Link | None
		asset: DF.Link
		company: DF.Link | None
		daily_prorata_based: DF.Check
		depreciation_method: DF.Literal[
			"", "Straight Line", "Double Declining Balance", "Written Down Value", "Manual"
		]
		depreciation_schedule: DF.Table[DepreciationSchedule]
		expected_value_after_useful_life: DF.Currency
		finance_book: DF.Link | None
		finance_book_id: DF.Int
		frequency_of_depreciation: DF.Int
		naming_series: DF.Literal["ACC-ADS-.YYYY.-"]
		net_purchase_amount: DF.Currency
		notes: DF.SmallText | None
		opening_accumulated_depreciation: DF.Currency
		opening_number_of_booked_depreciations: DF.Int
		rate_of_depreciation: DF.Percent
		shift_based: DF.Check
		status: DF.Literal["Draft", "Active", "Cancelled"]
		total_number_of_depreciations: DF.Int
		value_after_depreciation: DF.Currency
	# end: auto-generated types

	def validate(self):
		self.validate_another_asset_depr_schedule_does_not_exist()
		if not self.finance_book_id:
			self.create_depreciation_schedule()
		self.update_shift_depr_schedule()

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
		self.validate_asset()
		self.db_set("status", "Active")

	def validate_asset(self):
		asset = frappe.get_doc("Asset", self.asset)
		if not asset.calculate_depreciation:
			frappe.throw(
				_("Asset {0} is not set to calculate depreciation.").format(
					get_link_to_form("Asset", self.asset)
				)
			)
		if asset.docstatus != 1:
			frappe.throw(
				_("Asset {0} is not submitted. Please submit the asset before proceeding.").format(
					get_link_to_form("Asset", self.asset)
				)
			)

	def on_cancel(self):
		self.db_set("status", "Cancelled")
		if not self.flags.should_not_cancel_depreciation_entries:
			self.cancel_depreciation_entries()

	def cancel_depreciation_entries(self):
		for d in self.get("depreciation_schedule"):
			if d.journal_entry:
				je_status = frappe.db.get_value("Journal Entry", d.journal_entry, "docstatus")
				if je_status == 0:
					frappe.throw(
						_(
							"Cannot cancel Asset Depreciation Schedule {0} as it has a draft journal entry {1}."
						).format(self.name, d.journal_entry)
					)
				frappe.get_doc("Journal Entry", d.journal_entry).cancel()

	def update_shift_depr_schedule(self):
		if not self.shift_based or self.docstatus != 0 or self.get("__islocal"):
			return
		self.create_depreciation_schedule()

	def get_finance_book_row(self, fb_row=None):
		if fb_row:
			self.fb_row = fb_row
			return

		finance_book_filter = ["finance_book", "is", "not set"]
		if self.finance_book:
			finance_book_filter = ["finance_book", "=", self.finance_book]

		asset_finance_book_name = frappe.db.get_value(
			doctype="Asset Finance Book",
			filters=[["parent", "=", self.asset], finance_book_filter],
		)
		self.fb_row = frappe.get_doc("Asset Finance Book", asset_finance_book_name)

	def fetch_asset_details(self):
		self.asset = self.asset_doc.name
		self.finance_book = self.fb_row.get("finance_book")
		self.finance_book_id = self.fb_row.idx
		self.opening_accumulated_depreciation = self.asset_doc.opening_accumulated_depreciation or 0
		self.opening_number_of_booked_depreciations = (
			self.asset_doc.opening_number_of_booked_depreciations or 0
		)
		self.net_purchase_amount = self.asset_doc.net_purchase_amount
		self.depreciation_method = self.fb_row.depreciation_method
		self.total_number_of_depreciations = self.fb_row.total_number_of_depreciations
		self.frequency_of_depreciation = self.fb_row.frequency_of_depreciation
		self.rate_of_depreciation = self.fb_row.get("rate_of_depreciation")
		self.value_after_depreciation = self.fb_row.value_after_depreciation
		self.expected_value_after_useful_life = self.fb_row.get("expected_value_after_useful_life")
		self.daily_prorata_based = self.fb_row.get("daily_prorata_based")
		self.shift_based = self.fb_row.get("shift_based")
		self.status = "Draft"


def make_draft_asset_depr_schedule(asset_doc, row):
	asset_depr_schedule_doc = frappe.new_doc("Asset Depreciation Schedule")

	asset_depr_schedule_doc.create_depreciation_schedule(asset_doc, row)

	asset_depr_schedule_doc.insert()

	return asset_depr_schedule_doc.name


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


def reschedule_depreciation(asset_doc, notes, disposal_date=None):
	for row in asset_doc.get("finance_books"):
		current_schedule = get_asset_depr_schedule_doc(asset_doc.name, None, row.finance_book)

		if current_schedule:
			if current_schedule.docstatus == 1:
				new_schedule = frappe.copy_doc(current_schedule)
			elif current_schedule.docstatus == 0:
				new_schedule = current_schedule
		else:
			new_schedule = frappe.new_doc("Asset Depreciation Schedule")
			new_schedule.asset = asset_doc.name

		set_modified_depreciation_rate(asset_doc, row, new_schedule)

		new_schedule.create_depreciation_schedule(row, disposal_date)
		new_schedule.notes = notes

		if current_schedule and current_schedule.docstatus == 1:
			current_schedule.flags.should_not_cancel_depreciation_entries = True
			current_schedule.cancel()

		new_schedule.submit()


def set_modified_depreciation_rate(asset_doc, row, new_schedule):
	if row.depreciation_method in (
		"Written Down Value",
		"Double Declining Balance",
	):
		new_rate_of_depreciation = flt(
			asset_doc.get_depreciation_rate(row), row.precision("rate_of_depreciation")
		)

		row.db_set("rate_of_depreciation", new_rate_of_depreciation)
		new_schedule.rate_of_depreciation = new_rate_of_depreciation


def get_temp_depr_schedule_doc(asset_doc, fb_row, disposal_date=None, updated_depr_schedule=None):
	current_schedule = get_current_asset_depr(asset_doc, fb_row)
	temp_schedule_doc = frappe.copy_doc(current_schedule)

	if updated_depr_schedule:
		modify_depreciation_dchedule(temp_schedule_doc, updated_depr_schedule)

	temp_schedule_doc.create_depreciation_schedule(fb_row, disposal_date)
	return temp_schedule_doc


def get_current_asset_depr(asset_doc, row):
	current_schedule = get_asset_depr_schedule_doc(asset_doc.name, "Active", row.finance_book)
	if not current_schedule:
		frappe.throw(
			_("Asset Depreciation Schedule not found for Asset {0} and Finance Book {1}").format(
				get_link_to_form("Asset", asset_doc.name), row.finance_book
			)
		)
	return current_schedule


def modify_depreciation_dchedule(temp_schedule_doc, updated_depr_schedule):
	temp_schedule_doc.depreciation_schedule = []

	for schedule in updated_depr_schedule:
		temp_schedule_doc.append(
			"depreciation_schedule",
			{
				"schedule_date": schedule.schedule_date,
				"depreciation_amount": schedule.depreciation_amount,
				"accumulated_depreciation_amount": schedule.accumulated_depreciation_amount,
				"journal_entry": schedule.journal_entry,
				"shift": schedule.shift,
			},
		)


def get_asset_shift_factors_map():
	return dict(frappe.db.get_all("Asset Shift Factor", ["shift_name", "shift_factor"], as_list=True))


@frappe.whitelist()
def get_depr_schedule(asset_name, status, finance_book=None):
	asset_depr_schedule_doc = get_asset_depr_schedule_doc(asset_name, status, finance_book)

	if not asset_depr_schedule_doc:
		return

	return asset_depr_schedule_doc.get("depreciation_schedule")


@frappe.whitelist()
def get_asset_depr_schedule_doc(asset_name, status=None, finance_book=None):
	asset_depr_schedule = get_asset_depr_schedule_name(asset_name, status, finance_book)

	if not asset_depr_schedule:
		return

	asset_depr_schedule_doc = frappe.get_doc("Asset Depreciation Schedule", asset_depr_schedule[0].name)

	return asset_depr_schedule_doc


def get_asset_depr_schedule_name(asset_name, status=None, finance_book=None):
	filters = [
		["asset", "=", asset_name],
		["docstatus", "<", 2],
	]

	if status:
		if isinstance(status, str):
			status = [status]
		filters.append(["status", "in", status])

	if finance_book:
		filters.append(["finance_book", "=", finance_book])
	else:
		filters.append(["finance_book", "is", "not set"])

	return frappe.get_all(
		doctype="Asset Depreciation Schedule",
		filters=filters,
		limit=1,
	)


def is_first_day_of_the_month(date):
	first_day_of_the_month = get_first_day(date)

	return getdate(first_day_of_the_month) == getdate(date)
