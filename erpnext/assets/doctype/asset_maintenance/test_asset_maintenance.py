# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from assets.asset.doctype.asset_.test_asset_ import create_asset, create_asset_data, create_company
from frappe.utils import add_days, nowdate

from erpnext.assets.doctype.asset_maintenance.asset_maintenance import calculate_next_due_date


class TestAssetMaintenance_(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		create_company()
		create_asset_data()
		create_maintenance_personnel()

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()

	def test_start_date_is_before_end_date(self):
		asset = create_asset(maintenance_required=1, submit=1)

		asset_maintenance = create_asset_maintenance(asset.name)
		asset_maintenance.asset_maintenance_tasks[0].start_date = nowdate()
		asset_maintenance.asset_maintenance_tasks[0].end_date = add_days(nowdate(), -1)

		self.assertRaises(frappe.ValidationError, asset_maintenance.save)

	def test_next_due_date_calculation(self):
		asset = create_asset(maintenance_required=1, submit=1)

		asset_maintenance = create_asset_maintenance(asset.name)

		start_date = asset_maintenance.asset_maintenance_tasks[0].start_date
		periodicity = asset_maintenance.asset_maintenance_tasks[0].periodicity

		ideal_next_due_date = calculate_next_due_date(periodicity, start_date)
		actual_next_due_date = asset_maintenance.asset_maintenance_tasks[0].next_due_date

		self.assertEqual(ideal_next_due_date, actual_next_due_date)

	def test_maintenance_status_is_overdue(self):
		"""Tests if maintenance_status is set to Overdue after next_due_date has passed."""

		asset = create_asset(maintenance_required=1, submit=1)

		asset_maintenance = create_asset_maintenance(asset.name)
		asset_maintenance.asset_maintenance_tasks[0].next_due_date = add_days(nowdate(), -1)
		asset_maintenance.save()

		maintenance_status = asset_maintenance.asset_maintenance_tasks[0].maintenance_status
		self.assertEqual(maintenance_status, "Overdue")

	def test_assignee_is_mandatory(self):
		asset = create_asset(maintenance_required=1, submit=1)

		asset_maintenance = create_asset_maintenance(asset.name)
		asset_maintenance.asset_maintenance_tasks[0].assign_to = None

		self.assertRaises(frappe.ValidationError, asset_maintenance.save)

	def test_maintenance_required_is_enabled(self):
		asset = create_asset(maintenance_required=0, submit=1)
		asset_maintenance = create_asset_maintenance(asset_name=asset.name, do_not_save=1)

		self.assertRaises(frappe.ValidationError, asset_maintenance.save)

	def test_serial_no_is_entered_when_the_asset_is_serialized(self):
		asset = create_asset(maintenance_required=1, is_serialized_asset=1, submit=1)
		asset_maintenance = create_asset_maintenance(asset_name=asset.name, do_not_save=1)

		self.assertRaises(frappe.ValidationError, asset_maintenance.save)

	def test_num_of_assets_is_entered_when_the_asset_is_non_serialized(self):
		asset = create_asset(maintenance_required=1, is_serialized_asset=0, submit=1)
		asset_maintenance = create_asset_maintenance(asset_name=asset.name, do_not_save=1)
		asset_maintenance.num_of_assets = 0

		self.assertRaises(frappe.ValidationError, asset_maintenance.save)

	def test_asset_split(self):
		"""Tests if Asset gets split on creating Asset Maintenance with num_of_assets < the Asset's num_of_assets."""

		asset = create_asset(maintenance_required=1, is_serialized_asset=0, num_of_assets=3, submit=1)
		create_asset_maintenance(asset_name=asset.name, num_of_assets=1)

		asset.reload()
		self.assertEqual(asset.num_of_assets, 1)

	def test_assign_tasks(self):
		"""Test if ToDos are created for assignees."""

		asset = create_asset(maintenance_required=1, submit=1)
		asset_maintenance = create_asset_maintenance(asset.name)

		todos = frappe.get_all(
			"ToDo",
			filters={
				"reference_type": asset_maintenance.doctype,
				"reference_name": asset_maintenance.name,
				"status": "Open",
				"allocated_to": asset_maintenance.asset_maintenance_tasks[0].assign_to,
			},
		)

		self.assertTrue(todos)

	def test_maintenance_logs_are_created(self):
		asset = create_asset(maintenance_required=1, submit=1)
		asset_maintenance = create_asset_maintenance(asset.name)

		for task in asset_maintenance.asset_maintenance_tasks:
			maintenance_log = asset_maintenance.get_maintenance_log(task)
			self.assertTrue(maintenance_log)


def create_maintenance_personnel():
	user_list = ["dwight@dm.com", "jim@dm.com", "pam@dm.com"]

	if not frappe.db.exists("Role", "Technician"):
		create_role("Technician")

	for user in user_list:
		if not frappe.db.get_value("User", user):
			create_user(user)

	if not frappe.db.exists("Asset Maintenance Team", "Team Dunder Mifflin"):
		create_maintenance_team(user_list)


def create_role(role_name):
	frappe.get_doc({"doctype": "Role", "role_name": role_name}).insert()


def create_user(user):
	frappe.get_doc(
		{
			"doctype": "User",
			"email": user,
			"first_name": user,
			"new_password": "password",
			"roles": [{"doctype": "Has Role", "role": "Technician"}],
		}
	).insert()


def create_maintenance_team(user_list):
	frappe.get_doc(
		{
			"doctype": "Asset Maintenance Team",
			"maintenance_manager": "dwight@dm.com",
			"maintenance_team_name": "Team Dunder Mifflin",
			"company": "_Test Company",
			"maintenance_team_members": get_maintenance_team_members(user_list),
		}
	).insert()


def get_maintenance_team_members(user_list):
	maintenance_team_members = []

	for user in user_list[1:]:
		maintenance_team_members.append(
			{"team_member": user, "full_name": user, "maintenance_role": "Technician"}
		)

	return maintenance_team_members


def create_asset_maintenance(asset_name, num_of_assets=0, serial_no=None, do_not_save=False):
	asset_maintenance = frappe.get_doc(
		{
			"doctype": "Asset Maintenance",
			"asset": asset_name,
			"num_of_assets": num_of_assets or (0 if serial_no else 1),
			"serial_no": serial_no,
			"maintenance_team": "Team Dunder Mifflin",
			"company": "_Test Company",
			"asset_maintenance_tasks": get_maintenance_tasks(),
		}
	)

	if not do_not_save:
		try:
			asset_maintenance.insert(ignore_if_duplicate=True)
		except frappe.DuplicateEntryError:
			pass

	return asset_maintenance


def get_maintenance_tasks():
	return [
		{
			"maintenance_task": "Antivirus Scan",
			"start_date": nowdate(),
			"periodicity": "Monthly",
			"maintenance_type": "Preventive Maintenance",
			"maintenance_status": "Planned",
			"assign_to": "jim@dm.com",
		},
		{
			"maintenance_task": "Check Gears",
			"start_date": nowdate(),
			"periodicity": "Yearly",
			"maintenance_type": "Calibration",
			"maintenance_status": "Planned",
			"assign_to": "pam@dm.com",
		},
	]
