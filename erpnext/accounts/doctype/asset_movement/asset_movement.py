# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class AssetMovement(Document):
	def validate(self):
		self.validate_asset()
		self.validate_warehouses()
		
	def validate_asset(self):
		status, company = frappe.db.get_value("Asset", self.asset, ["status", "company"])
		if status in ("Draft", "Scrapped", "Sold"):
			frappe.throw(_("{0} asset cannot be transferred").format(status))
			
		if company != self.company:
			frappe.throw(_("Asset {0} does not belong to company {1}").format(self.asset, self.company))
			
	def validate_warehouses(self):
		if not self.source_warehouse:
			self.source_warehouse = frappe.db.get_value("Asset", self.asset, "warehouse")
		
		if self.source_warehouse == self.target_warehouse:
			frappe.throw(_("Source and Target Warehouse cannot be same"))

	def on_submit(self):
		self.set_latest_warehouse_in_asset()
		
	def on_cancel(self):
		self.set_latest_warehouse_in_asset()
		
	def set_latest_warehouse_in_asset(self):
		latest_movement_entry = frappe.db.sql("""select target_warehouse from `tabAsset Movement`
			where asset=%s and docstatus=1 and company=%s
			order by transaction_date desc limit 1""", (self.asset, self.company))
		
		if latest_movement_entry:
			warehouse = latest_movement_entry[0][0]
		else:
			warehouse = frappe.db.sql("""select source_warehouse from `tabAsset Movement`
				where asset=%s and docstatus=2 and company=%s
				order by transaction_date asc limit 1""", (self.asset, self.company))[0][0]
		
		frappe.db.set_value("Asset", self.asset, "warehouse", warehouse)