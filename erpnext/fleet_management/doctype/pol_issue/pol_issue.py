# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from erpnext.custom_utils import check_future_date
from frappe.utils import flt, cint
from erpnext.controllers.stock_controller import StockController

class POLIssue(StockController):
	def __init__(self, *args, **kwargs):
		super(POLIssue, self).__init__(*args, **kwargs)
	def validate(self):
		check_future_date(self.posting_date)
		self.validate_uom_is_integer("stock_uom", "qty")
		self.update_items()

	def validate_data(self):
		if not self.cost_center or not self.warehouse:
			frappe.throw("Cost Center and Warehouse are Mandatory")
		total_quantity = 0
		for a in self.items:
			if flt(a.qty) <= 0:
				frappe.throw("Quantity for <b>"+str(a.equipment)+"</b> should be greater than 0")
			total_quantity = flt(total_quantity) + flt(a.qty)
		self.total_quantity = total_quantity
		
	def on_submit(self):
		self.update_stock_ledger()
		self.make_gl_entries()
	def on_cancel(self):
		self.update_stock_ledger()
		self.make_gl_entries_on_cancel()

	def update_items(self):
		for a in self.items:
			# item code 
			a.item_code = self.pol_type
			# cost center
			a.cost_center = self.cost_center		
			# Warehouse
			a.warehouse = self.warehouse
			# Expense Account
			a.equipment_category = frappe.db.get_value("Equipment", a.equipment, "equipment_category")
			budget_account = frappe.db.get_value("Equipment Category", a.equipment_category, "budget_account")
			if not budget_account:
				budget_account = frappe.db.get_value("Item Default", {'parent':self.pol_type}, "expense_account")
			if not budget_account:
				frappe.throw("Set Budget Account in Equipment Category")
			a.expense_account = budget_account
	
	def update_stock_ledger(self):
		sl_entries = []
		for a in self.items:
			sl_entries.append(self.get_sl_entries(a, {
				"actual_qty": -1 * flt(a.qty), 
				"warehouse": self.warehouse, 
				"incoming_rate": 0 
			}))

		if self.docstatus == 2:
			sl_entries.reverse()
		self.make_sl_entries(sl_entries, self.amended_from and 'Yes' or 'No')