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
		for d in self.assets:
			status, company = frappe.db.get_value("Asset", d.asset, ["status", "company"])
			if self.purpose == 'Transfer' and status in ("Draft", "Scrapped", "Sold"):
				frappe.throw(_("{0} asset cannot be transferred").format(status))

			if company != self.company:
				frappe.throw(_("Asset {0} does not belong to company {1}").format(d.asset, self.company))

			if not(d.source_location or d.target_location or d.from_employee or d.to_employee):
				frappe.throw(_("Either location or employee must be required"))

	def validate_location(self):
		if self.purpose in ['Transfer', 'Issue']:
			for d in self.assets:
				if not (d.from_employee or d.to_employee) and not d.source_location:
					d.source_location = frappe.db.get_value("Asset", d.asset, "location")

				if self.purpose == 'Issue' and not (d.source_location or d.from_employee):
					frappe.throw(_("Source Location is required for the asset {0}").format(d.asset))

				if d.source_location:
					current_location = frappe.db.get_value("Asset", d.asset, "location")

					if current_location != d.source_location:
						frappe.throw(_("Asset {0} does not belongs to the location {1}").
							format(d.asset, d.source_location))

		for d in self.assets:
			if d.source_location and d.source_location == d.target_location and self.purpose == 'Transfer':
				frappe.throw(_("Source and Target Location cannot be same"))

			if self.purpose == 'Receipt' and not (d.target_location or d.to_employee):
				frappe.throw(_("Target Location or To Employee is required for the asset {0}").format(d.asset))

	def on_submit(self):
		self.set_latest_location_in_asset()
		
	def on_cancel(self):
		self.set_latest_location_in_asset()

	def set_latest_location_in_asset(self):
		location, employee = '', ''
		cond = "1=1"

		for d in self.assets:
			args = {
				'asset': d.asset,
				'company': self.company
			}

			latest_movement_entry = frappe.db.sql(
				"""
				SELECT 
					`tabAsset Movement Item`.target_location, `tabAsset Movement Item`.to_employee 
				FROM 
					`tabAsset Movement Item`, `tabAsset Movement`
				WHERE 
					`tabAsset Movement Item`.parent=`tabAsset Movement`.name and
					`tabAsset Movement Item`.asset=%(asset)s and
					`tabAsset Movement`.company=%(company)s and 
					`tabAsset Movement`.docstatus=1 and {0}
				ORDER BY
					`tabAsset Movement`.transaction_date desc limit 1
				""".format(cond), args)

			if latest_movement_entry:
				location = latest_movement_entry[0][0]
				employee = latest_movement_entry[0][1]
			elif self.purpose in ['Transfer', 'Receipt']:
				movement_entry = frappe.db.sql(
					"""
					SELECT 
						`tabAsset Movement Item`.target_location, `tabAsset Movement Item`.to_employee 
					FROM 
						`tabAsset Movement Item`, `tabAsset Movement`
					WHERE 
						`tabAsset Movement Item`.parent=`tabAsset Movement`.name and
						`tabAsset Movement Item`.asset=%(asset)s and
						`tabAsset Movement`.company=%(company)s and
						`tabAsset Movement`.docstatus=2 and {0}
					ORDER BY
						`tabAsset Movement`.transaction_date desc limit 1
					""".format(cond), args)

				if movement_entry:
					location = movement_entry[0][0]
					employee = movement_entry[0][1]

			if not employee and self.purpose in ['Receipt', 'Transfer']:
				employee = d.to_employee

			if (location or (self.purpose == 'Issue' and d.source_location)):
				frappe.db.set_value('Asset', d.asset, 'location', location)

			if employee or self.docstatus==2 or self.purpose == 'Issue':
				frappe.db.set_value('Asset', d.asset, 'custodian', employee)
