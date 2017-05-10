# -*- coding: utf-8 -*-
# Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, add_months, cint, nowdate, getdate
from frappe.model.document import Document
from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import get_fixed_asset_account
from erpnext.accounts.doctype.asset.depreciation \
	import get_disposal_account_and_cost_center, get_depreciation_accounts

class Asset(Document):
	def validate(self):
		self.status = self.get_status()
		self.validate_item()
		self.set_missing_values()
		self.validate_asset_values()
		self.make_depreciation_schedule()
		self.set_accumulated_depreciation()
		self.validate_expected_value_after_useful_life()
		# Validate depreciation related accounts
		get_depreciation_accounts(self)

	def on_submit(self):
		self.set_status()

	def on_cancel(self):
		self.validate_cancellation()
		self.delete_depreciation_entries()
		self.set_status()

	def validate_item(self):
		item = frappe.db.get_value("Item", self.item_code,
			["is_fixed_asset", "is_stock_item", "disabled"], as_dict=1)
		if not item:
			frappe.throw(_("Item {0} does not exist").format(self.item_code))
		elif item.disabled:
			frappe.throw(_("Item {0} has been disabled").format(self.item_code))
		elif not item.is_fixed_asset:
			frappe.throw(_("Item {0} must be a Fixed Asset Item").format(self.item_code))
		elif item.is_stock_item:
			frappe.throw(_("Item {0} must be a non-stock item").format(self.item_code))

	def set_missing_values(self):
		if self.item_code:
			item_details = get_item_details(self.item_code)
			for field, value in item_details.items():
				if not self.get(field):
					self.set(field, value)

		self.value_after_depreciation = (flt(self.gross_purchase_amount) -
			flt(self.opening_accumulated_depreciation))

	def validate_asset_values(self):
		if flt(self.expected_value_after_useful_life) >= flt(self.gross_purchase_amount):
			frappe.throw(_("Expected Value After Useful Life must be less than Gross Purchase Amount"))

		if not flt(self.gross_purchase_amount):
			frappe.throw(_("Gross Purchase Amount is mandatory"), frappe.MandatoryError)

		if not self.is_existing_asset:
			self.opening_accumulated_depreciation = 0
			self.number_of_depreciations_booked = 0
			if not self.next_depreciation_date:
				frappe.throw(_("Next Depreciation Date is mandatory for new asset"))
		else:
			depreciable_amount = flt(self.gross_purchase_amount) - flt(self.expected_value_after_useful_life)
			if flt(self.opening_accumulated_depreciation) > depreciable_amount:
					frappe.throw(_("Opening Accumulated Depreciation must be less than equal to {0}")
						.format(depreciable_amount))

			if self.opening_accumulated_depreciation:
				if not self.number_of_depreciations_booked:
					frappe.throw(_("Please set Number of Depreciations Booked"))
			else:
				self.number_of_depreciations_booked = 0

			if cint(self.number_of_depreciations_booked) > cint(self.total_number_of_depreciations):
				frappe.throw(_("Number of Depreciations Booked cannot be greater than Total Number of Depreciations"))

		if self.next_depreciation_date and getdate(self.next_depreciation_date) < getdate(nowdate()):
			frappe.msgprint(_("Next Depreciation Date is entered as past date"), title=_('Warning'), indicator='red')

		if self.next_depreciation_date and getdate(self.next_depreciation_date) < getdate(self.purchase_date):
			frappe.throw(_("Next Depreciation Date cannot be before Purchase Date"))

		if (flt(self.value_after_depreciation) > flt(self.expected_value_after_useful_life)
			and not self.next_depreciation_date):
				frappe.throw(_("Please set Next Depreciation Date"))

	def make_depreciation_schedule(self):
		if self.depreciation_method != 'Manual':
			self.schedules = []

		if not self.get("schedules") and self.next_depreciation_date:
			value_after_depreciation = flt(self.value_after_depreciation)

			number_of_pending_depreciations = cint(self.total_number_of_depreciations) - \
				cint(self.number_of_depreciations_booked)
			if number_of_pending_depreciations:
				for n in xrange(number_of_pending_depreciations):
					schedule_date = add_months(self.next_depreciation_date,
						n * cint(self.frequency_of_depreciation))

					depreciation_amount = self.get_depreciation_amount(value_after_depreciation)
					value_after_depreciation -= flt(depreciation_amount)

					self.append("schedules", {
						"schedule_date": schedule_date,
						"depreciation_amount": depreciation_amount
					})

	def set_accumulated_depreciation(self):
		accumulated_depreciation = flt(self.opening_accumulated_depreciation)
		value_after_depreciation = flt(self.value_after_depreciation)
		for i, d in enumerate(self.get("schedules")):
			depreciation_amount = flt(d.depreciation_amount, d.precision("depreciation_amount"))
			value_after_depreciation -= flt(depreciation_amount)

			if i==len(self.get("schedules"))-1 and self.depreciation_method == "Straight Line":
				depreciation_amount += flt(value_after_depreciation - flt(self.expected_value_after_useful_life),
					d.precision("depreciation_amount"))

			d.depreciation_amount = depreciation_amount
			accumulated_depreciation += d.depreciation_amount
			d.accumulated_depreciation_amount = flt(accumulated_depreciation, d.precision("accumulated_depreciation_amount"))

	def get_depreciation_amount(self, depreciable_value):
		if self.depreciation_method in ("Straight Line", "Manual"):
			depreciation_amount = (flt(self.value_after_depreciation) -
				flt(self.expected_value_after_useful_life)) / (cint(self.total_number_of_depreciations) -
				cint(self.number_of_depreciations_booked))
		else:
			factor = 200.0 /  self.total_number_of_depreciations
			depreciation_amount = flt(depreciable_value * factor / 100, 0)

			value_after_depreciation = flt(depreciable_value) - depreciation_amount
			if value_after_depreciation < flt(self.expected_value_after_useful_life):
				depreciation_amount = flt(depreciable_value) - flt(self.expected_value_after_useful_life)

		return depreciation_amount

	def validate_expected_value_after_useful_life(self):
		accumulated_depreciation_after_full_schedule = \
			max([d.accumulated_depreciation_amount for d in self.get("schedules")])

		asset_value_after_full_schedule = (flt(self.gross_purchase_amount) -
			flt(accumulated_depreciation_after_full_schedule))

		if self.expected_value_after_useful_life < asset_value_after_full_schedule:
			frappe.throw(_("Expected value after useful life must be greater than or equal to {0}")
				.format(asset_value_after_full_schedule))

	def validate_cancellation(self):
		if self.status not in ("Submitted", "Partially Depreciated", "Fully Depreciated"):
			frappe.throw(_("Asset cannot be cancelled, as it is already {0}").format(self.status))

		if self.purchase_invoice:
			frappe.throw(_("Please cancel Purchase Invoice {0} first").format(self.purchase_invoice))

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
			elif flt(self.value_after_depreciation) <= flt(self.expected_value_after_useful_life):
				status = "Fully Depreciated"
			elif flt(self.value_after_depreciation) < flt(self.gross_purchase_amount):
				status = 'Partially Depreciated'
		elif self.docstatus == 2:
			status = "Cancelled"

		return status

