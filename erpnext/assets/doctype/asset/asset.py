# Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import json
import math

import frappe
from frappe import _
from frappe.utils import (
	add_days,
	add_months,
	cint,
	date_diff,
	flt,
	get_datetime,
	get_last_day,
	getdate,
	month_diff,
	nowdate,
	today,
)

import erpnext
from erpnext.accounts.general_ledger import make_reverse_gl_entries
from erpnext.assets.doctype.asset.depreciation import (
	get_depreciation_accounts,
	get_disposal_account_and_cost_center,
	is_last_day_of_the_month,
)
from erpnext.assets.doctype.asset_category.asset_category import get_asset_category_account
from erpnext.controllers.accounts_controller import AccountsController


class Asset(AccountsController):
	def validate(self):
		self.validate_asset_values()
		self.validate_asset_and_reference()
		self.validate_item()
		self.validate_cost_center()
		self.set_missing_values()
		if not self.split_from:
			self.prepare_depreciation_data()
		self.validate_gross_and_purchase_amount()
		if self.get("schedules"):
			self.validate_expected_value_after_useful_life()

		self.status = self.get_status()

	def on_submit(self):
		self.validate_in_use_date()
		self.set_status()
		self.make_asset_movement()
		if not self.booked_fixed_asset and self.validate_make_gl_entry():
			self.make_gl_entries()

	def on_cancel(self):
		self.validate_cancellation()
		self.cancel_movement_entries()
		self.delete_depreciation_entries()
		self.set_status()
		self.ignore_linked_doctypes = ("GL Entry", "Stock Ledger Entry")
		make_reverse_gl_entries(voucher_type="Asset", voucher_no=self.name)
		self.db_set("booked_fixed_asset", 0)

	def validate_asset_and_reference(self):
		if self.purchase_invoice or self.purchase_receipt:
			reference_doc = "Purchase Invoice" if self.purchase_invoice else "Purchase Receipt"
			reference_name = self.purchase_invoice or self.purchase_receipt
			reference_doc = frappe.get_doc(reference_doc, reference_name)
			if reference_doc.get("company") != self.company:
				frappe.throw(
					_("Company of asset {0} and purchase document {1} doesn't matches.").format(
						self.name, reference_doc.get("name")
					)
				)

		if self.is_existing_asset and self.purchase_invoice:
			frappe.throw(
				_("Purchase Invoice cannot be made against an existing asset {0}").format(self.name)
			)

	def prepare_depreciation_data(self, date_of_disposal=None, date_of_return=None):
		if self.calculate_depreciation:
			self.value_after_depreciation = 0
			self.set_depreciation_rate()
			self.make_depreciation_schedule(date_of_disposal)
			self.set_accumulated_depreciation(date_of_disposal, date_of_return)
		else:
			self.finance_books = []
			self.value_after_depreciation = flt(self.gross_purchase_amount) - flt(
				self.opening_accumulated_depreciation
			)

	def validate_item(self):
		item = frappe.get_cached_value(
			"Item", self.item_code, ["is_fixed_asset", "is_stock_item", "disabled"], as_dict=1
		)
		if not item:
			frappe.throw(_("Item {0} does not exist").format(self.item_code))
		elif item.disabled:
			frappe.throw(_("Item {0} has been disabled").format(self.item_code))
		elif not item.is_fixed_asset:
			frappe.throw(_("Item {0} must be a Fixed Asset Item").format(self.item_code))
		elif item.is_stock_item:
			frappe.throw(_("Item {0} must be a non-stock item").format(self.item_code))

	def validate_cost_center(self):
		if not self.cost_center:
			return

		cost_center_company = frappe.db.get_value("Cost Center", self.cost_center, "company")
		if cost_center_company != self.company:
			frappe.throw(
				_("Selected Cost Center {} doesn't belongs to {}").format(
					frappe.bold(self.cost_center), frappe.bold(self.company)
				),
				title=_("Invalid Cost Center"),
			)

	def validate_in_use_date(self):
		if not self.available_for_use_date:
			frappe.throw(_("Available for use date is required"))

		for d in self.finance_books:
			if d.depreciation_start_date == self.available_for_use_date:
				frappe.throw(
					_("Row #{}: Depreciation Posting Date should not be equal to Available for Use Date.").format(
						d.idx
					),
					title=_("Incorrect Date"),
				)

	def set_missing_values(self):
		if not self.asset_category:
			self.asset_category = frappe.get_cached_value("Item", self.item_code, "asset_category")

		if self.item_code and not self.get("finance_books"):
			finance_books = get_item_details(self.item_code, self.asset_category)
			self.set("finance_books", finance_books)

	def validate_asset_values(self):
		if not self.asset_category:
			self.asset_category = frappe.get_cached_value("Item", self.item_code, "asset_category")

		if not flt(self.gross_purchase_amount):
			frappe.throw(_("Gross Purchase Amount is mandatory"), frappe.MandatoryError)

		if is_cwip_accounting_enabled(self.asset_category):
			if not self.is_existing_asset and not (self.purchase_receipt or self.purchase_invoice):
				frappe.throw(
					_("Please create purchase receipt or purchase invoice for the item {0}").format(
						self.item_code
					)
				)

			if (
				not self.purchase_receipt
				and self.purchase_invoice
				and not frappe.db.get_value("Purchase Invoice", self.purchase_invoice, "update_stock")
			):
				frappe.throw(
					_("Update stock must be enable for the purchase invoice {0}").format(self.purchase_invoice)
				)

		if not self.calculate_depreciation:
			return
		elif not self.finance_books:
			frappe.throw(_("Enter depreciation details"))

		if self.is_existing_asset:
			return

		if self.available_for_use_date and getdate(self.available_for_use_date) < getdate(
			self.purchase_date
		):
			frappe.throw(_("Available-for-use Date should be after purchase date"))

	def validate_gross_and_purchase_amount(self):
		if self.is_existing_asset:
			return

		if self.gross_purchase_amount and self.gross_purchase_amount != self.purchase_receipt_amount:
			error_message = _(
				"Gross Purchase Amount should be <b>equal</b> to purchase amount of one single Asset."
			)
			error_message += "<br>"
			error_message += _("Please do not book expense of multiple assets against one single Asset.")
			frappe.throw(error_message, title=_("Invalid Gross Purchase Amount"))

	def make_asset_movement(self):
		reference_doctype = "Purchase Receipt" if self.purchase_receipt else "Purchase Invoice"
		reference_docname = self.purchase_receipt or self.purchase_invoice
		transaction_date = getdate(self.purchase_date)
		if reference_docname:
			posting_date, posting_time = frappe.db.get_value(
				reference_doctype, reference_docname, ["posting_date", "posting_time"]
			)
			transaction_date = get_datetime("{} {}".format(posting_date, posting_time))
		assets = [
			{
				"asset": self.name,
				"asset_name": self.asset_name,
				"target_location": self.location,
				"to_employee": self.custodian,
			}
		]
		asset_movement = frappe.get_doc(
			{
				"doctype": "Asset Movement",
				"assets": assets,
				"purpose": "Receipt",
				"company": self.company,
				"transaction_date": transaction_date,
				"reference_doctype": reference_doctype,
				"reference_name": reference_docname,
			}
		).insert()
		asset_movement.submit()

	def set_depreciation_rate(self):
		for d in self.get("finance_books"):
			d.rate_of_depreciation = flt(
				self.get_depreciation_rate(d, on_validate=True), d.precision("rate_of_depreciation")
			)

	def make_depreciation_schedule(self, date_of_disposal):
		if "Manual" not in [d.depreciation_method for d in self.finance_books] and not self.get(
			"schedules"
		):
			self.schedules = []

		if not self.available_for_use_date:
			return

		start = self.clear_depreciation_schedule()

		for finance_book in self.get("finance_books"):
			self._make_depreciation_schedule(finance_book, start, date_of_disposal)

		if len(self.get("finance_books")) > 1 and any(start):
			self.sort_depreciation_schedule()

	def _make_depreciation_schedule(self, finance_book, start, date_of_disposal):
		self.validate_asset_finance_books(finance_book)

		value_after_depreciation = self._get_value_after_depreciation_for_making_schedule(finance_book)
		finance_book.value_after_depreciation = value_after_depreciation

		number_of_pending_depreciations = cint(finance_book.total_number_of_depreciations) - cint(
			self.number_of_depreciations_booked
		)

		has_pro_rata = self.check_is_pro_rata(finance_book)
		if has_pro_rata:
			number_of_pending_depreciations += 1

		skip_row = False
		should_get_last_day = is_last_day_of_the_month(finance_book.depreciation_start_date)

		for n in range(start[finance_book.idx - 1], number_of_pending_depreciations):
			# If depreciation is already completed (for double declining balance)
			if skip_row:
				continue

			depreciation_amount = get_depreciation_amount(self, value_after_depreciation, finance_book)

			if not has_pro_rata or n < cint(number_of_pending_depreciations) - 1:
				schedule_date = add_months(
					finance_book.depreciation_start_date, n * cint(finance_book.frequency_of_depreciation)
				)

				if should_get_last_day:
					schedule_date = get_last_day(schedule_date)

				# schedule date will be a year later from start date
				# so monthly schedule date is calculated by removing 11 months from it
				monthly_schedule_date = add_months(schedule_date, -finance_book.frequency_of_depreciation + 1)

			# if asset is being sold
			if date_of_disposal:
				from_date = self.get_from_date(finance_book.finance_book)
				depreciation_amount, days, months = self.get_pro_rata_amt(
					finance_book, depreciation_amount, from_date, date_of_disposal
				)

				if depreciation_amount > 0:
					self._add_depreciation_row(
						date_of_disposal,
						depreciation_amount,
						finance_book.depreciation_method,
						finance_book.finance_book,
						finance_book.idx,
					)

				break

			# For first row
			if has_pro_rata and not self.opening_accumulated_depreciation and n == 0:
				from_date = add_days(
					self.available_for_use_date, -1
				)  # needed to calc depr amount for available_for_use_date too
				depreciation_amount, days, months = self.get_pro_rata_amt(
					finance_book, depreciation_amount, from_date, finance_book.depreciation_start_date
				)

				# For first depr schedule date will be the start date
				# so monthly schedule date is calculated by removing month difference between use date and start date
				monthly_schedule_date = add_months(finance_book.depreciation_start_date, -months + 1)

			# For last row
			elif has_pro_rata and n == cint(number_of_pending_depreciations) - 1:
				if not self.flags.increase_in_asset_life:
					# In case of increase_in_asset_life, the self.to_date is already set on asset_repair submission
					self.to_date = add_months(
						self.available_for_use_date,
						(n + self.number_of_depreciations_booked) * cint(finance_book.frequency_of_depreciation),
					)

				depreciation_amount_without_pro_rata = depreciation_amount

				depreciation_amount, days, months = self.get_pro_rata_amt(
					finance_book, depreciation_amount, schedule_date, self.to_date
				)

				depreciation_amount = self.get_adjusted_depreciation_amount(
					depreciation_amount_without_pro_rata, depreciation_amount, finance_book.finance_book
				)

				monthly_schedule_date = add_months(schedule_date, 1)
				schedule_date = add_days(schedule_date, days)
				last_schedule_date = schedule_date

			if not depreciation_amount:
				continue
			value_after_depreciation -= flt(depreciation_amount, self.precision("gross_purchase_amount"))

			# Adjust depreciation amount in the last period based on the expected value after useful life
			if finance_book.expected_value_after_useful_life and (
				(
					n == cint(number_of_pending_depreciations) - 1
					and value_after_depreciation != finance_book.expected_value_after_useful_life
				)
				or value_after_depreciation < finance_book.expected_value_after_useful_life
			):
				depreciation_amount += value_after_depreciation - finance_book.expected_value_after_useful_life
				skip_row = True

			if depreciation_amount > 0:
				self._add_depreciation_row(
					schedule_date,
					depreciation_amount,
					finance_book.depreciation_method,
					finance_book.finance_book,
					finance_book.idx,
				)

	def _add_depreciation_row(
		self, schedule_date, depreciation_amount, depreciation_method, finance_book, finance_book_id
	):
		self.append(
			"schedules",
			{
				"schedule_date": schedule_date,
				"depreciation_amount": depreciation_amount,
				"depreciation_method": depreciation_method,
				"finance_book": finance_book,
				"finance_book_id": finance_book_id,
			},
		)

	def sort_depreciation_schedule(self):
		self.schedules = sorted(
			self.schedules, key=lambda s: (int(s.finance_book_id), getdate(s.schedule_date))
		)

		for idx, s in enumerate(self.schedules, 1):
			s.idx = idx

	def _get_value_after_depreciation_for_making_schedule(self, finance_book):
		if self.docstatus == 1 and finance_book.value_after_depreciation:
			value_after_depreciation = flt(finance_book.value_after_depreciation)
		else:
			value_after_depreciation = flt(self.gross_purchase_amount) - flt(
				self.opening_accumulated_depreciation
			)

		return value_after_depreciation

	# depreciation schedules need to be cleared before modification due to increase in asset life/asset sales
	# JE: Journal Entry, FB: Finance Book
	def clear_depreciation_schedule(self):
		start = []
		num_of_depreciations_completed = 0
		depr_schedule = []

		for schedule in self.get("schedules"):
			# to update start when there are JEs linked with all the schedule rows corresponding to an FB
			if len(start) == (int(schedule.finance_book_id) - 2):
				start.append(num_of_depreciations_completed)
				num_of_depreciations_completed = 0

			# to ensure that start will only be updated once for each FB
			if len(start) == (int(schedule.finance_book_id) - 1):
				if schedule.journal_entry:
					num_of_depreciations_completed += 1
					depr_schedule.append(schedule)
				else:
					start.append(num_of_depreciations_completed)
					num_of_depreciations_completed = 0

		# to update start when all the schedule rows corresponding to the last FB are linked with JEs
		if len(start) == (len(self.finance_books) - 1):
			start.append(num_of_depreciations_completed)

		# when the Depreciation Schedule is being created for the first time
		if start == []:
			start = [0] * len(self.finance_books)
		else:
			self.schedules = depr_schedule

		return start

	def get_from_date(self, finance_book):
		if not self.get("schedules"):
			return self.available_for_use_date

		if len(self.finance_books) == 1:
			return self.schedules[-1].schedule_date

		from_date = ""
		for schedule in self.get("schedules"):
			if schedule.finance_book == finance_book:
				from_date = schedule.schedule_date

		if from_date:
			return from_date

		# since depr for available_for_use_date is not yet booked
		return add_days(self.available_for_use_date, -1)

	# if it returns True, depreciation_amount will not be equal for the first and last rows
	def check_is_pro_rata(self, row):
		has_pro_rata = False

		# if not existing asset, from_date = available_for_use_date
		# otherwise, if number_of_depreciations_booked = 2, available_for_use_date = 01/01/2020 and frequency_of_depreciation = 12
		# from_date = 01/01/2022
		from_date = self.get_modified_available_for_use_date(row)
		days = date_diff(row.depreciation_start_date, from_date) + 1

		# if frequency_of_depreciation is 12 months, total_days = 365
		total_days = get_total_days(row.depreciation_start_date, row.frequency_of_depreciation)

		if days < total_days:
			has_pro_rata = True

		return has_pro_rata

	def get_modified_available_for_use_date(self, row):
		return add_months(
			self.available_for_use_date,
			(self.number_of_depreciations_booked * row.frequency_of_depreciation),
		)

	def validate_asset_finance_books(self, row):
		if flt(row.expected_value_after_useful_life) >= flt(self.gross_purchase_amount):
			frappe.throw(
				_("Row {0}: Expected Value After Useful Life must be less than Gross Purchase Amount").format(
					row.idx
				),
				title=_("Invalid Schedule"),
			)

		if not row.depreciation_start_date:
			if not self.available_for_use_date:
				frappe.throw(
					_("Row {0}: Depreciation Start Date is required").format(row.idx), title=_("Invalid Schedule")
				)
			row.depreciation_start_date = get_last_day(self.available_for_use_date)

		if not self.is_existing_asset:
			self.opening_accumulated_depreciation = 0
			self.number_of_depreciations_booked = 0
		else:
			depreciable_amount = flt(self.gross_purchase_amount) - flt(row.expected_value_after_useful_life)
			if flt(self.opening_accumulated_depreciation) > depreciable_amount:
				frappe.throw(
					_("Opening Accumulated Depreciation must be less than equal to {0}").format(
						depreciable_amount
					)
				)

			if self.opening_accumulated_depreciation:
				if not self.number_of_depreciations_booked:
					frappe.throw(_("Please set Number of Depreciations Booked"))
			else:
				self.number_of_depreciations_booked = 0

			if flt(row.total_number_of_depreciations) <= cint(self.number_of_depreciations_booked):
				frappe.throw(
					_(
						"Row {0}: Total Number of Depreciations cannot be less than or equal to Number of Depreciations Booked"
					).format(row.idx),
					title=_("Invalid Schedule"),
				)

		if row.depreciation_start_date and getdate(row.depreciation_start_date) < getdate(
			self.purchase_date
		):
			frappe.throw(
				_("Depreciation Row {0}: Next Depreciation Date cannot be before Purchase Date").format(
					row.idx
				)
			)

		if row.depreciation_start_date and getdate(row.depreciation_start_date) < getdate(
			self.available_for_use_date
		):
			frappe.throw(
				_(
					"Depreciation Row {0}: Next Depreciation Date cannot be before Available-for-use Date"
				).format(row.idx)
			)

	# to ensure that final accumulated depreciation amount is accurate
	def get_adjusted_depreciation_amount(
		self, depreciation_amount_without_pro_rata, depreciation_amount_for_last_row, finance_book
	):
		if not self.opening_accumulated_depreciation:
			depreciation_amount_for_first_row = self.get_depreciation_amount_for_first_row(finance_book)

			if (
				depreciation_amount_for_first_row + depreciation_amount_for_last_row
				!= depreciation_amount_without_pro_rata
			):
				depreciation_amount_for_last_row = (
					depreciation_amount_without_pro_rata - depreciation_amount_for_first_row
				)

		return depreciation_amount_for_last_row

	def get_depreciation_amount_for_first_row(self, finance_book):
		if self.has_only_one_finance_book():
			return self.schedules[0].depreciation_amount
		else:
			for schedule in self.schedules:
				if schedule.finance_book == finance_book:
					return schedule.depreciation_amount

	def has_only_one_finance_book(self):
		if len(self.finance_books) == 1:
			return True

	def set_accumulated_depreciation(
		self, date_of_disposal=None, date_of_return=None, ignore_booked_entry=False
	):
		straight_line_idx = [
			d.idx for d in self.get("schedules") if d.depreciation_method == "Straight Line"
		]
		finance_books = []

		for i, d in enumerate(self.get("schedules")):
			if ignore_booked_entry and d.journal_entry:
				continue

			if int(d.finance_book_id) not in finance_books:
				accumulated_depreciation = flt(self.opening_accumulated_depreciation)
				value_after_depreciation = flt(
					self.get("finance_books")[cint(d.finance_book_id) - 1].value_after_depreciation
				)
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
				book = self.get("finance_books")[cint(d.finance_book_id) - 1]
				depreciation_amount += flt(
					value_after_depreciation - flt(book.expected_value_after_useful_life),
					d.precision("depreciation_amount"),
				)

			d.depreciation_amount = depreciation_amount
			accumulated_depreciation += d.depreciation_amount
			d.accumulated_depreciation_amount = flt(
				accumulated_depreciation, d.precision("accumulated_depreciation_amount")
			)

	def validate_expected_value_after_useful_life(self):
		for row in self.get("finance_books"):
			accumulated_depreciation_after_full_schedule = [
				d.accumulated_depreciation_amount
				for d in self.get("schedules")
				if cint(d.finance_book_id) == row.idx
			]

			if accumulated_depreciation_after_full_schedule:
				accumulated_depreciation_after_full_schedule = max(
					accumulated_depreciation_after_full_schedule
				)

				asset_value_after_full_schedule = flt(
					flt(self.gross_purchase_amount) - flt(accumulated_depreciation_after_full_schedule),
					self.precision("gross_purchase_amount"),
				)

				if (
					row.expected_value_after_useful_life
					and row.expected_value_after_useful_life < asset_value_after_full_schedule
				):
					frappe.throw(
						_(
							"Depreciation Row {0}: Expected value after useful life must be greater than or equal to {1}"
						).format(row.idx, asset_value_after_full_schedule)
					)
				elif not row.expected_value_after_useful_life:
					row.expected_value_after_useful_life = asset_value_after_full_schedule

	def validate_cancellation(self):
		if self.status in ("In Maintenance", "Out of Order"):
			frappe.throw(
				_(
					"There are active maintenance or repairs against the asset. You must complete all of them before cancelling the asset."
				)
			)
		if self.status not in ("Submitted", "Partially Depreciated", "Fully Depreciated"):
			frappe.throw(_("Asset cannot be cancelled, as it is already {0}").format(self.status))

	def cancel_movement_entries(self):
		movements = frappe.db.sql(
			"""SELECT asm.name, asm.docstatus
			FROM `tabAsset Movement` asm, `tabAsset Movement Item` asm_item
			WHERE asm_item.parent=asm.name and asm_item.asset=%s and asm.docstatus=1""",
			self.name,
			as_dict=1,
		)

		for movement in movements:
			movement = frappe.get_doc("Asset Movement", movement.get("name"))
			movement.cancel()

	def delete_depreciation_entries(self):
		if self.calculate_depreciation:
			for d in self.get("schedules"):
				if d.journal_entry:
					frappe.get_doc("Journal Entry", d.journal_entry).cancel()
		else:
			depr_entries = self.get_manual_depreciation_entries()

			for depr_entry in depr_entries or []:
				frappe.get_doc("Journal Entry", depr_entry.name).cancel()

			self.db_set(
				"value_after_depreciation",
				(flt(self.gross_purchase_amount) - flt(self.opening_accumulated_depreciation)),
			)

	def set_status(self, status=None):
		"""Get and update status"""
		if not status:
			status = self.get_status()
		self.db_set("status", status)

	def get_status(self):
		"""Returns status based on whether it is draft, submitted, scrapped or depreciated"""
		if self.docstatus == 0:
			status = "Draft"
		elif self.docstatus == 1:
			status = "Submitted"

			if self.journal_entry_for_scrap:
				status = "Scrapped"
			else:
				expected_value_after_useful_life = 0
				value_after_depreciation = self.value_after_depreciation

				if self.calculate_depreciation:
					idx = self.get_default_finance_book_idx() or 0

					expected_value_after_useful_life = self.finance_books[idx].expected_value_after_useful_life
					value_after_depreciation = self.finance_books[idx].value_after_depreciation

				if flt(value_after_depreciation) <= expected_value_after_useful_life:
					status = "Fully Depreciated"
				elif flt(value_after_depreciation) < flt(self.gross_purchase_amount):
					status = "Partially Depreciated"
		elif self.docstatus == 2:
			status = "Cancelled"
		return status

	def get_value_after_depreciation(self, finance_book=None):
		if not self.calculate_depreciation:
			return flt(self.value_after_depreciation, self.precision("gross_purchase_amount"))

		if not finance_book:
			return flt(
				self.get("finance_books")[0].value_after_depreciation, self.precision("gross_purchase_amount")
			)

		for row in self.get("finance_books"):
			if finance_book == row.finance_book:
				return flt(row.value_after_depreciation, self.precision("gross_purchase_amount"))

	def get_default_finance_book_idx(self):
		if not self.get("default_finance_book") and self.company:
			self.default_finance_book = erpnext.get_default_finance_book(self.company)

		if self.get("default_finance_book"):
			for d in self.get("finance_books"):
				if d.finance_book == self.default_finance_book:
					return cint(d.idx) - 1

	def validate_make_gl_entry(self):
		purchase_document = self.get_purchase_document()
		if not purchase_document:
			return False

		asset_bought_with_invoice = purchase_document == self.purchase_invoice
		fixed_asset_account = self.get_fixed_asset_account()

		cwip_enabled = is_cwip_accounting_enabled(self.asset_category)
		cwip_account = self.get_cwip_account(cwip_enabled=cwip_enabled)

		query = """SELECT name FROM `tabGL Entry` WHERE voucher_no = %s and account = %s"""
		if asset_bought_with_invoice:
			# with invoice purchase either expense or cwip has been booked
			expense_booked = frappe.db.sql(query, (purchase_document, fixed_asset_account), as_dict=1)
			if expense_booked:
				# if expense is already booked from invoice then do not make gl entries regardless of cwip enabled/disabled
				return False

			cwip_booked = frappe.db.sql(query, (purchase_document, cwip_account), as_dict=1)
			if cwip_booked:
				# if cwip is booked from invoice then make gl entries regardless of cwip enabled/disabled
				return True
		else:
			# with receipt purchase either cwip has been booked or no entries have been made
			if not cwip_account:
				# if cwip account isn't available do not make gl entries
				return False

			cwip_booked = frappe.db.sql(query, (purchase_document, cwip_account), as_dict=1)
			# if cwip is not booked from receipt then do not make gl entries
			# if cwip is booked from receipt then make gl entries
			return cwip_booked

	def get_purchase_document(self):
		asset_bought_with_invoice = self.purchase_invoice and frappe.db.get_value(
			"Purchase Invoice", self.purchase_invoice, "update_stock"
		)
		purchase_document = self.purchase_invoice if asset_bought_with_invoice else self.purchase_receipt

		return purchase_document

	def get_fixed_asset_account(self):
		fixed_asset_account = get_asset_category_account(
			"fixed_asset_account", None, self.name, None, self.asset_category, self.company
		)
		if not fixed_asset_account:
			frappe.throw(
				_("Set {0} in asset category {1} for company {2}").format(
					frappe.bold("Fixed Asset Account"),
					frappe.bold(self.asset_category),
					frappe.bold(self.company),
				),
				title=_("Account not Found"),
			)
		return fixed_asset_account

	def get_cwip_account(self, cwip_enabled=False):
		cwip_account = None
		try:
			cwip_account = get_asset_account(
				"capital_work_in_progress_account", self.name, self.asset_category, self.company
			)
		except Exception:
			# if no cwip account found in category or company and "cwip is enabled" then raise else silently pass
			if cwip_enabled:
				raise

		return cwip_account

	def make_gl_entries(self):
		gl_entries = []

		purchase_document = self.get_purchase_document()
		fixed_asset_account, cwip_account = self.get_fixed_asset_account(), self.get_cwip_account()

		if (
			purchase_document and self.purchase_receipt_amount and self.available_for_use_date <= nowdate()
		):

			gl_entries.append(
				self.get_gl_dict(
					{
						"account": cwip_account,
						"against": fixed_asset_account,
						"remarks": self.get("remarks") or _("Accounting Entry for Asset"),
						"posting_date": self.available_for_use_date,
						"credit": self.purchase_receipt_amount,
						"credit_in_account_currency": self.purchase_receipt_amount,
						"cost_center": self.cost_center,
					},
					item=self,
				)
			)

			gl_entries.append(
				self.get_gl_dict(
					{
						"account": fixed_asset_account,
						"against": cwip_account,
						"remarks": self.get("remarks") or _("Accounting Entry for Asset"),
						"posting_date": self.available_for_use_date,
						"debit": self.purchase_receipt_amount,
						"debit_in_account_currency": self.purchase_receipt_amount,
						"cost_center": self.cost_center,
					},
					item=self,
				)
			)

		if gl_entries:
			from erpnext.accounts.general_ledger import make_gl_entries

			make_gl_entries(gl_entries)
			self.db_set("booked_fixed_asset", 1)

	@frappe.whitelist()
	def get_manual_depreciation_entries(self):
		(_, _, depreciation_expense_account) = get_depreciation_accounts(self)

		gle = frappe.qb.DocType("GL Entry")

		records = (
			frappe.qb.from_(gle)
			.select(gle.voucher_no.as_("name"), gle.debit.as_("value"), gle.posting_date)
			.where(gle.against_voucher == self.name)
			.where(gle.account == depreciation_expense_account)
			.where(gle.debit != 0)
			.where(gle.is_cancelled == 0)
			.orderby(gle.posting_date)
			.orderby(gle.creation)
		).run(as_dict=True)

		return records

	@frappe.whitelist()
	def get_depreciation_rate(self, args, on_validate=False):
		if isinstance(args, str):
			args = json.loads(args)

		float_precision = cint(frappe.db.get_default("float_precision")) or 2

		if args.get("depreciation_method") == "Double Declining Balance":
			return 200.0 / args.get("total_number_of_depreciations")

		if args.get("depreciation_method") == "Written Down Value":
			if args.get("rate_of_depreciation") and on_validate:
				return args.get("rate_of_depreciation")

			value = flt(args.get("expected_value_after_useful_life")) / flt(self.gross_purchase_amount)
			depreciation_rate = math.pow(value, 1.0 / flt(args.get("total_number_of_depreciations"), 2))
			return flt((100 * (1 - depreciation_rate)), float_precision)

	def get_pro_rata_amt(self, row, depreciation_amount, from_date, to_date):
		days = date_diff(to_date, from_date)
		months = month_diff(to_date, from_date)
		total_days = get_total_days(to_date, row.frequency_of_depreciation)

		return (depreciation_amount * flt(days)) / flt(total_days), days, months


