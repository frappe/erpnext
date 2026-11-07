# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe.utils import add_days, add_months, get_last_day, getdate, nowdate

from erpnext.assets.doctype.asset_maintenance.asset_maintenance import calculate_next_due_date
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt


class TestAssetMaintenance(unittest.TestCase):
	def setUp(self):
		set_depreciation_settings_in_company()
		create_asset_data()
		create_maintenance_team()
		purchase_receipt = make_purchase_receipt(
			item_code="Photocopier", qty=1, rate=100000.0, location="Test Location"
		)
		self.asset_name = frappe.db.get_value("Asset", {"purchase_receipt": purchase_receipt.name}, "name")
		self.asset_doc = frappe.get_doc("Asset", self.asset_name)

	def test_create_asset_maintenance(self):
		pr = make_purchase_receipt(item_code="Photocopier", qty=1, rate=100000.0, location="Test Location")

		asset_name = frappe.db.get_value("Asset", {"purchase_receipt": pr.name}, "name")
		asset_doc = frappe.get_doc("Asset", asset_name)
		month_end_date = get_last_day(nowdate())

		purchase_date = nowdate() if nowdate() != month_end_date else add_days(nowdate(), -15)

		asset_doc.available_for_use_date = purchase_date
		asset_doc.purchase_date = purchase_date

		asset_doc.calculate_depreciation = 1
		asset_doc.append(
			"finance_books",
			{
				"expected_value_after_useful_life": 200,
				"depreciation_method": "Straight Line",
				"total_number_of_depreciations": 3,
				"frequency_of_depreciation": 10,
				"depreciation_start_date": month_end_date,
			},
		)

		asset_doc.save()

		asset_maintenance = frappe.get_doc(
			{
				"doctype": "Asset Maintenance",
				"asset_name": asset_name,
				"maintenance_team": "Team Awesome",
				"company": "_Test Company",
				"asset_maintenance_tasks": get_maintenance_tasks(),
			}
		).insert()

		next_due_date = calculate_next_due_date("Monthly", nowdate())
		self.assertEqual(
			getdate(asset_maintenance.asset_maintenance_tasks[0].next_due_date), getdate(next_due_date)
		)

		asset_maintenance_log = frappe.get_doc(
			"Asset Maintenance Log",
			{"asset_maintenance": asset_maintenance.name, "task_name": "Change Oil"},
		)
		asset_maintenance_log.update({"completion_date": nowdate(), "maintenance_status": "Completed"})
		asset_maintenance_log.submit()

		asset_maintenance.reload()
		next_due_date = calculate_next_due_date("Monthly", nowdate())
		self.assertEqual(
			getdate(asset_maintenance.asset_maintenance_tasks[0].next_due_date), getdate(next_due_date)
		)

	def test_next_due_date_within_end_date(self):
		self.assertEqual(
			getdate(calculate_next_due_date("Monthly", "2026-10-01", "2027-12-31")), getdate("2026-11-01")
		)
		self.assertEqual(
			getdate(calculate_next_due_date("Monthly", "2026-10-01", "2027-12-31", "2026-10-03")),
			getdate("2026-11-03"),
		)
		self.assertEqual(calculate_next_due_date("Monthly", "2026-10-01", "2026-10-15"), "")

		tasks = get_maintenance_tasks()
		tasks[0]["end_date"] = add_days(nowdate(), 365)
		asset_maintenance = self.make_asset_maintenance(tasks)

		self.assertEqual(
			getdate(asset_maintenance.asset_maintenance_tasks[0].next_due_date), add_months(getdate(), 1)
		)

	def test_asset_is_in_maintenance_while_a_due_log_is_open(self):
		from erpnext.assets.doctype.asset.asset import update_maintenance_status

		self.submit_asset()
		tasks = get_maintenance_tasks()[:1]
		tasks[0].update({"start_date": add_months(nowdate(), -1), "next_due_date": add_days(nowdate(), -1)})
		self.make_asset_maintenance(tasks)

		update_maintenance_status()
		self.assertEqual(frappe.db.get_value("Asset", self.asset_name, "status"), "In Maintenance")

		log = frappe.get_last_doc("Asset Maintenance Log", {"asset_name": self.asset_name})
		log.update({"maintenance_status": "Completed", "completion_date": nowdate()})
		log.submit()
		self.assertEqual(frappe.db.get_value("Asset", self.asset_name, "status"), "Submitted")

	def test_removing_a_task_keeps_its_completed_logs(self):
		asset_maintenance = self.make_asset_maintenance()
		removed_task = asset_maintenance.asset_maintenance_tasks[1].name
		completed_log = frappe.get_last_doc("Asset Maintenance Log", {"task": removed_task})
		completed_log.update({"maintenance_status": "Completed", "completion_date": nowdate()})
		completed_log.submit()

		asset_maintenance.reload()
		asset_maintenance.asset_maintenance_tasks.pop()
		asset_maintenance.save()

		statuses = dict(
			frappe.get_all(
				"Asset Maintenance Log", {"task": removed_task}, ["name", "maintenance_status"], as_list=True
			)
		)
		self.assertEqual(statuses.pop(completed_log.name), "Completed")
		self.assertEqual(set(statuses.values()), {"Cancelled"})

	def test_cancelled_or_removed_task_cancels_only_its_open_logs(self):
		asset_maintenance = self.make_asset_maintenance()
		cancelled_task = asset_maintenance.asset_maintenance_tasks[0]
		removed_task = asset_maintenance.asset_maintenance_tasks[1].name
		completed_log = frappe.get_last_doc("Asset Maintenance Log", {"task": removed_task})
		completed_log.update({"maintenance_status": "Completed", "completion_date": nowdate()})
		completed_log.submit()

		asset_maintenance.reload()
		asset_maintenance.asset_maintenance_tasks[0].maintenance_status = "Cancelled"
		asset_maintenance.asset_maintenance_tasks.pop()
		asset_maintenance.save()

		self.assertEqual(
			frappe.db.get_value("Asset Maintenance Log", {"task": cancelled_task.name}, "maintenance_status"),
			"Cancelled",
		)
		statuses = dict(
			frappe.get_all(
				"Asset Maintenance Log", {"task": removed_task}, ["name", "maintenance_status"], as_list=True
			)
		)
		self.assertEqual(statuses.pop(completed_log.name), "Completed")
		self.assertEqual(set(statuses.values()), {"Cancelled"})

	def test_quality_manager_can_save_asset_maintenance(self):
		user = "test_asset_maintenance_qm@example.com"
		if not frappe.db.exists("User", user):
			frappe.get_doc(
				{"doctype": "User", "email": user, "first_name": "QM", "roles": [{"role": "Quality Manager"}]}
			).insert()

		frappe.set_user(user)
		try:
			asset_maintenance = self.make_asset_maintenance()
			asset_maintenance.save()
		finally:
			frappe.set_user("Administrator")

		self.assertTrue(
			frappe.db.exists("Asset Maintenance Log", {"asset_maintenance": asset_maintenance.name})
		)

	def submit_asset(self):
		self.asset_doc.update(
			{"available_for_use_date": nowdate(), "purchase_date": nowdate(), "maintenance_required": 1}
		)
		self.asset_doc.submit()

	def make_asset_maintenance(self, tasks: list[dict] | None = None):
		return frappe.get_doc(
			{
				"doctype": "Asset Maintenance",
				"asset_name": self.asset_name,
				"maintenance_team": "Team Awesome",
				"company": "_Test Company",
				"asset_maintenance_tasks": tasks or get_maintenance_tasks(),
			}
		).insert()


