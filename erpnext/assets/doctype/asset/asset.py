# -*- coding: utf-8 -*-
# Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe import _
from frappe.utils import flt, add_months, cint, nowdate, getdate, today, date_diff
from frappe.model.document import Document
from erpnext.assets.doctype.asset_category.asset_category import get_asset_category_account
from erpnext.assets.doctype.asset.depreciation \
	import get_disposal_account_and_cost_center, get_depreciation_accounts
from erpnext.accounting.general_ledger import make_gl_entries, delete_gl_entries
from erpnext.accounting.utils import get_account_currency
from erpnext.controllers.accounts_controller import AccountsController

class Asset(AccountsController):
	def validate(self):
		self.validate_asset_values()
		self.validate_item()
		self.set_missing_values()
		if self.calculate_depreciation:
			self.make_depreciation_schedule()
			self.set_accumulated_depreciation()
		else:
			self.finance_books = []
		if self.get("schedules"):
			self.validate_expected_value_after_useful_life()

		self.status = self.get_status()

	def on_submit(self):
		self.validate_in_use_date()
		self.set_status()
		self.update_stock_movement()
		if not self.booked_fixed_asset:
			self.make_gl_entries()

	def on_cancel(self):
		self.validate_cancellation()
		self.delete_depreciation_entries()
		self.set_status()
		delete_gl_entries(voucher_type='Asset', voucher_no=self.name)
		self.db_set('booked_fixed_asset', 0)

	def validate_item(self):
		item = frappe.get_cached_value("Item", self.item_code,
			["is_fixed_asset", "is_stock_item", "disabled"], as_dict=1)
		if not item:
			frappe.throw(_("Item {0} does not exist").format(self.item_code))
		elif item.disabled:
			frappe.throw(_("Item {0} has been disabled").format(self.item_code))
		elif not item.is_fixed_asset:
			frappe.throw(_("Item {0} must be a Fixed Asset Item").format(self.item_code))
		elif item.is_stock_item:
			frappe.throw(_("Item {0} must be a non-stock item").format(self.item_code))

	def validate_in_use_date(self):
		if not self.available_for_use_date:
			frappe.throw(_("Available for use date is required"))

	def set_missing_values(self):
		if not self.asset_category:
			self.asset_category = frappe.get_cached_value("Item", self.item_code, "asset_category")

		if self.item_code and not self.get('finance_books'):
			finance_books = get_item_details(self.item_code, self.asset_category)
			self.set('finance_books', finance_books)

	def validate_asset_values(self):
		if not flt(self.gross_purchase_amount):
			frappe.throw(_("Gross Purchase Amount is mandatory"), frappe.MandatoryError)

		if not self.is_existing_asset and not (self.purchase_receipt or self.purchase_invoice):
			frappe.throw(_("Please create purchase receipt or purchase invoice for the item {0}").
				format(self.item_code))

		if (not self.purchase_receipt and self.purchase_invoice
			and not frappe.db.get_value('Purchase Invoice', self.purchase_invoice, 'update_stock')):
			frappe.throw(_("Update stock must be enable for the purchase invoice {0}").
				format(self.purchase_invoice))

		if not self.calculate_depreciation:
			return
		elif not self.finance_books:
			frappe.throw(_("Enter depreciation details"))

		if self.is_existing_asset:
			return

		date =  nowdate()
		docname = self.purchase_receipt or self.purchase_invoice
		if docname:
			doctype = 'Purchase Receipt' if self.purchase_receipt else 'Purchase Invoice'
			date = frappe.db.get_value(doctype, docname, 'posting_date')

		if self.available_for_use_date and getdate(self.available_for_use_date) < getdate(date):
			frappe.throw(_("Available-for-use Date should be after purchase date"))

	def make_depreciation_schedule(self):
		if self.depreciation_method != 'Manual':
			self.schedules = []

		if not self.get("schedules") and self.available_for_use_date:
			total_depreciations = sum([d.total_number_of_depreciations for d in self.get('finance_books')])

			for d in self.get('finance_books'):
				self.validate_asset_finance_books(d)

				value_after_depreciation = (flt(self.gross_purchase_amount) -
					flt(self.opening_accumulated_depreciation))

				d.value_after_depreciation = value_after_depreciation

				no_of_depreciations = cint(d.total_number_of_depreciations - 1) - cint(self.number_of_depreciations_booked)
				end_date = add_months(d.depreciation_start_date,
					no_of_depreciations * cint(d.frequency_of_depreciation))

				total_days = date_diff(end_date, self.available_for_use_date)
				rate_per_day = value_after_depreciation / total_days

				number_of_pending_depreciations = cint(d.total_number_of_depreciations) - \
					cint(self.number_of_depreciations_booked)

				from_date = self.available_for_use_date
				if number_of_pending_depreciations:
					next_depr_date = getdate(add_months(self.available_for_use_date,
						number_of_pending_depreciations * 12))
					if  (cint(frappe.db.get_value("Asset Settings", None, "schedule_based_on_fiscal_year")) == 1
						and getdate(d.depreciation_start_date) < next_depr_date):

						number_of_pending_depreciations += 1
						for n in range(number_of_pending_depreciations):
							if n == list(range(number_of_pending_depreciations))[-1]:
								schedule_date = add_months(self.available_for_use_date, n * 12)
								previous_scheduled_date = add_months(d.depreciation_start_date, (n-1) * 12)
								depreciation_amount = \
									self.get_depreciation_amount_prorata_temporis(value_after_depreciation,
										d, previous_scheduled_date, schedule_date)

							elif n == list(range(number_of_pending_depreciations))[0]:
								schedule_date = d.depreciation_start_date
								depreciation_amount = \
									self.get_depreciation_amount_prorata_temporis(value_after_depreciation,
										d, self.available_for_use_date, schedule_date)

							else:
								schedule_date = add_months(d.depreciation_start_date, n * 12)
								depreciation_amount = \
									 self.get_depreciation_amount_prorata_temporis(value_after_depreciation, d)

							if value_after_depreciation != 0:
								value_after_depreciation -= flt(depreciation_amount)

								self.append("schedules", {
									"schedule_date": schedule_date,
									"depreciation_amount": depreciation_amount,
									"depreciation_method": d.depreciation_method,
									"finance_book": d.finance_book,
									"finance_book_id": d.idx
								})
					else:
						for n in range(number_of_pending_depreciations):
							schedule_date = add_months(d.depreciation_start_date,
								n * cint(d.frequency_of_depreciation))

							if d.depreciation_method in ("Straight Line", "Manual"):
								days = date_diff(schedule_date, from_date)
								if n == 0: days += 1

								depreciation_amount = days * rate_per_day
								from_date = schedule_date
							else:
								depreciation_amount = self.get_depreciation_amount(value_after_depreciation,
									d.total_number_of_depreciations, d)

							if depreciation_amount:
								value_after_depreciation -= flt(depreciation_amount)

								self.append("schedules", {
									"schedule_date": schedule_date,
									"depreciation_amount": depreciation_amount,
									"depreciation_method": d.depreciation_method,
									"finance_book": d.finance_book,
									"finance_book_id": d.idx
								})

	def validate_asset_finance_books(self, row):
		if flt(row.expected_value_after_useful_life) >= flt(self.gross_purchase_amount):
			frappe.throw(_("Row {0}: Expected Value After Useful Life must be less than Gross Purchase Amount")
				.format(row.idx))

		if not row.depreciation_start_date:
			frappe.throw(_("Row {0}: Depreciation Start Date is required").format(row.idx))

		if not self.is_existing_asset:
			self.opening_accumulated_depreciation = 0
			self.number_of_depreciations_booked = 0
		else:
			depreciable_amount = flt(self.gross_purchase_amount) - flt(row.expected_value_after_useful_life)
			if flt(self.opening_accumulated_depreciation) > depreciable_amount:
					frappe.throw(_("Opening Accumulated Depreciation must be less than equal to {0}")
						.format(depreciable_amount))

			if self.opening_accumulated_depreciation:
				if not self.number_of_depreciations_booked:
					frappe.throw(_("Please set Number of Depreciations Booked"))
			else:
				self.number_of_depreciations_booked = 0

			if cint(self.number_of_depreciations_booked) > cint(row.total_number_of_depreciations):
				frappe.throw(_("Number of Depreciations Booked cannot be greater than Total Number of Depreciations"))

		if row.depreciation_start_date and getdate(row.depreciation_start_date) < getdate(nowdate()):
			frappe.msgprint(_("Depreciation Row {0}: Depreciation Start Date is entered as past date")
				.format(row.idx), title=_('Warning'), indicator='red')

		if row.depreciation_start_date and getdate(row.depreciation_start_date) < getdate(self.purchase_date):
			frappe.throw(_("Depreciation Row {0}: Next Depreciation Date cannot be before Purchase Date")
				.format(row.idx))

		if row.depreciation_start_date and getdate(row.depreciation_start_date) < getdate(self.available_for_use_date):
			frappe.throw(_("Depreciation Row {0}: Next Depreciation Date cannot be before Available-for-use Date")
				.format(row.idx))

	def set_accumulated_depreciation(self, ignore_booked_entry = False):
		straight_line_idx = [d.idx for d in self.get("schedules") if d.depreciation_method == 'Straight Line']
		finance_books = []

		for i, d in enumerate(self.get("schedules")):
			if ignore_booked_entry and d.journal_entry:
				continue

			if d.finance_book_id not in finance_books:
				accumulated_depreciation = flt(self.opening_accumulated_depreciation)
				value_after_depreciation = flt(self.get_value_after_depreciation(d.finance_book_id))
				finance_books.append(d.finance_book_id)

			depreciation_amount = flt(d.depreciation_amount, d.precision("depreciation_amount"))
			value_after_depreciation -= flt(depreciation_amount)

			if straight_line_idx and i == max(straight_line_idx) - 1:
				book = self.get('finance_books')[cint(d.finance_book_id) - 1]
				depreciation_amount += flt(value_after_depreciation -
					flt(book.expected_value_after_useful_life), d.precision("depreciation_amount"))

			d.depreciation_amount = depreciation_amount
			accumulated_depreciation += d.depreciation_amount
			d.accumulated_depreciation_amount = flt(accumulated_depreciation,
				d.precision("accumulated_depreciation_amount"))

	def get_value_after_depreciation(self, idx):
		return flt(self.get('finance_books')[cint(idx)-1].value_after_depreciation)

	def get_depreciation_amount(self, depreciable_value, total_number_of_depreciations, row):
		percentage_value = 100.0 if row.depreciation_method == 'Written Down Value' else 200.0

		factor = percentage_value /  total_number_of_depreciations
		depreciation_amount = flt(depreciable_value * factor / 100, 0)

		value_after_depreciation = flt(depreciable_value) - depreciation_amount
		if value_after_depreciation < flt(row.expected_value_after_useful_life):
			depreciation_amount = flt(depreciable_value) - flt(row.expected_value_after_useful_life)

		return depreciation_amount

	def get_depreciation_amount_prorata_temporis(self, depreciable_value, row, start_date=None, end_date=None):
		if start_date and end_date:
			prorata_temporis =  min(abs(flt(date_diff(str(end_date), str(start_date)))) / flt(frappe.db.get_value("Asset Settings", None, "number_of_days_in_fiscal_year")), 1)
		else:
			prorata_temporis = 1

		if row.depreciation_method in ("Straight Line", "Manual"):
			depreciation_amount = (flt(row.value_after_depreciation) -
				flt(row.expected_value_after_useful_life)) / (cint(row.total_number_of_depreciations) -
				cint(self.number_of_depreciations_booked)) * prorata_temporis
		else:
			depreciation_amount = self.get_depreciation_amount(depreciable_value, row)

		return depreciation_amount

	def validate_expected_value_after_useful_life(self):
		for row in self.get('finance_books'):
			accumulated_depreciation_after_full_schedule = \
				max([d.accumulated_depreciation_amount for d in self.get("schedules") if d.finance_book_id == row.idx])

			asset_value_after_full_schedule = flt(flt(self.gross_purchase_amount) -
				flt(accumulated_depreciation_after_full_schedule),
				self.precision('gross_purchase_amount'))

			if row.expected_value_after_useful_life < asset_value_after_full_schedule:
				frappe.throw(_("Depreciation Row {0}: Expected value after useful life must be greater than or equal to {1}")
					.format(row.idx, asset_value_after_full_schedule))

	def validate_cancellation(self):
		if self.status not in ("Submitted", "Partially Depreciated", "Fully Depreciated"):
			frappe.throw(_("Asset cannot be cancelled, as it is already {0}").format(self.status))

		if self.purchase_invoice:
			frappe.throw(_("Please cancel Purchase Invoice {0} first").format(self.purchase_invoice))

		if self.purchase_receipt:
			frappe.throw(_("Please cancel Purchase Receipt {0} first").format(self.purchase_receipt))

	def delete_depreciation_entries(self):
		for d in self.get("schedules"):
			if d.journal_entry:
				frappe.get_doc("Journal Entry", d.journal_entry).cancel()
				d.db_set("journal_entry", None)

		self.db_set("value_after_depreciation",
			(flt(self.gross_purchase_amount) - flt(self.opening_accumulated_depreciation)))

	def set_status(self, status=None):
		'''Get and update status'''
		if not status:
			status = self.get_status()
		self.db_set("status", status)

	def get_status(self):
		'''Returns status based on whether it is draft, submitted, scrapped or depreciated'''
		if self.docstatus == 0:
			status = "Draft"
		elif self.docstatus == 1:
			status = "Submitted"

			if self.journal_entry_for_scrap:
				status = "Scrapped"
			elif self.finance_books:
				idx = self.get_default_finance_book_idx() or 0

				expected_value_after_useful_life = self.finance_books[idx].expected_value_after_useful_life
				value_after_depreciation = self.finance_books[idx].value_after_depreciation

				if flt(value_after_depreciation) <= expected_value_after_useful_life:
					status = "Fully Depreciated"
				elif flt(value_after_depreciation) < flt(self.gross_purchase_amount):
					status = 'Partially Depreciated'
		elif self.docstatus == 2:
			status = "Cancelled"
		return status

	def get_default_finance_book_idx(self):
		if not self.get('default_finance_book') and self.company:
			self.default_finance_book = erpnext.get_default_finance_book(self.company)

		if self.get('default_finance_book'):
			for d in self.get('finance_books'):
				if d.finance_book == self.default_finance_book:
					return cint(d.idx) - 1

	def update_stock_movement(self):
		asset_movement = frappe.db.get_value('Asset Movement',
			{'asset': self.name, 'reference_name': self.purchase_receipt, 'docstatus': 0}, 'name')

		if asset_movement:
			doc = frappe.get_doc('Asset Movement', asset_movement)
			doc.submit()

	def make_gl_entries(self):
		gl_entries = []

		if ((self.purchase_receipt or (self.purchase_invoice and
			frappe.db.get_value('Purchase Invoice', self.purchase_invoice, 'update_stock')))
			and self.purchase_receipt_amount and self.available_for_use_date <= nowdate()):
			fixed_aseet_account = get_asset_category_account(self.name, 'fixed_asset_account',
					asset_category = self.asset_category, company = self.company)

			cwip_account = get_asset_account("capital_work_in_progress_account",
				self.name, self.asset_category, self.company)

			gl_entries.append(self.get_gl_dict({
				"account": cwip_account,
				"against": fixed_aseet_account,
				"remarks": self.get("remarks") or _("Accounting Entry for Asset"),
				"posting_date": self.available_for_use_date,
				"credit": self.purchase_receipt_amount,
				"credit_in_account_currency": self.purchase_receipt_amount
			}))

			gl_entries.append(self.get_gl_dict({
				"account": fixed_aseet_account,
				"against": cwip_account,
				"remarks": self.get("remarks") or _("Accounting Entry for Asset"),
				"posting_date": self.available_for_use_date,
				"debit": self.purchase_receipt_amount,
				"debit_in_account_currency": self.purchase_receipt_amount
			}))

		if gl_entries:
			from erpnext.accounting.general_ledger import make_gl_entries

			make_gl_entries(gl_entries)
			self.db_set('booked_fixed_asset', 1)

