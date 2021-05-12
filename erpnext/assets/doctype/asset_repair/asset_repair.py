# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import time_diff_in_hours
from frappe.model.document import Document
from frappe.utils import flt
from erpnext.accounts.general_ledger import make_gl_entries
from erpnext.controllers.accounts_controller import AccountsController

class AssetRepair(Document):
	def validate(self):
		if self.repair_status == "Completed" and not self.completion_date:
			frappe.throw(_("Please select Completion Date for Completed Repair"))

		self.update_status()
		self.set_total_value()

	def set_total_value(self):
		for item in self.stock_items:
			item.total_value = flt(item.valuation_rate) * flt(item.consumed_quantity)

	def update_status(self):
		if self.repair_status == 'Pending':
			frappe.db.set_value('Asset', self.asset, 'status', 'Out of Order')
		else:
			frappe.db.set_value('Asset', self.asset, 'status', 'Submitted')

	def on_submit(self):
		if self.repair_status == "Pending":
			frappe.throw(_("Please update Repair Status."))

		self.increase_asset_value()
		self.make_gl_entries()

	def increase_asset_value(self):
		if self.capitalize_repair_cost:
			asset_value = frappe.db.get_value('Asset', self.asset, 'asset_value') + self.repair_cost
			for item in self.stock_items:
				asset_value += item.total_value

			frappe.db.set_value('Asset', self.asset, 'asset_value', asset_value)

	def on_cancel(self):
		if self.payable_account:
			self.make_gl_entries(cancel=True)

	def make_gl_entries(self, cancel=False):
		if flt(self.repair_cost) > 0:
			gl_entries = self.get_gl_entries()
			make_gl_entries(gl_entries, cancel)

	def get_gl_entries(self):
		gl_entry = []
		company = frappe.db.get_value('Asset', self.asset, 'company')
		repair_and_maintenance_account = frappe.db.get_value('Company', company, 'repair_and_maintenance_account')

		gl_entry = frappe.get_doc({
			"doctype": "GL Entry",
			"account": self.payable_account,
			"credit": self.repair_cost,
			"credit_in_account_currency": self.repair_cost,
			"against": repair_and_maintenance_account,
			"voucher_type": self.doctype,
			"voucher_no": self.name,
			"cost_center": self.cost_center
		})
		gl_entry.insert()
		gl_entry = frappe.get_doc({
			"doctype": "GL Entry",
			"account": repair_and_maintenance_account,
			"debit": self.repair_cost,
			"debit_in_account_currency": self.repair_cost,
			"against": self.payable_account,
			"voucher_type": self.doctype,
			"voucher_no": self.name,
			"cost_center": self.cost_center
		})
		gl_entry.insert()
	
@frappe.whitelist()
def get_downtime(failure_date, completion_date):
	downtime = time_diff_in_hours(completion_date, failure_date)
	return round(downtime, 2)