def create_asset_data():
	if not frappe.db.exists("Asset Category", "Equipment"):
		create_asset_category()

	if not frappe.db.exists("Location", "Test Location"):
		frappe.get_doc({"doctype": "Location", "location_name": "Test Location"}).insert()

	if not frappe.db.exists("Item", "Photocopier"):
		meta = frappe.get_meta("Asset")
		naming_series = meta.get_field("naming_series").options
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": "Photocopier",
				"item_name": "Photocopier",
				"item_group": "All Item Groups",
				"company": "_Test Company",
				"is_fixed_asset": 1,
				"is_stock_item": 0,
				"asset_category": "Equipment",
				"auto_create_assets": 1,
				"asset_naming_series": naming_series,
			}
		).insert()


def create_maintenance_team():
	user_list = ["marcus@abc.com", "thalia@abc.com", "mathias@abc.com"]
	if not frappe.db.exists("Role", "Technician"):
		frappe.get_doc({"doctype": "Role", "role_name": "Technician"}).insert()
	for user in user_list:
		if not frappe.db.get_value("User", user):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": user,
					"first_name": user,
					"new_password": "password",
					"roles": [{"doctype": "Has Role", "role": "Technician"}],
				}
			).insert()

	if not frappe.db.exists("Asset Maintenance Team", "Team Awesome"):
		frappe.get_doc(
			{
				"doctype": "Asset Maintenance Team",
				"maintenance_manager": "marcus@abc.com",
				"maintenance_team_name": "Team Awesome",
				"company": "_Test Company",
				"maintenance_team_members": get_maintenance_team(user_list),
			}
		).insert()


def get_maintenance_team(user_list):
	return [
		{"team_member": user, "full_name": user, "maintenance_role": "Technician"} for user in user_list[1:]
	]


def get_maintenance_tasks():
	return [
		{
			"maintenance_task": "Change Oil",
			"start_date": nowdate(),
			"periodicity": "Monthly",
			"maintenance_type": "Preventive Maintenance",
			"maintenance_status": "Planned",
			"assign_to": "marcus@abc.com",
		},
		{
			"maintenance_task": "Check Gears",
			"start_date": nowdate(),
			"periodicity": "Yearly",
			"maintenance_type": "Calibration",
			"maintenance_status": "Planned",
			"assign_to": "thalia@abc.com",
		},
	]


def create_asset_category():
	asset_category = frappe.new_doc("Asset Category")
	asset_category.asset_category_name = "Equipment"
	asset_category.total_number_of_depreciations = 3
	asset_category.frequency_of_depreciation = 3
	asset_category.append(
		"accounts",
		{
			"company_name": "_Test Company",
			"fixed_asset_account": "_Test Fixed Asset - _TC",
			"accumulated_depreciation_account": "_Test Accumulated Depreciations - _TC",
			"depreciation_expense_account": "_Test Depreciations - _TC",
		},
	)
	asset_category.insert()


def set_depreciation_settings_in_company():
	company = frappe.get_doc("Company", "_Test Company")
	company.accumulated_depreciation_account = "_Test Accumulated Depreciations - _TC"
	company.depreciation_expense_account = "_Test Depreciations - _TC"
	company.disposal_account = "_Test Gain/Loss on Asset Disposal - _TC"
	company.depreciation_cost_center = "_Test Cost Center - _TC"
	company.save()

	# Enable booking asset depreciation entry automatically
	frappe.db.set_single_value("Accounts Settings", "book_asset_depreciation_entry_automatically", 1)
