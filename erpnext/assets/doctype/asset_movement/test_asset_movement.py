# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe.utils import nowdate

from erpnext.assets.doctype.asset.test_asset import (
	create_asset,
	create_asset_data,
	create_company,
	create_location,
)
from erpnext.hr.doctype.employee.test_employee import make_employee


class TestAssetMovement(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		create_company()
		create_asset_data()
		create_location("Test Location2")
		make_employee("assetmovement@abc.com", company="_Test Company")

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()

	def test_movement_is_created_on_asset_submission(self):
		asset = create_asset(submit=1)
		asset_movement = frappe.get_last_doc("Asset Movement")

		self.assertEqual(asset_movement.purpose, "Receipt")
		self.assertEqual(asset_movement.assets[0].asset, asset.name)

	def test_transfer_draft_asset(self):
		asset = create_asset(submit=0)
		asset_movement = create_asset_movement(
			purpose="Transfer",
			company=asset.company,
			assets=[
				{"asset": asset.name, "source_location": "Test Location", "target_location": "Test Location2"}
			],
			do_not_save=1,
		)

		self.assertRaises(frappe.ValidationError, asset_movement.save)

	def test_employee_or_location_are_mandatory(self):
		asset = create_asset(submit=1)
		asset_movement = create_asset_movement(
			purpose="Transfer", company=asset.company, assets=[{"asset": asset.name}], do_not_save=1
		)

		self.assertRaises(frappe.ValidationError, asset_movement.save)

	def test_serial_no_mandatory_for_serialized_asset(self):
		asset = create_asset(is_serialized_asset=1, submit=1)
		asset_movement = create_asset_movement(
			purpose="Transfer",
			company=asset.company,
			assets=[
				{"asset": asset.name, "source_location": "Test Location", "target_location": "Test Location2"}
			],
			do_not_save=1,
		)

		self.assertRaises(frappe.ValidationError, asset_movement.save)

	def test_source_location_is_fetched_from_asset(self):
		asset = create_asset()
		asset.location = "Test Location"
		asset.submit()

		asset_movement = create_asset_movement(
			purpose="Transfer",
			company=asset.company,
			assets=[{"asset": asset.name, "source_location": None, "target_location": "Test Location2"}],
		)

		self.assertEqual(asset_movement.assets[0].source_location, asset.location)

	def test_source_location_is_the_same_as_asset_location(self):
		create_location("Test Location3")

		asset = create_asset()
		asset.location = "Test Location"
		asset.submit()

		asset_movement = create_asset_movement(
			purpose="Transfer",
			company=asset.company,
			assets=[
				{"asset": asset.name, "source_location": "Test Location2", "target_location": "Test Location3"}
			],
			do_not_save=1,
		)

		self.assertRaises(frappe.ValidationError, asset_movement.save)

	def test_issue_asset_to_a_location(self):
		asset = create_asset(submit=1)

		asset_movement = create_asset_movement(
			purpose="Issue",
			company=asset.company,
			assets=[
				{"asset": asset.name, "source_location": "Test Location", "target_location": "Test Location2"}
			],
			do_not_save=1,
		)

		self.assertRaises(frappe.ValidationError, asset_movement.save)

	def test_to_employee_mandatory_for_asset_issue(self):
		asset = create_asset(submit=1)

		asset_movement = create_asset_movement(
			purpose="Issue",
			company=asset.company,
			assets=[{"asset": asset.name, "source_location": "Test Location", "to_employee": None}],
			do_not_save=1,
		)

		self.assertRaises(frappe.ValidationError, asset_movement.save)

	def test_target_location_mandatory_for_asset_transfer(self):
		asset = create_asset(submit=1)

		asset_movement = create_asset_movement(
			purpose="Transfer",
			company=asset.company,
			assets=[{"asset": asset.name, "source_location": "Test Location", "target_location": None}],
			do_not_save=1,
		)

		self.assertRaises(frappe.ValidationError, asset_movement.save)

	def test_target_location_same_as_source_location_asset_transfer(self):
		asset = create_asset(submit=1)

		asset_movement = create_asset_movement(
			purpose="Transfer",
			company=asset.company,
			assets=[
				{"asset": asset.name, "source_location": "Test Location", "target_location": "Test Location"}
			],
			do_not_save=1,
		)

		self.assertRaises(frappe.ValidationError, asset_movement.save)

	def test_transfer_asset_to_employee(self):
		asset = create_asset(submit=1)

		asset_movement = create_asset_movement(
			purpose="Transfer",
			company=asset.company,
			assets=[{"asset": asset.name, "source_location": "Test Location", "to_employee": "EMP-00001"}],
			do_not_save=1,
		)

		self.assertRaises(frappe.ValidationError, asset_movement.save)

	def test_from_employee_is_mandatory_during_receipt(self):
		asset = create_asset(submit=1)

		asset_movement = create_asset_movement(
			purpose="Receipt",
			company=asset.company,
			assets=[
				{
					"asset": asset.name,
					"source_location": "Test Location",
					"target_location": "Test Location2",
					"from_employee": None,
				}
			],
			do_not_save=1,
		)

		self.assertRaises(frappe.ValidationError, asset_movement.save)

	def test_target_location_is_mandatory_during_receipt(self):
		asset = create_asset(submit=1)

		asset_movement = create_asset_movement(
			purpose="Receipt",
			company=asset.company,
			assets=[
				{
					"asset": asset.name,
					"source_location": "Test Location",
					"target_location": None,
					"from_employee": "EMP-00001",
				}
			],
			do_not_save=1,
		)

		self.assertRaises(frappe.ValidationError, asset_movement.save)

	def test_receipt_has_both_target_location_and_to_employee(self):
		asset = create_asset(submit=1)
		to_employee = make_employee("assetmovement2@abc.com", company="_Test Company")

		asset_movement = create_asset_movement(
			purpose="Receipt",
			company=asset.company,
			assets=[
				{
					"asset": asset.name,
					"source_location": "Test Location",
					"target_location": "Test Location2",
					"from_employee": "EMP-00001",
					"to_employee": to_employee,
				}
			],
			do_not_save=1,
		)

		self.assertRaises(frappe.ValidationError, asset_movement.save)

	def test_from_employee_is_asset_custodian(self):
		asset = create_asset(custodian="EMP-00001", submit=1)
		from_employee = make_employee("assetmovement2@abc.com", company="_Test Company")

		asset_movement = create_asset_movement(
			purpose="Transfer",
			company=asset.company,
			assets=[
				{
					"asset": asset.name,
					"source_location": "Test Location",
					"target_location": "Test Location2",
					"from_employee": from_employee,
				}
			],
			do_not_save=1,
		)

		self.assertRaises(frappe.ValidationError, asset_movement.save)

	def test_to_employee_belongs_to_the_same_company(self):
		asset = create_asset(custodian="EMP-00001", submit=1)
		to_employee = make_employee("assetmovement21@abc.com", company="_Test Company 2")

		self.assertEqual(frappe.db.get_value("Employee", to_employee, "company"), "_Test Company 2")

		asset_movement = create_asset_movement(
			purpose="Issue",
			company=asset.company,
			assets=[{"asset": asset.name, "from_employee": "EMP-00001", "to_employee": to_employee}],
			do_not_save=1,
		)

		self.assertRaises(frappe.ValidationError, asset_movement.save)


def create_asset_movement(**args):
	args = frappe._dict(args)

	if not args.transaction_date:
		args.transaction_date = nowdate()

	movement = frappe.new_doc("Asset Movement")
	movement.update(
		{
			"assets": args.assets,
			"transaction_date": args.transaction_date,
			"company": args.company or "_Test Company",
			"purpose": args.purpose or "Receipt",
			"reference_doctype": args.reference_doctype,
			"reference_name": args.reference_name,
		}
	)

	if not args.do_not_save:
		movement.insert()

		if args.submit:
			movement.submit()

	return movement