def update_maintenance_status():
	assets = frappe.get_all('Asset', filters = {'docstatus': 1, 'maintenance_required': 1})

	for asset in assets:
		asset = frappe.get_doc("Asset", asset.name)
		if frappe.db.exists('Asset Maintenance Task', {'parent': asset.name, 'next_due_date': today()}):
			asset.set_status('In Maintenance')
		if frappe.db.exists('Asset Repair', {'asset_name': asset.name, 'repair_status': 'Pending'}):
			asset.set_status('Out of Order')

def make_post_gl_entry():
	assets = frappe.db.sql_list(""" select name from `tabAsset`
		where ifnull(booked_fixed_asset, 0) = 0 and available_for_use_date = %s""", nowdate())

	for asset in assets:
		doc = frappe.get_doc('Asset', asset)
		doc.make_gl_entries()

def get_asset_naming_series():
	meta = frappe.get_meta('Asset')
	return meta.get_field("naming_series").options

@frappe.whitelist()
def make_purchase_invoice(asset, item_code, gross_purchase_amount, company, posting_date):
	pi = frappe.new_doc("Purchase Invoice")
	pi.company = company
	pi.currency = frappe.get_cached_value('Company',  company,  "default_currency")
	pi.set_posting_time = 1
	pi.posting_date = posting_date
	pi.append("items", {
		"item_code": item_code,
		"is_fixed_asset": 1,
		"asset": asset,
		"expense_account": get_asset_category_account(asset, 'fixed_asset_account'),
		"qty": 1,
		"price_list_rate": gross_purchase_amount,
		"rate": gross_purchase_amount
	})
	pi.set_missing_values()
	return pi