def update_maintenance_status():
	assets = frappe.get_all(
		"Asset", filters={"docstatus": 1, "maintenance_required": 1, "disposal_date": ("is", "not set")}
	)

	for asset in assets:
		asset = frappe.get_doc("Asset", asset.name)
		if frappe.db.exists("Asset Repair", {"asset_name": asset.name, "repair_status": "Pending"}):
			asset.set_status("Out of Order")
		elif frappe.db.exists(
			"Asset Maintenance Task", {"parent": asset.name, "next_due_date": today()}
		):
			asset.set_status("In Maintenance")
		else:
			asset.set_status()


def make_post_gl_entry():
	asset_categories = frappe.db.get_all("Asset Category", fields=["name", "enable_cwip_accounting"])

	for asset_category in asset_categories:
		if cint(asset_category.enable_cwip_accounting):
			assets = frappe.db.sql_list(
				""" select name from `tabAsset`
				where asset_category = %s and ifnull(booked_fixed_asset, 0) = 0
				and available_for_use_date = %s""",
				(asset_category.name, nowdate()),
			)

			for asset in assets:
				doc = frappe.get_doc("Asset", asset)
				doc.make_gl_entries()


def get_asset_naming_series():
	meta = frappe.get_meta("Asset")
	return meta.get_field("naming_series").options


