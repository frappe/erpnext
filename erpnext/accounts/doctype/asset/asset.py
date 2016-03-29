# -*- coding: utf-8 -*-
# Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, add_months, cint
from frappe.model.document import Document

class Asset(Document):
	def validate(self):
		self.set_status()
		self.validate_fixed_asset_item()
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
		
	def validate_fixed_asset_item(self):
		item = frappe.get_doc("Item", self.item_code)
		if item.disabled:
			frappe.throw(_("Item {0} has been disabled").format(self.item_code))
		if item.is_stock_item:
			frappe.throw(_("Item {0} must be a non-stock item").format(self.item_code))
			
	def validate_asset_values(self):
		if flt(self.expected_value_after_useful_life) >= flt(self.gross_purchase_amount):
			frappe.throw(_("Expected Value After Useful Life must be less than Gross Purchase Amount"))
			
		if not flt(self.gross_purchase_amount):
			frappe.throw(_("Gross Purchase Amount is mandatory"), frappe.MandatoryError)
			
		if not self.current_value and self.next_depreciation_date:
			self.current_value = flt(self.gross_purchase_amount)
		else:
			if flt(self.current_value) > flt(self.gross_purchase_amount):
				frappe.throw(_("Current Value After Depreciation must be less than equal to {0}")
					.format(flt(self.gross_purchase_amount)))
							
	def set_depreciation_settings(self):
		asset_category = frappe.get_doc("Asset Category", self.asset_category)
		
		for field in ("depreciation_method", "number_of_depreciations", "number_of_months_in_a_period"):
			if not self.get(field):
				self.set(field, asset_category.get(field))
				
	def make_depreciation_schedule(self):
		self.schedules = []
		if not self.get("schedules") and self.next_depreciation_date:
			accumulated_depreciation = 0
			value_after_depreciation = flt(self.current_value)
			for n in xrange(self.number_of_depreciations):
				schedule_date = add_months(self.next_depreciation_date, 
					n * cint(self.number_of_months_in_a_period))
					
				depreciation_amount = self.get_depreciation_amount(value_after_depreciation)
				
				self.append("schedules", {
					"schedule_date": schedule_date,
					"depreciation_amount": depreciation_amount,
					"accumulated_depreciation_amount": accumulated_depreciation + depreciation_amount
				})
				accumulated_depreciation += flt(depreciation_amount)
				value_after_depreciation -= flt(depreciation_amount)
									
	def get_depreciation_amount(self, depreciable_value):
		if self.depreciation_method == "Straight Line":
			depreciation_amount = (flt(self.current_value) - 
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
		total_depreciation_amount = 0
		for d in self.get("schedules"):
			if d.journal_entry:
				frappe.get_doc("Journal Entry", d.journal_entry).cancel()
			
				d.db_set("journal_entry", None)
				total_depreciation_amount += flt(d.depreciation_amount)
		self.db_set("current_value", (self.current_value + total_depreciation_amount))
		
	def validate_depreciation_settings_in_company(self):
		company = frappe.get_doc("Company", self.company)
		for field in ("accumulated_depreciation_account", "depreciation_expense_account", 
			"disposal_account", "depreciation_cost_center"):
				if not company.get(field):
					frappe.throw(_("Please set {0} in Company {1}")
						.format(company.meta.get_label(field), self.company))
	
	def set_status(self, status=None):
		if not status:
			if self.docstatus == 0:
				status = "Draft"
			elif self.docstatus == 1:
				status = "Submitted"
				if self.journal_entry_for_scrap:
					status = "Scrapped"
				elif flt(self.current_value) <= flt(self.expected_value_after_useful_life):
					status = "Fully Depreciated"
				elif flt(self.current_value) < flt(self.gross_purchase_amount):
					status = 'Partially Depreciated'
			elif self.docstatus == 2:
				status = "Cancelled"

		self.db_set("status", status)