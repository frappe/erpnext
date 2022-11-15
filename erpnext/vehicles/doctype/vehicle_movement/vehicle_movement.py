# -*- coding: utf-8 -*-
# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from erpnext.vehicles.vehicle_transaction_controller import VehicleTransactionController


class VehicleMovement(VehicleTransactionController):
	def get_feed(self):
		return _("{0} -> {1}").format(self.get("warehouse"), self.get("target_warehouse"))

	def validate(self):
		super(VehicleMovement, self).validate()
		self.validate_warehouse()
		self.set_title()

	def before_submit(self):
		self.validate_vehicle_mandatory()

	def on_submit(self):
		self.update_stock_ledger()

	def on_cancel(self):
		self.update_stock_ledger()

	def set_title(self):
		titles = [self.vehicle_license_plate, self.vehicle_chassis_no]
		titles = [t for t in titles if t]
		if titles:
			self.title = " | ".join(titles)

	def validate_warehouse(self):
		if not self.warehouse:
			frappe.throw(_("Source Warehouse is mandatory"))
		if not self.target_warehouse:
			frappe.throw(_("Target Warehouse is mandatory"))
		if self.target_warehouse == self.warehouse:
			frappe.throw(_("Source Warehouse and Target Warehouse cannot be the same"))

	def update_stock_ledger(self):
		source_sle = self.get_sl_entries(self, {
			"warehouse": self.warehouse,
			"actual_qty": -1,
			"incoming_rate": 0
		})

		target_sle = self.get_sl_entries(self, {
			"warehouse": self.target_warehouse,
			"actual_qty": 1,
			"incoming_rate": 0
		})

		# SLE Dependency
		if self.docstatus == 1:
			target_sle.dependencies = [{
				"dependent_voucher_type": self.doctype,
				"dependent_voucher_no": self.name,
				"dependent_voucher_detail_no": self.name,
				"dependency_type": "Amount",
			}]

		sl_entries = [source_sle, target_sle]
		self.make_sl_entries(sl_entries, self.amended_from and 'Yes' or 'No')