@frappe.whitelist()
def make_sales_invoice(asset, item_code, company, serial_no=None):
	si = frappe.new_doc("Sales Invoice")
	si.company = company
	si.currency = frappe.get_cached_value("Company", company, "default_currency")
	disposal_account, depreciation_cost_center = get_disposal_account_and_cost_center(company)
	si.append(
		"items",
		{
			"item_code": item_code,
			"is_fixed_asset": 1,
			"asset": asset,
			"income_account": disposal_account,
			"serial_no": serial_no,
			"cost_center": depreciation_cost_center,
			"qty": 1,
		},
	)
	si.set_missing_values()
	return si


@frappe.whitelist()
def create_asset_maintenance(asset, item_code, item_name, asset_category, company):
	asset_maintenance = frappe.new_doc("Asset Maintenance")
	asset_maintenance.update(
		{
			"asset_name": asset,
			"company": company,
			"item_code": item_code,
			"item_name": item_name,
			"asset_category": asset_category,
		}
	)
	return asset_maintenance


@frappe.whitelist()
def create_asset_repair(asset, asset_name):
	asset_repair = frappe.new_doc("Asset Repair")
	asset_repair.update({"asset": asset, "asset_name": asset_name})
	return asset_repair


@frappe.whitelist()
def create_asset_value_adjustment(asset, asset_category, company):
	asset_value_adjustment = frappe.new_doc("Asset Value Adjustment")
	asset_value_adjustment.update(
		{"asset": asset, "company": company, "asset_category": asset_category}
	)
	return asset_value_adjustment