@frappe.whitelist()
def make_sales_invoice(asset, item_code, company, serial_no=None):
	si = frappe.new_doc("Sales Invoice")
	si.company = company
	si.currency = frappe.get_cached_value('Company',  company,  "default_currency")
	disposal_account, depreciation_cost_center = get_disposal_account_and_cost_center(company)
	si.append("items", {
		"item_code": item_code,
		"is_fixed_asset": 1,
		"asset": asset,
		"income_account": disposal_account,
		"serial_no": serial_no,
		"cost_center": depreciation_cost_center,
		"qty": 1
	})
	si.set_missing_values()
	return si

@frappe.whitelist()
def create_asset_maintenance(asset, item_code, item_name, asset_category, company):
	asset_maintenance = frappe.new_doc("Asset Maintenance")
	asset_maintenance.update({
		"asset_name": asset,
		"company": company,
		"item_code": item_code,
		"item_name": item_name,
		"asset_category": asset_category
	})
	return asset_maintenance

@frappe.whitelist()
def create_asset_adjustment(asset, asset_category, company):
	asset_maintenance = frappe.new_doc("Asset Value Adjustment")
	asset_maintenance.update({
		"asset": asset,
		"company": company,
		"asset_category": asset_category
	})
	return asset_maintenance

@frappe.whitelist()
def transfer_asset(args):
	import json
	args = json.loads(args)

	if args.get('serial_no'):
		args['quantity'] = len(args.get('serial_no').split('\n'))

	movement_entry = frappe.new_doc("Asset Movement")
	movement_entry.update(args)
	movement_entry.insert()
	movement_entry.submit()

	frappe.db.commit()

	frappe.msgprint(_("Asset Movement record {0} created").format("<a href='#Form/Asset Movement/{0}'>{0}</a>".format(movement_entry.name)))