@frappe.whitelist()
def make_purchase_invoice(asset, item_code, gross_purchase_amount, company, posting_date):
	pi = frappe.new_doc("Purchase Invoice")
	pi.company = company
	pi.currency = frappe.db.get_value("Company", company, "default_currency")
	pi.set_posting_time = 1
	pi.posting_date = posting_date
	pi.append("items", {
		"item_code": item_code,
		"is_fixed_asset": 1,
		"asset": asset,
		"expense_account": get_fixed_asset_account(asset),
		"qty": 1,
		"price_list_rate": gross_purchase_amount,
		"rate": gross_purchase_amount
	})
	pi.set_missing_values()
	return pi

@frappe.whitelist()
def make_sales_invoice(asset, item_code, company):
	si = frappe.new_doc("Sales Invoice")
	si.company = company
	si.currency = frappe.db.get_value("Company", company, "default_currency")
	disposal_account, depreciation_cost_center = get_disposal_account_and_cost_center(company)
	si.append("items", {
		"item_code": item_code,
		"is_fixed_asset": 1,
		"asset": asset,
		"income_account": disposal_account,
		"cost_center": depreciation_cost_center,
		"qty": 1
	})
	si.set_missing_values()
	return si

@frappe.whitelist()
def transfer_asset(args):
	import json
	args = json.loads(args)
	movement_entry = frappe.new_doc("Asset Movement")
	movement_entry.update(args)
	movement_entry.insert()
	movement_entry.submit()

	frappe.db.commit()

	frappe.msgprint(_("Asset Movement record {0} created").format("<a href='#Form/Asset Movement/{0}'>{0}</a>".format(movement_entry.name)))

@frappe.whitelist()
def get_item_details(item_code):
	asset_category = frappe.db.get_value("Item", item_code, "asset_category")

	if not asset_category:
		frappe.throw(_("Please enter Asset Category in Item {0}").format(item_code))

	ret = frappe.db.get_value("Asset Category", asset_category,
		["depreciation_method", "total_number_of_depreciations", "frequency_of_depreciation"], as_dict=1)

	ret.update({
		"asset_category": asset_category
	})

	return ret