@frappe.whitelist()
def transfer_asset(args):
	args = json.loads(args)

	if args.get("serial_no"):
		args["quantity"] = len(args.get("serial_no").split("\n"))

	movement_entry = frappe.new_doc("Asset Movement")
	movement_entry.update(args)
	movement_entry.insert()
	movement_entry.submit()

	frappe.db.commit()

	frappe.msgprint(
		_("Asset Movement record {0} created")
		.format("<a href='/app/Form/Asset Movement/{0}'>{0}</a>")
		.format(movement_entry.name)
	)


@frappe.whitelist()
def get_item_details(item_code, asset_category):
	asset_category_doc = frappe.get_doc("Asset Category", asset_category)
	books = []
	for d in asset_category_doc.finance_books:
		books.append(
			{
				"finance_book": d.finance_book,
				"depreciation_method": d.depreciation_method,
				"total_number_of_depreciations": d.total_number_of_depreciations,
				"frequency_of_depreciation": d.frequency_of_depreciation,
				"start_date": nowdate(),
			}
		)

	return books


def get_asset_account(account_name, asset=None, asset_category=None, company=None):
	account = None
	if asset:
		account = get_asset_category_account(
			account_name, asset=asset, asset_category=asset_category, company=company
		)

	if not asset and not account:
		account = get_asset_category_account(
			account_name, asset_category=asset_category, company=company
		)

	if not account:
		account = frappe.get_cached_value("Company", company, account_name)

	if not account:
		if not asset_category:
			frappe.throw(
				_("Set {0} in company {1}").format(account_name.replace("_", " ").title(), company)
			)
		else:
			frappe.throw(
				_("Set {0} in asset category {1} or company {2}").format(
					account_name.replace("_", " ").title(), asset_category, company
				)
			)

	return account


