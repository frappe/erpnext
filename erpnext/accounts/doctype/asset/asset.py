# -*- coding: utf-8 -*-
# Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, add_months, cint, nowdate, getdate
from frappe.model.document import Document
from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import get_fixed_asset_account
from erpnext.accounts.doctype.asset.depreciation import get_disposal_account_and_cost_center

class Asset(Document):
	def validate(self):
		self.status = self.get_status()
		self.validate_item()
		self.validate_asset_values()
		self.set_depreciation_settings()
		self.make_depreciation_schedule()
		self.validate_depreciation_settings_in_company()

	def on_submit(self):
		self.set_status()

	def on_cancel(self):
		self.validate_cancellation()
		self.delete_depreciation_entries()
		self.set_status()

	def validate_item(self):
		item = frappe.get_doc("Item", self.item_code)
		if item.disabled:
			frappe.throw(_("Item {0} has been disabled").format(self.item_code))

	def validate_asset_values(self):
		self.value_after_depreciation = flt(self.gross_purchase_amount) - flt(self.opening_accumulated_depreciation)
		
		if flt(self.expected_value_after_useful_life) >= flt(self.gross_purchase_amount):
			frappe.throw(_("Expected Value After Useful Life must be less than Gross Purchase Amount"))

		if not flt(self.gross_purchase_amount):
			frappe.throw(_("Gross Purchase Amount is mandatory"), frappe.MandatoryError)
		
		if not self.is_existing_asset:
			self.opening_accumulated_depreciation = 0
			if not self.next_depreciation_date:
				frappe.throw(_("Next Depreciation Date is mandatory for new asset"))
		else:
			depreciable_amount = flt(self.gross_purchase_amount) - flt(self.expected_value_after_useful_life)
			if flt(self.opening_accumulated_depreciation) > depreciable_amount:
					frappe.throw(_("Opening Accumulated Depreciation must be less than equal to {0}")
						.format(depreciable_amount))
						
		if self.next_depreciation_date and getdate(self.next_depreciation_date) < getdate(nowdate()):
			frappe.throw(_("Next Depreciation Date must be on or after today"))
		

	def set_depreciation_settings(self):
		asset_category = frappe.get_doc("Asset Category", self.asset_category)

		for field in ("depreciation_method", "number_of_depreciations", "frequency_of_depreciation"):
			if not self.get(field):
				self.set(field, asset_category.get(field))

	def make_depreciation_schedule(self):
		self.schedules = []
		if not self.get("schedules") and self.next_depreciation_date:
			accumulated_depreciation = flt(self.opening_accumulated_depreciation)
			value_after_depreciation = flt(self.value_after_depreciation)
			for n in xrange(self.number_of_depreciations):
				schedule_date = add_months(self.next_depreciation_date,
					n * cint(self.frequency_of_depreciation))

				depreciation_amount = self.get_depreciation_amount(value_after_depreciation)
				
				accumulated_depreciation += flt(depreciation_amount)
				value_after_depreciation -= flt(depreciation_amount)

				self.append("schedules", {
					"schedule_date": schedule_date,
					"depreciation_amount": depreciation_amount,
					"accumulated_depreciation_amount": accumulated_depreciation
				})

	def get_depreciation_amount(self, depreciable_value):
		if self.depreciation_method == "Straight Line":
			depreciation_amount = (flt(self.value_after_depreciation) -
				flt(self.expected_value_after_useful_life)) / cint(self.number_of_depreciations)
		else:
			factor = 200.0 /  cint(self.number_of_depreciations)
			depreciation_amount = flt(depreciable_value * factor / 100, 0)

			value_after_depreciation = flt(depreciable_value) - depreciation_amount
			if value_after_depreciation < flt(self.expected_value_after_useful_life):
				depreciation_amount = flt(depreciable_value) - flt(self.expected_value_after_useful_life)

		return depreciation_amount

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

	def validate_depreciation_settings_in_company(self):
		company = frappe.get_doc("Company", self.company)
		for field in ("accumulated_depreciation_account", "depreciation_expense_account",
			"disposal_account", "depreciation_cost_center"):
				if not company.get(field):
					frappe.throw(_("Please set {0} in Company {1}")
						.format(company.meta.get_label(field), self.company))

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
def make_purchase_invoice(asset, item_code, gross_purchase_amount, company):
	pi = frappe.new_doc("Purchase Invoice")
	pi.company = company
	pi.currency = frappe.db.get_value("Company", company, "default_currency")
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