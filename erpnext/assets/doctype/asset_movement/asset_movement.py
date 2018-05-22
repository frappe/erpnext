# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
from frappe.model.document import Document

class AssetMovement(Document):
	def validate(self):
		self.validate_asset()
		self.validate_warehouses()

	def validate_asset(self):
		status, company = frappe.db.get_value("Asset", self.asset, ["status", "company"])
		if self.purpose == 'Transfer' and status in ("Draft", "Scrapped", "Sold"):
			frappe.throw(_("{0} asset cannot be transferred").format(status))

		if company != self.company:
			frappe.throw(_("Asset {0} does not belong to company {1}").format(self.asset, self.company))

		if self.serial_no and len(get_serial_nos(self.serial_no)) != self.quantity:
			frappe.throw(_("Number of serial nos and quantity must be the same"))

		if not(self.source_location or self.target_location or self.from_employee or self.to_employee):
			frappe.throw(_("Either location or employee must be required"))

	def validate_warehouses(self):
		if self.purpose in ['Transfer', 'Issue']:
			self.source_location = frappe.db.get_value("Asset", self.asset, "location")

		if self.source_location == self.target_location:
			frappe.throw(_("Source and Target Location cannot be same"))

	def on_submit(self):
		self.set_latest_location_in_asset()
		
	def on_cancel(self):
		self.set_latest_location_in_asset()

	def set_latest_location_in_asset(self):
		latest_movement_entry = frappe.db.sql("""select target_location from `tabAsset Movement`
			where asset=%s and docstatus=1 and company=%s
			order by transaction_date desc limit 1""", (self.asset, self.company))
		
		if latest_movement_entry:
			location = latest_movement_entry[0][0]
		else:
			location = frappe.db.sql("""select source_location from `tabAsset Movement`
				where asset=%s and docstatus=2 and company=%s
				order by transaction_date asc limit 1""", (self.asset, self.company))[0][0]

		frappe.db.set_value("Asset", self.asset, "location", location)

		if self.serial_no:
			for d in get_serial_nos(self.serial_no):
				frappe.db.set_value('Serial No', d, 'location', location)