@frappe.whitelist()
def make_journal_entry(asset_name):
	asset = frappe.get_doc("Asset", asset_name)
	(
		fixed_asset_account,
		accumulated_depreciation_account,
		depreciation_expense_account,
	) = get_depreciation_accounts(asset)

	depreciation_cost_center, depreciation_series = frappe.get_cached_value(
		"Company", asset.company, ["depreciation_cost_center", "series_for_depreciation_entry"]
	)
	depreciation_cost_center = asset.cost_center or depreciation_cost_center

	je = frappe.new_doc("Journal Entry")
	je.voucher_type = "Depreciation Entry"
	je.naming_series = depreciation_series
	je.company = asset.company
	je.remark = "Depreciation Entry against asset {0}".format(asset_name)

	je.append(
		"accounts",
		{
			"account": depreciation_expense_account,
			"reference_type": "Asset",
			"reference_name": asset.name,
			"cost_center": depreciation_cost_center,
		},
	)

	je.append(
		"accounts",
		{
			"account": accumulated_depreciation_account,
			"reference_type": "Asset",
			"reference_name": asset.name,
		},
	)

	return je


@frappe.whitelist()
def make_asset_movement(assets, purpose=None):
	import json

	if isinstance(assets, str):
		assets = json.loads(assets)

	if len(assets) == 0:
		frappe.throw(_("Atleast one asset has to be selected."))

	asset_movement = frappe.new_doc("Asset Movement")
	asset_movement.quantity = len(assets)
	for asset in assets:
		asset = frappe.get_doc("Asset", asset.get("name"))
		asset_movement.company = asset.get("company")
		asset_movement.append(
			"assets",
			{
				"asset": asset.get("name"),
				"source_location": asset.get("location"),
				"from_employee": asset.get("custodian"),
			},
		)

	if asset_movement.get("assets"):
		return asset_movement.as_dict()


