# Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import json
import math

import frappe
from frappe import _
from frappe.utils import (
	cint,
	flt,
	get_datetime,
	get_last_day,
	get_link_to_form,
	getdate,
	nowdate,
	today,
)

import erpnext
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import get_dimensions
from erpnext.accounts.general_ledger import make_reverse_gl_entries
from erpnext.assets.doctype.asset.depreciation import (
	get_comma_separated_links,
	get_depreciation_accounts,
	get_disposal_account_and_cost_center,
)
from erpnext.assets.doctype.asset_activity.asset_activity import add_asset_activity
from erpnext.assets.doctype.asset_category.asset_category import get_asset_category_account
from erpnext.assets.doctype.asset_depreciation_schedule.asset_depreciation_schedule import (
	cancel_asset_depr_schedules,
	convert_draft_asset_depr_schedules_into_active,
	get_asset_depr_schedule_doc,
	get_depr_schedule,
	make_draft_asset_depr_schedules,
	make_draft_asset_depr_schedules_if_not_present,
	update_draft_asset_depr_schedules,
)
from erpnext.controllers.accounts_controller import AccountsController


class Asset(AccountsController):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.assets.doctype.asset_finance_book.asset_finance_book import AssetFinanceBook

		additional_asset_cost: DF.Currency
		amended_from: DF.Link | None
		asset_category: DF.Link | None
		asset_name: DF.Data
		asset_owner: DF.Literal["", "Company", "Supplier", "Customer"]
		asset_owner_company: DF.Link | None
		asset_quantity: DF.Int
		available_for_use_date: DF.Date | None
		booked_fixed_asset: DF.Check
		calculate_depreciation: DF.Check
		company: DF.Link
		comprehensive_insurance: DF.Data | None
		cost_center: DF.Link | None
		custodian: DF.Link | None
		customer: DF.Link | None
		default_finance_book: DF.Link | None
		department: DF.Link | None
		depr_entry_posting_status: DF.Literal["", "Successful", "Failed"]
		depreciation_method: DF.Literal["", "Straight Line", "Double Declining Balance", "Manual"]
		disposal_date: DF.Date | None
		finance_books: DF.Table[AssetFinanceBook]
		frequency_of_depreciation: DF.Int
		gross_purchase_amount: DF.Currency
		image: DF.AttachImage | None
		insurance_end_date: DF.Date | None
		insurance_start_date: DF.Date | None
		insured_value: DF.Data | None
		insurer: DF.Data | None
		is_composite_asset: DF.Check
		is_existing_asset: DF.Check
		is_fully_depreciated: DF.Check
		item_code: DF.Link
		item_name: DF.ReadOnly | None
		journal_entry_for_scrap: DF.Link | None
		location: DF.Link
		maintenance_required: DF.Check
		naming_series: DF.Literal["ACC-ASS-.YYYY.-"]
		next_depreciation_date: DF.Date | None
		opening_accumulated_depreciation: DF.Currency
		opening_number_of_booked_depreciations: DF.Int
		policy_number: DF.Data | None
		purchase_amount: DF.Currency
		purchase_date: DF.Date | None
		purchase_invoice: DF.Link | None
		purchase_invoice_item: DF.Link | None
		purchase_receipt: DF.Link | None
		purchase_receipt_item: DF.Link | None
		split_from: DF.Link | None
		status: DF.Literal[
			"Draft",
			"Submitted",
			"Partially Depreciated",
			"Fully Depreciated",
			"Sold",
			"Scrapped",
			"In Maintenance",
			"Out of Order",
			"Issue",
			"Receipt",
			"Capitalized",
			"Work In Progress",
		]
		supplier: DF.Link | None
		total_asset_cost: DF.Currency
		total_number_of_depreciations: DF.Int
		value_after_depreciation: DF.Currency
	# end: auto-generated types

	def validate(self):
		self.validate_precision()
		self.validate_asset_values()
		self.validate_asset_and_reference()
		self.validate_item()
		self.validate_cost_center()
		self.set_missing_values()
		self.validate_gross_and_purchase_amount()
		self.validate_finance_books()

		if not self.split_from:
			self.prepare_depreciation_data()

			if self.calculate_depreciation:
				update_draft_asset_depr_schedules(self)

				if frappe.db.exists("Asset", self.name):
					asset_depr_schedules_names = make_draft_asset_depr_schedules_if_not_present(self)

					if asset_depr_schedules_names:
						asset_depr_schedules_links = get_comma_separated_links(
							asset_depr_schedules_names, "Asset Depreciation Schedule"
						)
						frappe.msgprint(
							_(
								"Asset Depreciation Schedules created:<br>{0}<br><br>Please check, edit if needed, and submit the Asset."
							).format(asset_depr_schedules_links)
						)
		self.validate_expected_value_after_useful_life()
		self.set_total_booked_depreciations()
		self.total_asset_cost = self.gross_purchase_amount
		self.status = self.get_status()

	def on_submit(self):
		self.validate_in_use_date()
		self.make_asset_movement()
		if not self.booked_fixed_asset and self.validate_make_gl_entry():
			self.make_gl_entries()
		if self.calculate_depreciation and not self.split_from:
			convert_draft_asset_depr_schedules_into_active(self)
		self.set_status()
		add_asset_activity(self.name, _("Asset submitted"))

	def on_cancel(self):
		self.validate_cancellation()
		self.cancel_movement_entries()
		self.reload()
		self.delete_depreciation_entries()
		cancel_asset_depr_schedules(self)
		self.set_status()
		self.ignore_linked_doctypes = ("GL Entry", "Stock Ledger Entry")
		make_reverse_gl_entries(voucher_type="Asset", voucher_no=self.name)
		self.db_set("booked_fixed_asset", 0)
		add_asset_activity(self.name, _("Asset cancelled"))

	def after_insert(self):
		if self.calculate_depreciation and not self.split_from:
			asset_depr_schedules_names = make_draft_asset_depr_schedules(self)
			asset_depr_schedules_links = get_comma_separated_links(
				asset_depr_schedules_names, "Asset Depreciation Schedule"
			)
			frappe.msgprint(
				_(
					"Asset Depreciation Schedules created:<br>{0}<br><br>Please check, edit if needed, and submit the Asset."
				).format(asset_depr_schedules_links)
			)
		if (
			not frappe.db.exists(
				{
					"doctype": "Asset Activity",
					"asset": self.name,
				}
			)
			and not self.flags.asset_created_via_asset_capitalization
		):
			add_asset_activity(self.name, _("Asset created"))

	def after_delete(self):
		add_asset_activity(self.name, _("Asset deleted"))

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
			frappe.throw(_("Purchase Invoice cannot be made against an existing asset {0}").format(self.name))

	def prepare_depreciation_data(self):
		if self.calculate_depreciation:
			self.value_after_depreciation = 0
			self.set_depreciation_rate()
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
		if self.cost_center:
			cost_center_company, cost_center_is_group = frappe.db.get_value(
				"Cost Center", self.cost_center, ["company", "is_group"]
			)
			if cost_center_company != self.company:
				frappe.throw(
					_("Cost Center {} doesn't belong to Company {}").format(
						frappe.bold(self.cost_center), frappe.bold(self.company)
					),
					title=_("Invalid Cost Center"),
				)
			if cost_center_is_group:
				frappe.throw(
					_(
						"Cost Center {} is a group cost center and group cost centers cannot be used in transactions"
					).format(frappe.bold(self.cost_center)),
					title=_("Invalid Cost Center"),
				)

		else:
			if not frappe.get_cached_value("Company", self.company, "depreciation_cost_center"):
				frappe.throw(
					_(
						"Please set a Cost Center for the Asset or set an Asset Depreciation Cost Center for the Company {}"
					).format(frappe.bold(self.company)),
					title=_("Missing Cost Center"),
				)

	def validate_in_use_date(self):
		if not self.available_for_use_date:
			frappe.throw(_("Available for use date is required"))

		for d in self.finance_books:
			if getdate(d.depreciation_start_date) < getdate(self.available_for_use_date):
				frappe.throw(
					_(
						"Depreciation Row {0}: Depreciation Posting Date cannot be before Available-for-use Date"
					).format(d.idx),
					title=_("Incorrect Date"),
				)

	def set_missing_values(self):
		if not self.asset_category:
			self.asset_category = frappe.get_cached_value("Item", self.item_code, "asset_category")

		if self.item_code and not self.get("finance_books"):
			finance_books = get_item_details(self.item_code, self.asset_category, self.gross_purchase_amount)
			self.set("finance_books", finance_books)

	def validate_finance_books(self):
		if not self.calculate_depreciation or len(self.finance_books) == 1:
			return

		finance_books = set()

		for d in self.finance_books:
			if d.finance_book in finance_books:
				frappe.throw(
					_("Row #{}: Please use a different Finance Book.").format(d.idx),
					title=_("Duplicate Finance Book"),
				)
			else:
				finance_books.add(d.finance_book)

			if not d.finance_book:
				frappe.throw(
					_("Row #{}: Finance Book should not be empty since you're using multiple.").format(d.idx),
					title=_("Missing Finance Book"),
				)

	def validate_precision(self):
		if self.gross_purchase_amount:
			self.gross_purchase_amount = flt(
				self.gross_purchase_amount, self.precision("gross_purchase_amount")
			)

		if self.opening_accumulated_depreciation:
			self.opening_accumulated_depreciation = flt(
				self.opening_accumulated_depreciation, self.precision("opening_accumulated_depreciation")
			)

	def validate_asset_values(self):
		if not self.asset_category:
			self.asset_category = frappe.get_cached_value("Item", self.item_code, "asset_category")

		if not flt(self.gross_purchase_amount) and not self.is_composite_asset:
			frappe.throw(_("Gross Purchase Amount is mandatory"), frappe.MandatoryError)

		if is_cwip_accounting_enabled(self.asset_category):
			if (
				not self.is_existing_asset
				and not self.is_composite_asset
				and not self.purchase_receipt
				and not self.purchase_invoice
			):
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
					_("Update stock must be enabled for the purchase invoice {0}").format(
						self.purchase_invoice
					)
				)

		if not self.calculate_depreciation:
			return
		else:
			if not self.finance_books:
				frappe.throw(_("Enter depreciation details"))
			if self.is_fully_depreciated:
				frappe.throw(_("Depreciation cannot be calculated for fully depreciated assets"))

		if self.is_existing_asset:
			return

		if self.available_for_use_date and getdate(self.available_for_use_date) < getdate(self.purchase_date):
			frappe.throw(_("Available-for-use Date should be after purchase date"))

	def validate_gross_and_purchase_amount(self):
		if self.is_existing_asset:
			return

		if self.gross_purchase_amount and self.gross_purchase_amount != self.purchase_amount:
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
			transaction_date = get_datetime(f"{posting_date} {posting_time}")
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

	def validate_asset_finance_books(self, row):
		row.expected_value_after_useful_life = flt(
			row.expected_value_after_useful_life, self.precision("gross_purchase_amount")
		)
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
					_("Row {0}: Depreciation Start Date is required").format(row.idx),
					title=_("Invalid Schedule"),
				)
			row.depreciation_start_date = get_last_day(self.available_for_use_date)

		if not self.is_existing_asset:
			self.opening_accumulated_depreciation = 0
			self.opening_number_of_booked_depreciations = 0
		else:
			depreciable_amount = flt(
				flt(self.gross_purchase_amount) - flt(row.expected_value_after_useful_life),
				self.precision("gross_purchase_amount"),
			)
			if flt(self.opening_accumulated_depreciation) > depreciable_amount:
				frappe.throw(
					_("Opening Accumulated Depreciation must be less than or equal to {0}").format(
						depreciable_amount
					)
				)

			if self.opening_accumulated_depreciation:
				if not self.opening_number_of_booked_depreciations:
					frappe.throw(_("Please set Opening Number of Booked Depreciations"))
			else:
				self.opening_number_of_booked_depreciations = 0

			if flt(row.total_number_of_depreciations) <= cint(self.opening_number_of_booked_depreciations):
				frappe.throw(
					_(
						"Row {0}: Total Number of Depreciations cannot be less than or equal to Opening Number of Booked Depreciations"
					).format(row.idx),
					title=_("Invalid Schedule"),
				)

		if row.depreciation_start_date and getdate(row.depreciation_start_date) < getdate(self.purchase_date):
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

	def set_total_booked_depreciations(self):
		# set value of total number of booked depreciations field
		for fb_row in self.get("finance_books"):
			total_number_of_booked_depreciations = self.opening_number_of_booked_depreciations
			depr_schedule = get_depr_schedule(self.name, "Active", fb_row.finance_book)
			if depr_schedule:
				for je in depr_schedule:
					if je.journal_entry:
						total_number_of_booked_depreciations += 1
			fb_row.db_set("total_number_of_booked_depreciations", total_number_of_booked_depreciations)

	def validate_expected_value_after_useful_life(self):
		for row in self.get("finance_books"):
			depr_schedule = get_depr_schedule(self.name, "Draft", row.finance_book)
			if not depr_schedule:
				continue

			accumulated_depreciation_after_full_schedule = [
				d.accumulated_depreciation_amount for d in depr_schedule
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
			for row in self.get("finance_books"):
				depr_schedule = get_depr_schedule(self.name, "Active", row.finance_book)

				for d in depr_schedule or []:
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
					expected_value_after_useful_life = self.finance_books[
						idx
					].expected_value_after_useful_life
					value_after_depreciation = self.finance_books[idx].value_after_depreciation

				if (
					flt(value_after_depreciation) <= expected_value_after_useful_life
					or self.is_fully_depreciated
				):
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

	@frappe.whitelist()
	def get_manual_depreciation_entries(self):
		(_, _, depreciation_expense_account) = get_depreciation_accounts(self.asset_category, self.company)

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

	def validate_make_gl_entry(self):
		if self.is_composite_asset:
			return True

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
					frappe.bold(_("Fixed Asset Account")),
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
		if self.check_asset_capitalization_gl_entries():
			return

		gl_entries = []

		purchase_document = self.get_purchase_document()
		fixed_asset_account, cwip_account = self.get_fixed_asset_account(), self.get_cwip_account()

		if (self.is_composite_asset or (purchase_document and self.purchase_amount)) and getdate(
			self.available_for_use_date
		) <= getdate():
			gl_entries.append(
				self.get_gl_dict(
					{
						"account": cwip_account,
						"against": fixed_asset_account,
						"remarks": self.get("remarks") or _("Accounting Entry for Asset"),
						"posting_date": self.available_for_use_date,
						"credit": self.purchase_amount,
						"credit_in_account_currency": self.purchase_amount,
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
						"debit": self.purchase_amount,
						"debit_in_account_currency": self.purchase_amount,
						"cost_center": self.cost_center,
					},
					item=self,
				)
			)

		if gl_entries:
			from erpnext.accounts.general_ledger import make_gl_entries

			make_gl_entries(gl_entries)
			self.db_set("booked_fixed_asset", 1)

	def check_asset_capitalization_gl_entries(self):
		if self.is_composite_asset:
			result = frappe.db.get_value(
				"Asset Capitalization",
				{"target_asset": self.name, "docstatus": 1},
				["name", "target_fixed_asset_account"],
			)

			if result:
				asset_capitalization, target_fixed_asset_account = result
				# Check GL entries for the retrieved Asset Capitalization and target fixed asset account
				return has_gl_entries(
					"Asset Capitalization", asset_capitalization, target_fixed_asset_account
				)
			# return if there are no submitted capitalization for given asset
			return True
		return False

	@frappe.whitelist()
	def get_depreciation_rate(self, args, on_validate=False):
		if isinstance(args, str):
			args = json.loads(args)

		float_precision = cint(frappe.db.get_default("float_precision")) or 2

		if args.get("depreciation_method") == "Double Declining Balance":
			return 200.0 / (
				(
					flt(args.get("total_number_of_depreciations"), 2)
					* flt(args.get("frequency_of_depreciation"))
				)
				/ 12
			)

		if args.get("depreciation_method") == "Written Down Value":
			if (
				args.get("rate_of_depreciation")
				and on_validate
				and not self.flags.increase_in_asset_value_due_to_repair
			):
				return args.get("rate_of_depreciation")

			if args.get("rate_of_depreciation") and not flt(args.get("expected_value_after_useful_life")):
				return args.get("rate_of_depreciation")

			if self.flags.increase_in_asset_value_due_to_repair:
				value = flt(args.get("expected_value_after_useful_life")) / flt(
					args.get("value_after_depreciation")
				)
			else:
				value = flt(args.get("expected_value_after_useful_life")) / (
					flt(self.gross_purchase_amount) - flt(self.opening_accumulated_depreciation)
				)

			depreciation_rate = math.pow(
				value,
				1.0
				/ (
					(
						(
							flt(args.get("total_number_of_depreciations"), 2)
							- flt(self.opening_number_of_booked_depreciations)
						)
						* flt(args.get("frequency_of_depreciation"))
					)
					/ 12
				),
			)

			return flt((100 * (1 - depreciation_rate)), float_precision)


def has_gl_entries(doctype, docname, target_account):
	gl_entry = frappe.qb.DocType("GL Entry")
	gl_entries = (
		frappe.qb.from_(gl_entry)
		.select(gl_entry.account)
		.where(
			(gl_entry.voucher_type == doctype)
			& (gl_entry.voucher_no == docname)
			& (gl_entry.debit != 0)
			& (gl_entry.account == target_account)
		)
		.run(as_dict=True)
	)
	return len(gl_entries) > 0


def update_maintenance_status():
	assets = frappe.get_all(
		"Asset", filters={"docstatus": 1, "maintenance_required": 1, "disposal_date": ("is", "not set")}
	)

	for asset in assets:
		asset = frappe.get_doc("Asset", asset.name)
		if frappe.db.exists("Asset Repair", {"asset_name": asset.name, "repair_status": "Pending"}):
			asset.set_status("Out of Order")
		elif frappe.db.exists("Asset Maintenance Task", {"parent": asset.name, "next_due_date": today()}):
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
	asset_doc = frappe.get_doc("Asset", asset)
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

	accounting_dimensions = get_dimensions(with_cost_center_and_project=True)
	for dimension in accounting_dimensions[0]:
		si.update(
			{
				dimension["fieldname"]: asset_doc.get(dimension["fieldname"])
				or dimension.get("default_dimension")
			}
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
def create_asset_repair(company, asset, asset_name):
	asset_repair = frappe.new_doc("Asset Repair")
	asset_repair.update({"company": company, "asset": asset, "asset_name": asset_name})
	return asset_repair


@frappe.whitelist()
def create_asset_capitalization(company, asset, asset_name, item_code):
	asset_capitalization = frappe.new_doc("Asset Capitalization")
	asset_capitalization.update(
		{
			"target_asset": asset,
			"company": company,
			"capitalization_method": "Choose a WIP composite asset",
			"target_asset_name": asset_name,
			"target_item_code": item_code,
		}
	)
	return asset_capitalization


@frappe.whitelist()
def create_asset_value_adjustment(asset, asset_category, company):
	asset_value_adjustment = frappe.new_doc("Asset Value Adjustment")
	asset_value_adjustment.update({"asset": asset, "company": company, "asset_category": asset_category})
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
def get_item_details(item_code, asset_category, gross_purchase_amount):
	asset_category_doc = frappe.get_cached_doc("Asset Category", asset_category)
	books = []
	for d in asset_category_doc.finance_books:
		books.append(
			{
				"finance_book": d.finance_book,
				"depreciation_method": d.depreciation_method,
				"total_number_of_depreciations": d.total_number_of_depreciations,
				"frequency_of_depreciation": d.frequency_of_depreciation,
				"daily_prorata_based": d.daily_prorata_based,
				"shift_based": d.shift_based,
				"salvage_value_percentage": d.salvage_value_percentage,
				"expected_value_after_useful_life": flt(gross_purchase_amount)
				* flt(d.salvage_value_percentage / 100),
				"depreciation_start_date": d.depreciation_start_date or nowdate(),
				"rate_of_depreciation": d.rate_of_depreciation,
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
		account = get_asset_category_account(account_name, asset_category=asset_category, company=company)

	if not account:
		account = frappe.get_cached_value("Company", company, account_name)

	if not account:
		if not asset_category:
			frappe.throw(_("Set {0} in company {1}").format(account_name.replace("_", " ").title(), company))
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
		_,
		accumulated_depreciation_account,
		depreciation_expense_account,
	) = get_depreciation_accounts(asset.asset_category, asset.company)

	depreciation_cost_center, depreciation_series = frappe.get_cached_value(
		"Company", asset.company, ["depreciation_cost_center", "series_for_depreciation_entry"]
	)
	depreciation_cost_center = asset.cost_center or depreciation_cost_center

	je = frappe.new_doc("Journal Entry")
	je.voucher_type = "Depreciation Entry"
	je.naming_series = depreciation_series
	je.company = asset.company
	je.remark = f"Depreciation Entry against asset {asset_name}"

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
	if not asset.calculate_depreciation:
		return flt(asset.value_after_depreciation)

	return asset.get_value_after_depreciation(finance_book)


@frappe.whitelist()
def has_active_capitalization(asset):
	active_capitalizations = frappe.db.count(
		"Asset Capitalization", filters={"target_asset": asset, "docstatus": 1}
	)
	return active_capitalizations > 0


@frappe.whitelist()
def split_asset(asset_name, split_qty):
	asset = frappe.get_doc("Asset", asset_name)
	split_qty = cint(split_qty)

	if split_qty >= asset.asset_quantity:
		frappe.throw(_("Split qty cannot be grater than or equal to asset qty"))

	remaining_qty = asset.asset_quantity - split_qty

	new_asset = create_new_asset_after_split(asset, split_qty)
	update_existing_asset(asset, remaining_qty, new_asset.name)

	return new_asset


def update_existing_asset(asset, remaining_qty, new_asset_name):
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

	add_asset_activity(
		asset.name,
		_("Asset updated after being split into Asset {0}").format(get_link_to_form("Asset", new_asset_name)),
	)

	for row in asset.get("finance_books"):
		value_after_depreciation = flt((row.value_after_depreciation * remaining_qty) / asset.asset_quantity)
		expected_value_after_useful_life = flt(
			(row.expected_value_after_useful_life * remaining_qty) / asset.asset_quantity
		)
		frappe.db.set_value(
			"Asset Finance Book", row.name, "value_after_depreciation", value_after_depreciation
		)
		frappe.db.set_value(
			"Asset Finance Book",
			row.name,
			"expected_value_after_useful_life",
			expected_value_after_useful_life,
		)

		current_asset_depr_schedule_doc = get_asset_depr_schedule_doc(asset.name, "Active", row.finance_book)
		new_asset_depr_schedule_doc = frappe.copy_doc(current_asset_depr_schedule_doc)

		new_asset_depr_schedule_doc.set_draft_asset_depr_schedule_details(asset, row)

		accumulated_depreciation = 0

		for term in new_asset_depr_schedule_doc.get("depreciation_schedule"):
			depreciation_amount = flt((term.depreciation_amount * remaining_qty) / asset.asset_quantity)
			term.depreciation_amount = depreciation_amount
			accumulated_depreciation += depreciation_amount
			term.accumulated_depreciation_amount = accumulated_depreciation

		notes = _(
			"This schedule was created when Asset {0} was updated after being split into new Asset {1}."
		).format(get_link_to_form(asset.doctype, asset.name), get_link_to_form(asset.doctype, new_asset_name))
		new_asset_depr_schedule_doc.notes = notes

		current_asset_depr_schedule_doc.flags.should_not_cancel_depreciation_entries = True
		current_asset_depr_schedule_doc.cancel()

		new_asset_depr_schedule_doc.submit()


def create_new_asset_after_split(asset, split_qty):
	new_asset = frappe.copy_doc(asset)
	new_gross_purchase_amount = flt((asset.gross_purchase_amount * split_qty) / asset.asset_quantity)
	opening_accumulated_depreciation = flt(
		(asset.opening_accumulated_depreciation * split_qty) / asset.asset_quantity
	)

	new_asset.gross_purchase_amount = new_gross_purchase_amount
	if asset.purchase_amount:
		new_asset.purchase_amount = new_gross_purchase_amount
	new_asset.opening_accumulated_depreciation = opening_accumulated_depreciation
	new_asset.asset_quantity = split_qty
	new_asset.split_from = asset.name

	for row in new_asset.get("finance_books"):
		row.value_after_depreciation = flt((row.value_after_depreciation * split_qty) / asset.asset_quantity)
		row.expected_value_after_useful_life = flt(
			(row.expected_value_after_useful_life * split_qty) / asset.asset_quantity
		)

	new_asset.insert()

	add_asset_activity(
		new_asset.name,
		_("Asset created after being split from Asset {0}").format(get_link_to_form("Asset", asset.name)),
	)

	new_asset.submit()
	new_asset.set_status()

	for row in new_asset.get("finance_books"):
		current_asset_depr_schedule_doc = get_asset_depr_schedule_doc(asset.name, "Active", row.finance_book)
		if not current_asset_depr_schedule_doc:
			continue
		new_asset_depr_schedule_doc = frappe.copy_doc(current_asset_depr_schedule_doc)

		new_asset_depr_schedule_doc.set_draft_asset_depr_schedule_details(new_asset, row)

		accumulated_depreciation = 0

		for term in new_asset_depr_schedule_doc.get("depreciation_schedule"):
			depreciation_amount = flt((term.depreciation_amount * split_qty) / asset.asset_quantity)
			term.depreciation_amount = depreciation_amount
			accumulated_depreciation += depreciation_amount
			term.accumulated_depreciation_amount = accumulated_depreciation

		notes = _("This schedule was created when new Asset {0} was split from Asset {1}.").format(
			get_link_to_form(new_asset.doctype, new_asset.name), get_link_to_form(asset.doctype, asset.name)
		)
		new_asset_depr_schedule_doc.notes = notes

		new_asset_depr_schedule_doc.submit()

	for row in new_asset.get("finance_books"):
		depr_schedule = get_depr_schedule(new_asset.name, "Active", row.finance_book)
		for term in depr_schedule:
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