@frappe.whitelist()
def get_item_details(item_code, asset_category):
	asset_category_doc = frappe.get_doc('Asset Category', asset_category)
	books = []
	for d in asset_category_doc.finance_books:
		books.append({
			'finance_book': d.finance_book,
			'depreciation_method': d.depreciation_method,
			'total_number_of_depreciations': d.total_number_of_depreciations,
			'frequency_of_depreciation': d.frequency_of_depreciation,
			'start_date': nowdate()
		})

	return books

def get_asset_account(account_name, asset=None, asset_category=None, company=None):
	account = None
	if asset:
		account = get_asset_category_account(asset, account_name,
				asset_category = asset_category, company = company)

	if not account:
		account = frappe.get_cached_value('Company',  company,  account_name)

	if not account:
		frappe.throw(_("Set {0} in asset category {1} or company {2}")
			.format(account_name.replace('_', ' ').title(), asset_category, company))

	return account

@frappe.whitelist()
def make_journal_entry(asset_name):
	asset = frappe.get_doc("Asset", asset_name)
	fixed_asset_account, accumulated_depreciation_account, depreciation_expense_account = \
		get_depreciation_accounts(asset)

	depreciation_cost_center, depreciation_series = frappe.db.get_value("Company", asset.company,
		["depreciation_cost_center", "series_for_depreciation_entry"])
	depreciation_cost_center = asset.cost_center or depreciation_cost_center

	je = frappe.new_doc("Journal Entry")
	je.voucher_type = "Depreciation Entry"
	je.naming_series = depreciation_series
	je.company = asset.company
	je.remark = "Depreciation Entry against asset {0}".format(asset_name)

	je.append("accounts", {
		"account": depreciation_expense_account,
		"reference_type": "Asset",
		"reference_name": asset.name,
		"cost_center": depreciation_cost_center
	})

	je.append("accounts", {
		"account": accumulated_depreciation_account,
		"reference_type": "Asset",
		"reference_name": asset.name
	})

	return je
