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
		self.validate_location()

	def validate_asset(self):
		status, company = frappe.db.get_value("Asset", self.asset, ["status", "company"])
		if self.purpose == 'Transfer' and status in ("Draft", "Scrapped", "Sold"):
			frappe.throw(_("{0} asset cannot be transferred").format(status))

		if company != self.company:
			frappe.throw(_("Asset {0} does not belong to company {1}").format(self.asset, self.company))

		if not(self.source_location or self.target_location or self.from_employee or self.to_employee):
			frappe.throw(_("Either location or employee must be required"))

	def validate_location(self):
		if self.purpose in ['Transfer', 'Issue']:
			if not (self.from_employee or self.to_employee):
				self.source_location = frappe.db.get_value("Asset", self.asset, "location")

			if self.purpose == 'Issue' and not (self.source_location or self.from_employee):
				frappe.throw(_("Source Location is required for the asset {0}").format(self.asset))

		if self.source_location and self.source_location == self.target_location and self.purpose == 'Transfer':
			frappe.throw(_("Source and Target Location cannot be same"))

		if self.purpose == 'Receipt' and not (self.target_location or self.to_employee):
			frappe.throw(_("Target Location is required for the asset {0}").format(self.asset))

	def on_submit(self):
		self.set_latest_location_in_asset()
		
	def on_cancel(self):
		self.set_latest_location_in_asset()

	def set_latest_location_in_asset(self):
		location, employee = '', ''
		cond = "1=1"

		args = {
			'asset': self.asset,
			'company': self.company
		}

		latest_movement_entry = frappe.db.sql("""select target_location, to_employee from `tabAsset Movement`
			where asset=%(asset)s and docstatus=1 and company=%(company)s and {0}
			order by transaction_date desc limit 1""".format(cond), args)

		if latest_movement_entry:
			location = latest_movement_entry[0][0]
			employee = latest_movement_entry[0][1]
		elif self.purpose in ['Transfer', 'Receipt']:
			movement_entry = frappe.db.sql("""select source_location, from_employee from `tabAsset Movement`
				where asset=%(asset)s and docstatus=2 and company=%(company)s and {0}
				order by transaction_date asc limit 1""".format(cond), args)
			if movement_entry:
				location = movement_entry[0][0]
				employee = movement_entry[0][1]

		frappe.db.set_value("Asset", self.asset, "location", location)

		if not employee and self.purpose in ['Receipt', 'Transfer']:
			employee = self.to_employee

