# -*- coding: utf-8 -*-
# Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, add_years
from frappe.model.document import Document

class Asset(Document):
	def validate(self):
		self.validate_mandatory()
		self.make_depreciation_schedule()
	
	def validate_mandatory(self):
		if not self.useful_life:
			self.useful_life = frappe.db.get_value("Asset Category", self.asset_category, "useful_life")
			if not self.useful_life:
				frappe.throw(_("Useful Life is mandatory"))

	def make_depreciation_schedule(self):
		self.schedules = []
		if not self.get("schedules") and self.status == "Available":
			depreciation_method = self.get_depreciation_method()
			
			accumulated_depreciation = 0
			value_after_depreciation = flt(self.gross_value)
			for n in xrange(self.useful_life):
				depreciation_date = add_years(self.purchase_date, 
					n if self.start_depreciation_from_purchase_date else n+1)
				depreciation_amount = self.get_depreciation_amount(value_after_depreciation, 
					depreciation_method)
				
				self.append("schedules", {
					"depreciation_date": depreciation_date,
					"depreciation_amount": depreciation_amount,
					"accumulated_depreciation_amount": accumulated_depreciation + depreciation_amount
				})
				
	def get_depreciation_method(self):
		depreciation_method = self.depreciation_method or \
			frappe.db.get_value("Asset Category", self.asset_category, "depreciation_method") or \
			frappe.db.get_value("Company", self.company, "depreciation_method")
			
		if not depreciation_method:
			frappe.throw(_("Please set Depreciation Method in Asset Category {0} or Company {1}")
				.format(self.asset_category, self.company))
	
	def get_depreciation_amount(self, depreciable_value, depreciation_method=None):
		if not depreciation_method:
			depreciation_method = self.get_depreciation_method()
	
		if depreciation_method == "Straight Line":
			depreciation_amount = (flt(self.gross_value) - flt(self.salvage_value)) / flt(self.useful_life)
		else:
			factor = 200 / self.useful_life
			depreciation_amount = depreciable_value * factor / 100
	
			value_after_depreciation = flt(depreciable_value) - depreciation_amount
			if value_after_depreciation < self.salvage_value:
				depreciation_amount = flt(depreciable_value) - flt(self.salvage_value)
		
		return depreciation_amount
	