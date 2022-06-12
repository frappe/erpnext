# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document

from erpnext.assets.doctype.asset_activity.asset_activity import create_asset_activity


class AssetMovement(Document):
	def validate(self):
		self.validate_asset()
		self.validate_movement()
		self.validate_employee()

	def on_submit(self):
		self.update_asset_location_and_custodian()
		self.record_asset_movements()

	def on_cancel(self):
		self.update_asset_location_and_custodian()

	def validate_asset(self):
		for asset in self.assets:
			status, company, is_serialized_asset, num_of_assets = frappe.db.get_value(
				"Asset", asset.asset, ["status", "company", "is_serialized_asset", "num_of_assets"]
			)

			self.validate_movement_fields(asset)
			self.validate_asset_status(asset, status)
			self.validate_company(asset, company)

			if is_serialized_asset:
				self.validate_serial_no(asset)
			else:
				self.validate_num_of_assets(asset, num_of_assets)

	def validate_movement_fields(self, asset):
		if not (
			asset.source_location or asset.target_location or asset.from_employee or asset.to_employee
		):
			frappe.throw(_("Either location or employee must be entered."))

	def validate_asset_status(self, asset, status):
		if self.purpose == "Transfer" and status in ("Draft", "Scrapped", "Sold"):
			frappe.throw(_("Row {0}: {1} asset cannot be transferred.").format(asset.idx, status))

	def validate_company(self, asset, company):
		if company != self.company:
			frappe.throw(
				_("Row {0}: {1} does not belong to company {2}.").format(asset.idx, asset.asset, self.company)
			)

	def validate_serial_no(self, asset):
		if not asset.serial_no:
			frappe.throw(_("Row {0}: Enter Serial No for Asset {1}").format(asset.idx, asset.asset))

	def validate_num_of_assets(self, asset, num_of_assets):
		if not asset.num_of_assets:
			asset.num_of_assets = num_of_assets

		if asset.num_of_assets > num_of_assets:
			frappe.throw(
				_("Row {0}: Number of Assets cannot be greater than {1}").format(
					asset.idx, frappe.bold(num_of_assets)
				),
				title=_("Number Exceeded Limit"),
			)

		if asset.num_of_assets < 1:
			frappe.throw(
				_("Row {0}: Number of Assets needs to be between <b>1</b> and {1}").format(
					asset.idx, frappe.bold(num_of_assets)
				),
				title=_("Invalid Number"),
			)

	def validate_movement(self):
		for asset in self.assets:
			if self.purpose in ["Transfer", "Issue"]:
				self.validate_source_location(asset)

				if self.purpose == "Issue":
					self.validate_asset_issue(asset)
				if self.purpose == "Transfer":
					self.validate_asset_transfer(asset)

			else:
				self.validate_asset_receipt(asset)

	def validate_source_location(self, asset):
		current_location = self.get_current_location(asset)

		if not asset.source_location:
			if not current_location:
				frappe.throw(_("Source Location is required for the Asset {0}").format(asset.asset))
			else:
				asset.source_location = current_location
		else:
			if current_location != asset.source_location:
				frappe.throw(
					_("Asset {0} is currently located at {1}, not {2}.").format(
						asset.asset, current_location, asset.source_location
					)
				)

	def get_current_location(self, asset):
		current_location, is_serialized_asset = frappe.db.get_value(
			"Asset", asset.asset, ["location", "is_serialized_asset"]
		)

		if is_serialized_asset:
			current_location = frappe.db.get_value("Asset Serial No", asset.serial_no, "location")

		return current_location

	def validate_asset_issue(self, asset):
		if asset.target_location:
			frappe.throw(
				_(
					"Issuing cannot be done to a location. Please enter employee who has issued Asset {0}."
				).format(asset.asset),
				title=_("Incorrect Movement Purpose"),
			)

		if not asset.to_employee:
			frappe.throw(_("Employee is required while issuing Asset {0}").format(asset.asset))

	def validate_asset_transfer(self, asset):
		if asset.to_employee:
			frappe.throw(
				_(
					"Transferring cannot be done to an Employee. Please enter location where Asset {0} has to be transferred."
				).format(asset.asset),
				title=_("Incorrect Movement Purpose"),
			)

		if not asset.target_location:
			frappe.throw(_("Target Location is required while transferring Asset {0}").format(asset.asset))

		if asset.source_location == asset.target_location:
			frappe.throw(_("Source and Target Location cannot be same"))

	def validate_asset_receipt(self, asset):
		# only when asset is bought and first entry is made
		if not asset.source_location and not (asset.target_location or asset.to_employee):
			frappe.throw(
				_("Target Location or To Employee is required while receiving Asset {0}").format(asset.asset)
			)

		elif asset.source_location:
			if asset.target_location and not asset.from_employee:
				frappe.throw(
					_("From employee is required while receiving Asset {0} at a target location").format(
						asset.asset
					)
				)

			if asset.from_employee and not asset.target_location:
				frappe.throw(
					_("Target Location is required while receiving Asset {0} from an employee").format(
						asset.asset
					)
				)

			if asset.to_employee and asset.target_location:
				frappe.throw(
					_(
						"Asset {0} cannot be received at a location and given to employee in a single movement"
					).format(asset.asset)
				)

	def validate_employee(self):
		for row in self.assets:
			if row.from_employee:
				self.validate_from_employee(row)

			if row.to_employee:
				self.validate_to_employee(row)

	def validate_from_employee(self, row):
		current_custodian = self.get_current_custodian(row)

		if current_custodian != row.from_employee:
			frappe.throw(
				_("Asset {0} currently belongs to {1}, not {2}.").format(
					row.asset, current_custodian, row.from_employee
				)
			)

	def get_current_custodian(self, row):
		current_custodian, is_serialized_asset = frappe.db.get_value(
			"Asset", row.asset, ["custodian", "is_serialized_asset"]
		)

		if is_serialized_asset:
			current_custodian = frappe.db.get_value("Asset Serial No", row.serial_no, "custodian")

		return current_custodian

	def validate_to_employee(self, row):
		if frappe.db.get_value("Employee", row.to_employee, "company") != self.company:
			frappe.throw(
				_("Employee {0} does not belong to the company {1}").format(row.to_employee, self.company)
			)

	def update_asset_location_and_custodian(self):
		current_location, current_custodian = "", ""
		assets_to_be_updated = self.get_assets_to_be_updated()

		for d in self.assets:
			if d.asset in assets_to_be_updated:
				args = {"asset": d.asset, "company": self.company, "serial_no": d.serial_no}

				current_location, current_custodian = self.get_current_location_and_custodian(args)

				if d.serial_no:
					frappe.db.set_value("Asset Serial No", d.serial_no, "location", current_location)
					frappe.db.set_value("Asset Serial No", d.serial_no, "custodian", current_custodian)
				else:
					frappe.db.set_value("Asset", d.asset, "location", current_location)
					frappe.db.set_value("Asset", d.asset, "custodian", current_custodian)

	def get_assets_to_be_updated(self):
		assets_being_moved = [d.asset for d in self.assets]

		submitted_assets_being_moved = frappe.get_all(
			"Asset", filters={"docstatus": 1, "name": ["in", assets_being_moved]}, pluck="name"
		)
		return submitted_assets_being_moved

	def get_current_location_and_custodian(self, args):
		cond = "1=1"

		# latest entry corresponds to current document's location, custodian when transaction date > previous dates
		# In case of cancellation it corresponds to previous latest document's location, custodian
		latest_movement_entry = frappe.db.sql(
			"""
			SELECT asm_item.target_location, asm_item.to_employee
			FROM `tabAsset Movement Item` asm_item, `tabAsset Movement` asm
			WHERE
				asm_item.parent=asm.name and
				asm_item.asset=%(asset)s and
				asm_item.serial_no=%(serial_no)s and
				asm.company=%(company)s and
				asm.docstatus=1 and {0}
			ORDER BY
				asm.transaction_date desc limit 1
			""".format(
				cond
			),
			args,
		)

		if latest_movement_entry:
			return latest_movement_entry[0][0], latest_movement_entry[0][1]
		else:
			frappe.throw(
				_("Unable to update Custodian and Location for Asset {0}").format(frappe.bold(args["asset"]))
			)

	def record_asset_movements(self):
		for asset in self.assets:
			if self.purpose == "Issue":
				create_asset_activity(
					asset=asset.asset,
					asset_serial_no=asset.serial_no,
					activity_type="Movement",
					reference_doctype=self.doctype,
					reference_docname=self.name,
					notes=_("Issued to Employee {0} from {1}").format(asset.to_employee, asset.source_location),
				)
			elif self.purpose == "Receipt":
				# when asset is first received after purchase
				if not (asset.from_employee or asset.source_location):
					create_asset_activity(
						asset=asset.asset,
						asset_serial_no=asset.serial_no,
						activity_type="Movement",
						reference_doctype=self.doctype,
						reference_docname=self.name,
						notes=_("Received at Location {0}").format(asset.target_location),
					)
				else:
					create_asset_activity(
						asset=asset.asset,
						asset_serial_no=asset.serial_no,
						activity_type="Movement",
						reference_doctype=self.doctype,
						reference_docname=self.name,
						notes=_("Received at Location {0} from Employee {1}").format(
							asset.target_location, asset.from_employee
						),
					)
			else:
				create_asset_activity(
					asset=asset.asset,
					asset_serial_no=asset.serial_no,
					activity_type="Movement",
					reference_doctype=self.doctype,
					reference_docname=self.name,
					notes=_("Transferred from {0} to {1}").format(asset.source_location, asset.target_location),
				)
