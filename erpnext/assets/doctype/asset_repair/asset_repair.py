# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import time_diff_in_hours, getdate, add_months, flt, cint
from frappe.model.document import Document
from erpnext.accounts.general_ledger import make_gl_entries
from erpnext.assets.doctype.asset.asset import get_asset_account
from erpnext.controllers.accounts_controller import AccountsController

class AssetRepair(AccountsController):
	def validate(self):
		if self.repair_status == "Completed" and not self.completion_date:
			frappe.throw(_("Please select Completion Date for Completed Repair"))

		self.update_status()
		self.set_total_value()		# change later
		self.calculate_total_repair_cost()
		
	def update_status(self):
		if self.repair_status == 'Pending':
			frappe.db.set_value('Asset', self.asset, 'status', 'Out of Order')
		else:
			asset = frappe.get_doc('Asset', self.asset)
			asset.set_status()

	def set_total_value(self):
		for item in self.stock_items:
			item.total_value = flt(item.valuation_rate) * flt(item.consumed_quantity)

	def calculate_total_repair_cost(self):
		self.total_repair_cost = self.repair_cost
		if self.stock_consumption:
			for item in self.stock_items:
				self.total_repair_cost += item.total_value

	def on_submit(self):
		self.check_repair_status()

		if self.stock_consumption or self.capitalize_repair_cost:
			self.increase_asset_value()
		if self.stock_consumption:
			self.check_for_stock_items_and_warehouse()
			self.decrease_stock_quantity()
		if self.capitalize_repair_cost:
			self.make_gl_entries()
			if frappe.db.get_value('Asset', self.asset, 'calculate_depreciation') and self.increase_in_asset_life:
				self.modify_depreciation_schedule()

	def check_repair_status(self):
		if self.repair_status == "Pending":
			frappe.throw(_("Please update Repair Status."))

	def check_for_stock_items_and_warehouse(self):
		if not self.stock_items:
			frappe.throw(_("Please enter Stock Items consumed during the Repair."), title=_("Missing Items"))
		if not self.warehouse:
			frappe.throw(_("Please enter Warehouse from which Stock Items consumed during the Repair were taken."), title=_("Missing Warehouse"))

	def increase_asset_value(self):
		total_value_of_stock_consumed = 0
		for item in self.stock_items:
			total_value_of_stock_consumed += item.total_value

		asset = frappe.get_doc('Asset', self.asset)
		asset.flags.ignore_validate_update_after_submit = True
		if asset.calculate_depreciation:
			for row in asset.finance_books:
				row.value_after_depreciation += total_value_of_stock_consumed

				if self.capitalize_repair_cost:
					row.value_after_depreciation += self.repair_cost
		asset.save()

	def decrease_stock_quantity(self):
		stock_entry = frappe.get_doc({
			"doctype": "Stock Entry",
			"stock_entry_type": "Material Issue",
			"company": self.company
		})

		for stock_item in self.stock_items:
			stock_entry.append('items', {
				"s_warehouse": self.warehouse,
				"item_code": stock_item.item,
				"qty": stock_item.consumed_quantity
			})

		stock_entry.insert()
		stock_entry.submit()

	def on_cancel(self):
		self.make_gl_entries(cancel=True)

	def make_gl_entries(self, cancel=False):
		if flt(self.repair_cost) > 0:
			gl_entries = self.get_gl_entries()
			make_gl_entries(gl_entries, cancel)

	def get_gl_entries(self):
		gl_entries = []
		repair_and_maintenance_account = frappe.db.get_value('Company', self.company, 'repair_and_maintenance_account')
		fixed_asset_account = get_asset_account("fixed_asset_account", asset=self.asset, company=self.company)
		expense_account = frappe.get_doc('Purchase Invoice', self.purchase_invoice).items[0].expense_account	

		gl_entries.append(
			self.get_gl_dict({
				"account": expense_account,
				"credit": self.repair_cost,
				"credit_in_account_currency": self.repair_cost,
				"against": repair_and_maintenance_account,
				"voucher_type": self.doctype,		
				"voucher_no": self.name,
				"cost_center": self.cost_center,
				"posting_date": getdate(),
				"company": self.company
			}, item=self)
		)

		if self.stock_consumption:
			# creating GL Entries for each row in Stock Items based on the Stock Entry created for it
			stock_entry = frappe.get_last_doc('Stock Entry')
			for item in stock_entry.items:
				gl_entries.append(
					self.get_gl_dict({
						"account": item.expense_account,
						"credit": item.amount,
						"credit_in_account_currency": item.amount,
						"against": repair_and_maintenance_account,
						"voucher_type": self.doctype,		
						"voucher_no": self.name,
						"cost_center": self.cost_center,
						"posting_date": getdate(),
						"company": self.company
					}, item=self)
				)

		gl_entries.append(
			self.get_gl_dict({
				"account": fixed_asset_account,
				"debit": self.total_repair_cost,
				"debit_in_account_currency": self.total_repair_cost,
				"against": expense_account,
				"voucher_type": self.doctype,
				"voucher_no": self.name,
				"cost_center": self.cost_center,
				"posting_date": getdate(),
				"against_voucher_type": "Purchase Invoice",
				"against_voucher": self.purchase_invoice,
				"company": self.company
			}, item=self)
		)

		return gl_entries

	def modify_depreciation_schedule(self):
		asset = frappe.get_doc('Asset', self.asset)
		asset.flags.ignore_validate_update_after_submit = True
		for row in asset.finance_books:
			row.total_number_of_depreciations += self.increase_in_asset_life/row.frequency_of_depreciation

			asset.edit_dates = ""
			extra_months = self.increase_in_asset_life % row.frequency_of_depreciation
			if extra_months != 0:
				self.calculate_last_schedule_date(asset, row, extra_months)

		asset.prepare_depreciation_data()
		asset.save()

	# to help modify depreciation schedule when increase_in_asset_life is not a multiple of frequency_of_depreciation
	def calculate_last_schedule_date(self, asset, row, extra_months):
		asset.edit_dates = "Don't Edit"
		number_of_pending_depreciations = cint(row.total_number_of_depreciations) - \
			cint(asset.number_of_depreciations_booked)

		# the Schedule Date in the final row of the old Depreciation Schedule
		last_schedule_date = asset.schedules[len(asset.schedules)-1].schedule_date

		# the Schedule Date in the final row of the new Depreciation Schedule
		asset.to_date = add_months(last_schedule_date, extra_months)

		# the latest possible date at which the depreciation can occur, without increasing the Total Number of Depreciations
		# if depreciations happen yearly and the Depreciation Posting Date is 01-01-2020, this could be 01-01-2021, 01-01-2022...
		schedule_date = add_months(row.depreciation_start_date,
			number_of_pending_depreciations * cint(row.frequency_of_depreciation))

		if asset.to_date > schedule_date:
			row.total_number_of_depreciations += 1

@frappe.whitelist()
def get_downtime(failure_date, completion_date):
	downtime = time_diff_in_hours(completion_date, failure_date)
	return round(downtime, 2)