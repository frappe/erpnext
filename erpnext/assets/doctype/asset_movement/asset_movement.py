# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
<<<<<<< HEAD
from frappe.utils import cstr, get_link_to_form
=======
from frappe.utils import get_link_to_form
>>>>>>> 7c4cf3e834 (Favicon.svg)

from erpnext.assets.doctype.asset_activity.asset_activity import add_asset_activity


class AssetMovement(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.assets.doctype.asset_movement_item.asset_movement_item import AssetMovementItem

		amended_from: DF.Link | None
		assets: DF.Table[AssetMovementItem]
		company: DF.Link
<<<<<<< HEAD
		purpose: DF.Literal["", "Issue", "Receipt", "Transfer", "Transfer and Issue"]
=======
		purpose: DF.Literal["", "Issue", "Receipt", "Transfer"]
>>>>>>> 7c4cf3e834 (Favicon.svg)
		reference_doctype: DF.Link | None
		reference_name: DF.DynamicLink | None
		transaction_date: DF.Datetime
	# end: auto-generated types

	def validate(self):
<<<<<<< HEAD
		for d in self.assets:
			self.validate_asset(d)
			self.validate_movement(d)

	def validate_asset(self, d):
		status, company = frappe.db.get_value("Asset", d.asset, ["status", "company"])
		if self.purpose == "Transfer" and status in ("Draft", "Scrapped", "Sold"):
			frappe.throw(_("{0} asset cannot be transferred").format(status))

		if company != self.company:
			frappe.throw(_("Asset {0} does not belong to company {1}").format(d.asset, self.company))

	def validate_movement(self, d):
		if self.purpose == "Transfer and Issue":
			self.validate_location_and_employee(d)
		elif self.purpose in ["Receipt", "Transfer"]:
			self.validate_location(d)
		else:
			self.validate_employee(d)

	def validate_location_and_employee(self, d):
		self.validate_location(d)
		self.validate_employee(d)

	def validate_location(self, d):
		if self.purpose in ["Transfer", "Transfer and Issue"]:
			current_location = frappe.db.get_value("Asset", d.asset, "location")
			if d.source_location:
				if current_location != d.source_location:
					frappe.throw(
						_("Asset {0} does not belong to the location {1}").format(d.asset, d.source_location)
					)
			else:
				d.source_location = current_location

			if not d.target_location:
				frappe.throw(_("Target Location is required for transferring Asset {0}").format(d.asset))
			if d.source_location == d.target_location:
				frappe.throw(_("Source and Target Location cannot be same"))

		if self.purpose == "Receipt":
			if not d.target_location:
				frappe.throw(_("Target Location is required while receiving Asset {0}").format(d.asset))
			if d.to_employee and frappe.db.get_value("Employee", d.to_employee, "company") != self.company:
				frappe.throw(
					_("Employee {0} does not belong to the company {1}").format(d.to_employee, self.company)
				)

	def validate_employee(self, d):
		if self.purpose == "Transfer and Issue":
			if not d.from_employee:
				frappe.throw(_("From Employee is required while issuing Asset {0}").format(d.asset))

		if d.from_employee:
			current_custodian = frappe.db.get_value("Asset", d.asset, "custodian")

			if current_custodian != d.from_employee:
				frappe.throw(
					_("Asset {0} does not belong to the custodian {1}").format(d.asset, d.from_employee)
				)

		if not d.to_employee:
			frappe.throw(_("Employee is required while issuing Asset {0}").format(d.asset))

		if d.to_employee and frappe.db.get_value("Employee", d.to_employee, "company") != self.company:
			frappe.throw(
				_("Employee {0} does not belong to the company {1}").format(d.to_employee, self.company)
			)

=======
		self.validate_asset()
		self.validate_location()
		self.validate_employee()

	def validate_asset(self):
		for d in self.assets:
			status, company = frappe.db.get_value("Asset", d.asset, ["status", "company"])
			if self.purpose == "Transfer" and status in ("Draft", "Scrapped", "Sold"):
				frappe.throw(_("{0} asset cannot be transferred").format(status))

			if company != self.company:
				frappe.throw(_("Asset {0} does not belong to company {1}").format(d.asset, self.company))

			if not (d.source_location or d.target_location or d.from_employee or d.to_employee):
				frappe.throw(_("Either location or employee must be required"))

	def validate_location(self):
		for d in self.assets:
			if self.purpose in ["Transfer", "Issue"]:
				current_location = frappe.db.get_value("Asset", d.asset, "location")
				if d.source_location:
					if current_location != d.source_location:
						frappe.throw(
							_("Asset {0} does not belongs to the location {1}").format(
								d.asset, d.source_location
							)
						)
				else:
					d.source_location = current_location

			if self.purpose == "Issue":
				if d.target_location:
					frappe.throw(
						_(
							"Issuing cannot be done to a location. Please enter employee to issue the Asset {0} to"
						).format(d.asset),
						title=_("Incorrect Movement Purpose"),
					)
				if not d.to_employee:
					frappe.throw(_("Employee is required while issuing Asset {0}").format(d.asset))

			if self.purpose == "Transfer":
				if d.to_employee:
					frappe.throw(
						_(
							"Transferring cannot be done to an Employee. Please enter location where Asset {0} has to be transferred"
						).format(d.asset),
						title=_("Incorrect Movement Purpose"),
					)
				if not d.target_location:
					frappe.throw(
						_("Target Location is required while transferring Asset {0}").format(d.asset)
					)
				if d.source_location == d.target_location:
					frappe.throw(_("Source and Target Location cannot be same"))

			if self.purpose == "Receipt":
				if not (d.source_location) and not d.target_location and not d.to_employee:
					frappe.throw(
						_("Target Location or To Employee is required while receiving Asset {0}").format(
							d.asset
						)
					)
				elif d.source_location:
					if d.from_employee and not d.target_location:
						frappe.throw(
							_(
								"Target Location is required while receiving Asset {0} from an employee"
							).format(d.asset)
						)
					elif d.to_employee and d.target_location:
						frappe.throw(
							_(
								"Asset {0} cannot be received at a location and given to an employee in a single movement"
							).format(d.asset)
						)

	def validate_employee(self):
		for d in self.assets:
			if d.from_employee:
				current_custodian = frappe.db.get_value("Asset", d.asset, "custodian")

				if current_custodian != d.from_employee:
					frappe.throw(
						_("Asset {0} does not belongs to the custodian {1}").format(d.asset, d.from_employee)
					)

			if d.to_employee and frappe.db.get_value("Employee", d.to_employee, "company") != self.company:
				frappe.throw(
					_("Employee {0} does not belongs to the company {1}").format(d.to_employee, self.company)
				)

>>>>>>> 7c4cf3e834 (Favicon.svg)
	def on_submit(self):
		self.set_latest_location_and_custodian_in_asset()

	def on_cancel(self):
		self.set_latest_location_and_custodian_in_asset()

	def set_latest_location_and_custodian_in_asset(self):
<<<<<<< HEAD
		for d in self.assets:
			current_location, current_employee = self.get_latest_location_and_custodian(d.asset)
			self.update_asset_location_and_custodian(d.asset, current_location, current_employee)
			self.log_asset_activity(d.asset, current_location, current_employee)

	def get_latest_location_and_custodian(self, asset):
		current_location, current_employee = "", ""
		cond = "1=1"

		# latest entry corresponds to current document's location, employee when transaction date > previous dates
		# In case of cancellation it corresponds to previous latest document's location, employee
		args = {"asset": asset, "company": self.company}
		latest_movement_entry = frappe.db.sql(
			f"""
			SELECT asm_item.target_location, asm_item.to_employee
			FROM `tabAsset Movement Item` asm_item
			JOIN `tabAsset Movement` asm ON asm_item.parent = asm.name
			WHERE
				asm_item.asset = %(asset)s AND
				asm.company = %(company)s AND
				asm.docstatus = 1 AND {cond}
			ORDER BY asm.transaction_date DESC
			LIMIT 1
			""",
			args,
		)

		if latest_movement_entry:
			current_location = latest_movement_entry[0][0]
			current_employee = latest_movement_entry[0][1]

		return current_location, current_employee

	def update_asset_location_and_custodian(self, asset_id, location, employee):
		asset = frappe.get_doc("Asset", asset_id)

		if cstr(employee) != asset.custodian:
			frappe.db.set_value("Asset", asset_id, "custodian", cstr(employee))
		if location and location != asset.location:
			frappe.db.set_value("Asset", asset_id, "location", location)

	def log_asset_activity(self, asset_id, location, employee):
		if location and employee:
			add_asset_activity(
				asset_id,
				_("Asset received at Location {0} and issued to Employee {1}").format(
					get_link_to_form("Location", location),
					get_link_to_form("Employee", employee),
				),
			)
		elif location:
			add_asset_activity(
				asset_id,
				_("Asset transferred to Location {0}").format(get_link_to_form("Location", location)),
			)
		elif employee:
			add_asset_activity(
				asset_id,
				_("Asset issued to Employee {0}").format(get_link_to_form("Employee", employee)),
			)
=======
		current_location, current_employee = "", ""
		cond = "1=1"

		for d in self.assets:
			args = {"asset": d.asset, "company": self.company}

			# latest entry corresponds to current document's location, employee when transaction date > previous dates
			# In case of cancellation it corresponds to previous latest document's location, employee
			latest_movement_entry = frappe.db.sql(
				f"""
				SELECT asm_item.target_location, asm_item.to_employee
				FROM `tabAsset Movement Item` asm_item, `tabAsset Movement` asm
				WHERE
					asm_item.parent=asm.name and
					asm_item.asset=%(asset)s and
					asm.company=%(company)s and
					asm.docstatus=1 and {cond}
				ORDER BY
					asm.transaction_date desc limit 1
				""",
				args,
			)
			if latest_movement_entry:
				current_location = latest_movement_entry[0][0]
				current_employee = latest_movement_entry[0][1]

			frappe.db.set_value("Asset", d.asset, "location", current_location, update_modified=False)
			frappe.db.set_value("Asset", d.asset, "custodian", current_employee, update_modified=False)

			if current_location and current_employee:
				add_asset_activity(
					d.asset,
					_("Asset received at Location {0} and issued to Employee {1}").format(
						get_link_to_form("Location", current_location),
						get_link_to_form("Employee", current_employee),
					),
				)
			elif current_location:
				add_asset_activity(
					d.asset,
					_("Asset transferred to Location {0}").format(
						get_link_to_form("Location", current_location)
					),
				)
			elif current_employee:
				add_asset_activity(
					d.asset,
					_("Asset issued to Employee {0}").format(get_link_to_form("Employee", current_employee)),
				)
>>>>>>> 7c4cf3e834 (Favicon.svg)
