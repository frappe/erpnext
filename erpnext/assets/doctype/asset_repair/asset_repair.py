# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import time_diff_in_hours, getdate, nowdate, add_months, flt, cint
from frappe.model.document import Document
from erpnext.accounts.general_ledger import make_gl_entries

class AssetRepair(Document):
	def validate(self):
		if self.repair_status == "Completed" and not self.completion_date:
			self.completion_date = nowdate()

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
		for item in self.stock_items:
			self.total_repair_cost += item.total_value

	def on_submit(self):
		self.check_repair_status()
		self.check_for_cost_center()

		if self.stock_consumption or self.capitalize_repair_cost:
			self.increase_asset_value()
		if self.stock_consumption:
			self.check_for_stock_items_and_warehouse()
			self.decrease_stock_quantity()
		if self.capitalize_repair_cost:
			self.check_for_purchase_invoice()
			self.make_gl_entries()
			if frappe.db.get_value('Asset', self.asset, 'calculate_depreciation'):
				self.modify_depreciation_schedule()

	def check_repair_status(self):
		if self.repair_status == "Pending":
			frappe.throw(_("Please update Repair Status."))

	def check_for_stock_items_and_warehouse(self):
		if not self.stock_items:
			frappe.throw(_("Please enter Stock Items consumed during Asset Repair."))
		if not self.warehouse:
			frappe.throw(_("Please enter Warehouse from which Stock Items consumed during Asset Repair were taken."))

	def check_for_cost_center(self):
		if not self.cost_center:
			frappe.throw(_("Please enter Cost Center."))

	def increase_asset_value(self):
		asset_value = frappe.db.get_value('Asset', self.asset, 'asset_value')
		for item in self.stock_items:
			asset_value += item.total_value

		if self.capitalize_repair_cost:
			asset_value += self.repair_cost
		frappe.db.set_value('Asset', self.asset, 'asset_value', asset_value)

	def decrease_stock_quantity(self):
		stock_entry = frappe.get_doc({
			"doctype": "Stock Entry",
			"stock_entry_type": "Material Issue",
			"company": frappe.get_value('Asset', self.asset, "company")
		})

		for stock_item in self.stock_items:
			stock_entry.append('items', {
				"s_warehouse": self.warehouse,
				"item_code": stock_item.item,
				"qty": stock_item.consumed_quantity
			})

		stock_entry.insert()
		stock_entry.submit()

	def check_for_purchase_invoice(self):
		if not self.purchase_invoice:
			frappe.throw(_("Please link Purchase Invoice."))

	def on_cancel(self):
		self.make_gl_entries(cancel=True)

	def make_gl_entries(self, cancel=False):
		if flt(self.repair_cost) > 0:
			gl_entries = self.get_gl_entries()
			make_gl_entries(gl_entries, cancel)

	def get_gl_entries(self):
		gl_entry = []
		company = frappe.db.get_value('Asset', self.asset, 'company')
		repair_and_maintenance_account = frappe.db.get_value('Company', company, 'repair_and_maintenance_account')
		fixed_asset_account = self.get_fixed_asset_account()
		expense_account = frappe.get_doc('Purchase Invoice', self.purchase_invoice).items[0].expense_account	

		gl_entry = frappe.get_doc({
			"doctype": "GL Entry",
			"account": expense_account,
			"credit": self.total_repair_cost,
			"credit_in_account_currency": self.total_repair_cost,
			"against": repair_and_maintenance_account,
			"voucher_type": self.doctype,		
			"voucher_no": self.name,
			"cost_center": self.cost_center,
			"posting_date": getdate(),
			"company": company
		})
		gl_entry.insert()
		gl_entry = frappe.get_doc({
			"doctype": "GL Entry",
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
			"company": company
		})
		gl_entry.insert()

	def get_fixed_asset_account(self):
		asset_category = frappe.get_doc('Asset Category', frappe.db.get_value('Asset', self.asset, 'asset_category'))
		company = frappe.db.get_value('Asset', self.asset, 'company')
		for account in asset_category.accounts:
			if account.company_name == company:
				return account.fixed_asset_account

	def modify_depreciation_schedule(self):
		if self.increase_in_asset_life:
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
		last_schedule_date = asset.schedules[len(asset.schedules)-1].schedule_date
		asset.to_date = add_months(last_schedule_date, extra_months)
		schedule_date = add_months(row.depreciation_start_date,
			number_of_pending_depreciations * cint(row.frequency_of_depreciation))

		if asset.to_date > schedule_date:
			row.total_number_of_depreciations += 1

			
@frappe.whitelist()
def get_downtime(failure_date, completion_date):
	downtime = time_diff_in_hours(completion_date, failure_date)
	return round(downtime, 2)