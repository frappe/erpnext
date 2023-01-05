# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from erpnext.controllers.status_updater import StatusUpdater
from frappe.utils import flt


class HandlingUnit(StatusUpdater):
	def validate(self):
		self.set_status()

	def set_status(self, update=False, status=None, update_modified=True):
		previous_status = self.status

		has_stock_ledger_entry = self.has_stock_ledger_entry()
		stock_qty = self.get_stock_qty()

		if has_stock_ledger_entry:
			if stock_qty:
				self.status = "In Stock"
			else:
				self.status = "Delivered"
		else:
			self.status = "Inactive"

		self.add_status_comment(previous_status)

		if update:
			self.db_set('status', self.status, update_modified=update_modified)

	def has_stock_ledger_entry(self):
		if self.is_new():
			return False

		return frappe.db.exists("Stock Ledger Entry", {"handling_unit": self.name})

	def get_stock_qty(self):
		if self.is_new():
			return 0

		stock_qty = frappe.db.sql("""
			select sum(actual_qty)
			from `tabStock Ledger Entry`
			where handling_unit = %s
		""", self.name)

		return flt(stock_qty[0][0]) if stock_qty else 0