def is_cwip_accounting_enabled(asset_category):
	return cint(frappe.db.get_value("Asset Category", asset_category, "enable_cwip_accounting"))


@frappe.whitelist()
def get_asset_value_after_depreciation(asset_name, finance_book=None):
	asset = frappe.get_doc("Asset", asset_name)

	return asset.get_value_after_depreciation(finance_book)


def get_total_days(date, frequency):
	period_start_date = add_months(date, cint(frequency) * -1)

	if is_last_day_of_the_month(date):
		period_start_date = get_last_day(period_start_date)

	return date_diff(date, period_start_date)


@erpnext.allow_regional
def get_depreciation_amount(asset, depreciable_value, row):
	if row.depreciation_method in ("Straight Line", "Manual"):
		# if the Depreciation Schedule is being prepared for the first time
		if not asset.flags.increase_in_asset_life:
			depreciation_amount = (
				flt(asset.gross_purchase_amount) - flt(row.expected_value_after_useful_life)
			) / flt(row.total_number_of_depreciations)

		# if the Depreciation Schedule is being modified after Asset Repair
		else:
			depreciation_amount = (
				flt(row.value_after_depreciation) - flt(row.expected_value_after_useful_life)
			) / (date_diff(asset.to_date, asset.available_for_use_date) / 365)
	else:
		depreciation_amount = flt(depreciable_value * (flt(row.rate_of_depreciation) / 100))

	return depreciation_amount


