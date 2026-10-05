# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import add_days, add_months, get_last_day, getdate, nowdate

from erpnext.assets.doctype.asset_maintenance.asset_maintenance import calculate_next_due_date
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.tests.utils import ERPNextTestSuite


class TestAssetMaintenance(ERPNextTestSuite):
	def setUp(self):
		set_depreciation_settings_in_company()
		self.pr = make_purchase_receipt(
			item_code="Photocopier", qty=1, rate=100000.0, location="Test Location"
		)
		self.asset_name = frappe.db.get_value("Asset", {"purchase_receipt": self.pr.name}, "name")
		self.asset_doc = frappe.get_doc("Asset", self.asset_name)

	def test_get_maintenance_log_counts_by_status(self):
		"""get_maintenance_log uses a v16 dict aggregate field spec
		({"COUNT": "asset_name", "as": "count"}); confirm it runs and returns correct per-status counts
		on both engines (the whitelisted endpoint was previously untested)."""
		from erpnext.assets.doctype.asset_maintenance.asset_maintenance import get_maintenance_log

		self.asset_doc.available_for_use_date = nowdate()
		self.asset_doc.purchase_date = nowdate()
		self.asset_doc.save()

		self.make_asset_maintenance()

		rows = get_maintenance_log(self.asset_name)
		# the dict aggregate spec did not crash and returned grouped rows...
		self.assertTrue(rows)
		self.assertTrue(all("maintenance_status" in r for r in rows))
		# ...and the per-status counts sum to the total number of logs for this asset
		self.assertEqual(
			sum(r["count"] for r in rows),
			frappe.db.count("Asset Maintenance Log", {"asset_name": self.asset_name}),
		)

	def test_create_asset_maintenance_with_log(self):
		month_end_date = get_last_day(nowdate())

		purchase_date = nowdate() if nowdate() != month_end_date else add_days(nowdate(), -15)

		self.asset_doc.available_for_use_date = purchase_date
		self.asset_doc.purchase_date = purchase_date

		self.asset_doc.calculate_depreciation = 1
		self.asset_doc.append(
			"finance_books",
			{
				"expected_value_after_useful_life": 200,
				"depreciation_method": "Straight Line",
				"total_number_of_depreciations": 3,
				"frequency_of_depreciation": 10,
				"depreciation_start_date": month_end_date,
			},
		)

		self.asset_doc.save()

		asset_maintenance = self.make_asset_maintenance()

		next_due_date = calculate_next_due_date("Monthly", nowdate())
		self.assertEqual(
			getdate(asset_maintenance.asset_maintenance_tasks[0].next_due_date), getdate(next_due_date)
		)

		asset_maintenance_log = frappe.db.get_value(
			"Asset Maintenance Log",
			{"asset_maintenance": asset_maintenance.name, "task_name": "Change Oil"},
			"name",
		)

		asset_maintenance_log_doc = frappe.get_doc("Asset Maintenance Log", asset_maintenance_log)
		asset_maintenance_log_doc.update(
			{
				"completion_date": add_days(nowdate(), 2),
				"maintenance_status": "Completed",
			}
		)

		asset_maintenance_log_doc.save()
		next_due_date = calculate_next_due_date("Monthly", nowdate())

		asset_maintenance.reload()
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

	def test_quality_manager_can_save_asset_maintenance(self):
		user = "test_asset_maintenance_qm@example.com"
		if not frappe.db.exists("User", user):
			frappe.get_doc(
				{"doctype": "User", "email": user, "first_name": "QM", "roles": [{"role": "Quality Manager"}]}
			).insert()

		self.submit_asset()
		frappe.set_user(user)
		try:
			asset_maintenance = self.make_asset_maintenance()
			asset_maintenance.save()
		finally:
			frappe.set_user("Administrator")

		self.assertTrue(
			frappe.db.exists("Asset Maintenance Log", {"asset_maintenance": asset_maintenance.name})
		)

	def test_todo_of_an_unassigned_user_is_closed(self):
		asset_maintenance = self.make_asset_maintenance()
		asset_maintenance.asset_maintenance_tasks[1].assign_to = "marcus@abc.com"
		asset_maintenance.save()

		open_todos = frappe.get_all(
			"ToDo",
			filters={"reference_name": asset_maintenance.name, "status": "Open"},
			pluck="allocated_to",
		)
		self.assertEqual(open_todos, ["marcus@abc.com"])

	def test_assign_task_to_user_whose_name_is_not_the_email(self):
		team = frappe.get_doc("Asset Maintenance Team", "Team Awesome")
		team.append(
			"maintenance_team_members", {"team_member": "Administrator", "maintenance_role": "Technician"}
		)
		team.save()
		tasks = get_maintenance_tasks()
		tasks[0]["assign_to"] = "Administrator"

		asset_maintenance = self.make_asset_maintenance(tasks)

		self.assertTrue(
			frappe.db.exists(
				"ToDo",
				{"reference_name": asset_maintenance.name, "allocated_to": "Administrator", "status": "Open"},
			)
		)

	def test_lookups_need_read_permission(self):
		from erpnext.assets.doctype.asset_maintenance.asset_maintenance import (
			get_maintenance_log,
			get_team_members,
		)

		self.make_asset_maintenance()
		self.assertEqual(
			list(get_team_members("User", "thal", "name", 0, 20, {"maintenance_team": "Team Awesome"})),
			[("thalia@abc.com",)],
		)

		user = "test_asset_maintenance_outsider@example.com"
		if not frappe.db.exists("User", user):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": user,
					"first_name": "Outsider",
					"roles": [{"role": "Sales User"}],
				}
			).insert()

		frappe.set_user(user)
		try:
			with self.assertRaises(frappe.PermissionError):
				get_team_members("User", "", "name", 0, 20, {"maintenance_team": "Team Awesome"})
			with self.assertRaises(frappe.PermissionError):
				get_maintenance_log(self.asset_name)
		finally:
			frappe.set_user("Administrator")

	def test_delete_asset_maintenance_with_draft_logs(self):
		asset_maintenance = self.make_asset_maintenance()

		asset_maintenance.delete()

		self.assertFalse(frappe.db.exists("Asset Maintenance", asset_maintenance.name))
		self.assertFalse(
			frappe.db.exists("Asset Maintenance Log", {"asset_maintenance": asset_maintenance.name})
		)

	def test_validations(self):
		tasks = get_maintenance_tasks()
		tasks[0]["assign_to"] = "Administrator"
		self.assertRaisesRegex(frappe.ValidationError, "not a member", self.make_asset_maintenance, tasks)

		tasks = get_maintenance_tasks()
		tasks[0]["next_due_date"] = add_days(nowdate(), -1)
		self.assertRaisesRegex(
			frappe.ValidationError, "before the Start Date", self.make_asset_maintenance, tasks
		)

		tasks[0].update({"start_date": add_months(nowdate(), -1)})
		asset_maintenance = self.make_asset_maintenance(tasks)
		self.assertEqual(asset_maintenance.asset_maintenance_tasks[0].maintenance_status, "Overdue")

		asset_maintenance.asset_maintenance_tasks[0].next_due_date = add_days(nowdate(), 20)
		asset_maintenance.save()
		self.assertEqual(asset_maintenance.asset_maintenance_tasks[0].maintenance_status, "Planned")

	def test_asset_must_be_submitted(self):
		maintenance = frappe.get_doc(
			{
				"doctype": "Asset Maintenance",
				"asset_name": self.asset_name,
				"maintenance_team": "Team Awesome",
				"company": "_Test Company",
				"asset_maintenance_tasks": get_maintenance_tasks(),
			}
		)
		self.assertRaisesRegex(frappe.ValidationError, "must be submitted", maintenance.insert)

	def submit_asset(self):
		self.asset_doc.available_for_use_date = self.asset_doc.available_for_use_date or nowdate()
		self.asset_doc.maintenance_required = 1
		self.asset_doc.submit()

	def make_asset_maintenance(self, tasks: list[dict] | None = None):
		if self.asset_doc.docstatus == 0:
			self.submit_asset()
		return frappe.get_doc(
			{
				"doctype": "Asset Maintenance",
				"asset_name": self.asset_name,
				"maintenance_team": "Team Awesome",
				"company": "_Test Company",
				"asset_maintenance_tasks": tasks or get_maintenance_tasks(),
			}
		).insert()


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


def set_depreciation_settings_in_company():
	company = frappe.get_doc("Company", "_Test Company")
	company.accumulated_depreciation_account = "_Test Accumulated Depreciations - _TC"
	company.depreciation_expense_account = "_Test Depreciations - _TC"
	company.disposal_account = "_Test Gain/Loss on Asset Disposal - _TC"
	company.depreciation_cost_center = "_Test Cost Center - _TC"
	company.save()

	# Enable booking asset depreciation entry automatically
	frappe.db.set_single_value("Accounts Settings", "book_asset_depreciation_entry_automatically", 1)