@frappe.whitelist()
def split_asset(asset_name, split_qty):
	asset = frappe.get_doc("Asset", asset_name)
	split_qty = cint(split_qty)

	if split_qty >= asset.asset_quantity:
		frappe.throw(_("Split qty cannot be grater than or equal to asset qty"))

	remaining_qty = asset.asset_quantity - split_qty

	new_asset = create_new_asset_after_split(asset, split_qty)
	update_existing_asset(asset, remaining_qty)

	return new_asset


def update_existing_asset(asset, remaining_qty):
	remaining_gross_purchase_amount = flt(
		(asset.gross_purchase_amount * remaining_qty) / asset.asset_quantity
	)
	opening_accumulated_depreciation = flt(
		(asset.opening_accumulated_depreciation * remaining_qty) / asset.asset_quantity
	)

	frappe.db.set_value(
		"Asset",
		asset.name,
		{
			"opening_accumulated_depreciation": opening_accumulated_depreciation,
			"gross_purchase_amount": remaining_gross_purchase_amount,
			"asset_quantity": remaining_qty,
		},
	)

	for finance_book in asset.get("finance_books"):
		value_after_depreciation = flt(
			(finance_book.value_after_depreciation * remaining_qty) / asset.asset_quantity
		)
		expected_value_after_useful_life = flt(
			(finance_book.expected_value_after_useful_life * remaining_qty) / asset.asset_quantity
		)
		frappe.db.set_value(
			"Asset Finance Book", finance_book.name, "value_after_depreciation", value_after_depreciation
		)
		frappe.db.set_value(
			"Asset Finance Book",
			finance_book.name,
			"expected_value_after_useful_life",
			expected_value_after_useful_life,
		)

	processed_finance_books = []

	for term in asset.get("schedules"):
		if int(term.finance_book_id) not in processed_finance_books:
			accumulated_depreciation = 0
			processed_finance_books.append(int(term.finance_book_id))

		depreciation_amount = flt((term.depreciation_amount * remaining_qty) / asset.asset_quantity)
		frappe.db.set_value(
			"Depreciation Schedule", term.name, "depreciation_amount", depreciation_amount
		)
		accumulated_depreciation += depreciation_amount
		frappe.db.set_value(
			"Depreciation Schedule", term.name, "accumulated_depreciation_amount", accumulated_depreciation
		)


def create_new_asset_after_split(asset, split_qty):
	new_asset = frappe.copy_doc(asset)
	new_gross_purchase_amount = flt((asset.gross_purchase_amount * split_qty) / asset.asset_quantity)
	opening_accumulated_depreciation = flt(
		(asset.opening_accumulated_depreciation * split_qty) / asset.asset_quantity
	)

	new_asset.gross_purchase_amount = new_gross_purchase_amount
	new_asset.opening_accumulated_depreciation = opening_accumulated_depreciation
	new_asset.asset_quantity = split_qty
	new_asset.split_from = asset.name

	for finance_book in new_asset.get("finance_books"):
		finance_book.value_after_depreciation = flt(
			(finance_book.value_after_depreciation * split_qty) / asset.asset_quantity
		)
		finance_book.expected_value_after_useful_life = flt(
			(finance_book.expected_value_after_useful_life * split_qty) / asset.asset_quantity
		)

	processed_finance_books = []

	for term in new_asset.get("schedules"):
		if int(term.finance_book_id) not in processed_finance_books:
			accumulated_depreciation = 0
			processed_finance_books.append(int(term.finance_book_id))

		depreciation_amount = flt((term.depreciation_amount * split_qty) / asset.asset_quantity)
		term.depreciation_amount = depreciation_amount
		accumulated_depreciation += depreciation_amount
		term.accumulated_depreciation_amount = accumulated_depreciation

	new_asset.submit()
	new_asset.set_status()

	for term in new_asset.get("schedules"):
		# Update references in JV
		if term.journal_entry:
			add_reference_in_jv_on_split(
				term.journal_entry, new_asset.name, asset.name, term.depreciation_amount
			)

	return new_asset


def add_reference_in_jv_on_split(entry_name, new_asset_name, old_asset_name, depreciation_amount):
	journal_entry = frappe.get_doc("Journal Entry", entry_name)
	entries_to_add = []
	idx = len(journal_entry.get("accounts")) + 1

	for account in journal_entry.get("accounts"):
		if account.reference_name == old_asset_name:
			entries_to_add.append(frappe.copy_doc(account).as_dict())
			if account.credit:
				account.credit = account.credit - depreciation_amount
				account.credit_in_account_currency = (
					account.credit_in_account_currency - account.exchange_rate * depreciation_amount
				)
			elif account.debit:
				account.debit = account.debit - depreciation_amount
				account.debit_in_account_currency = (
					account.debit_in_account_currency - account.exchange_rate * depreciation_amount
				)

	for entry in entries_to_add:
		entry.reference_name = new_asset_name
		if entry.credit:
			entry.credit = depreciation_amount
			entry.credit_in_account_currency = entry.exchange_rate * depreciation_amount
		elif entry.debit:
			entry.debit = depreciation_amount
			entry.debit_in_account_currency = entry.exchange_rate * depreciation_amount

		entry.idx = idx
		idx += 1

		journal_entry.append("accounts", entry)

	journal_entry.flags.ignore_validate_update_after_submit = True
	journal_entry.save()

	# Repost GL Entries
	journal_entry.docstatus = 2
	journal_entry.make_gl_entries(1)
	journal_entry.docstatus = 1
	journal_entry.make_gl_entries()
