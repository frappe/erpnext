# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import add_days, add_months, getdate, nowdate

from erpnext.assets.doctype.asset_maintenance.test_asset_maintenance import (
	get_maintenance_tasks,
	set_depreciation_settings_in_company,
)
from erpnext.assets.doctype.asset_maintenance_log.asset_maintenance_log import (
	get_maintenance_tasks as task_query,
)
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.tests.utils import ERPNextTestSuite


class TestAssetMaintenanceLog(ERPNextTestSuite):
	def setUp(self):
		set_depreciation_settings_in_company()
		self.asset_maintenance = make_asset_maintenance()

	def test_task_query_returns_task_names(self):
		task = self.asset_maintenance.asset_maintenance_tasks[0]

		tasks = task_query(
			"Asset Maintenance Task", "Oil", "name", 0, 20, {"asset_maintenance": self.asset_maintenance.name}
		)

		self.assertEqual(list(tasks), [(task.name, "Change Oil")])

		user = "test_asset_maintenance_log_outsider@example.com"
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
				task_query(
					"Asset Maintenance Task",
					"",
					"name",
					0,
					20,
					{"asset_maintenance": self.asset_maintenance.name},
				)
		finally:
			frappe.set_user("Administrator")

	def test_cancelling_a_completed_log_reverts_the_task(self):
		task = self.asset_maintenance.asset_maintenance_tasks[0]
		log = get_open_log(task.name)
		log.update({"maintenance_status": "Completed", "completion_date": nowdate()})
		log.submit()
		self.assertEqual(getdate(get_open_log(task.name).due_date), add_months(getdate(), 1))

		log.cancel()

		task.reload()
		self.assertIsNone(task.last_completion_date)
		self.assertEqual(getdate(task.next_due_date), getdate())
		self.assertEqual(getdate(get_open_log(task.name).due_date), getdate())

	def test_cancelled_log_does_not_reschedule_the_task(self):
		task = self.asset_maintenance.asset_maintenance_tasks[0]
		log = get_open_log(task.name)
		log.maintenance_status = "Cancelled"
		log.submit()

		self.asset_maintenance.reload()
		self.asset_maintenance.save()

		task.reload()
		self.assertEqual(task.maintenance_status, "Cancelled")
		self.assertFalse(frappe.db.exists("Asset Maintenance Log", {"task": task.name, "docstatus": 0}))

	def test_task_and_completion_date_validations(self):
		other_task = make_asset_maintenance().asset_maintenance_tasks[0]
		log = get_open_log(self.asset_maintenance.asset_maintenance_tasks[0].name)
		log.task = other_task.name

		self.assertRaisesRegex(frappe.ValidationError, "does not belong", log.save)

		log.reload()
		log.task = None
		self.assertRaisesRegex(frappe.ValidationError, "select a Task", log.save)

		log.reload()
		log.update({"maintenance_status": "Completed", "completion_date": add_days(nowdate(), 1)})
		self.assertRaisesRegex(frappe.ValidationError, "cannot be in the future", log.save)

	def test_overdue_status_follows_the_due_date(self):
		from erpnext.assets.doctype.asset_maintenance_log.asset_maintenance_log import (
			update_asset_maintenance_log_status,
		)

		task = self.asset_maintenance.asset_maintenance_tasks[0]
		frappe.db.set_value(
			"Asset Maintenance Log", get_open_log(task.name).name, "due_date", add_days(nowdate(), -1)
		)
		frappe.db.set_value("Asset Maintenance Task", task.name, "next_due_date", add_days(nowdate(), -1))

		update_asset_maintenance_log_status()
		self.assertEqual(
			frappe.db.get_value("Asset Maintenance Task", task.name, "maintenance_status"), "Overdue"
		)
		log = get_open_log(task.name)
		self.assertEqual(log.maintenance_status, "Overdue")

		frappe.db.set_value("Asset Maintenance Task", task.name, "next_due_date", add_days(nowdate(), 10))
		log.save()
		self.assertEqual(log.maintenance_status, "Planned")


def get_open_log(task: str):
	return frappe.get_doc("Asset Maintenance Log", {"task": task, "docstatus": 0})


def make_asset_maintenance():
	purchase_receipt = make_purchase_receipt(
		item_code="Photocopier", qty=1, rate=100000.0, location="Test Location"
	)
	asset = frappe.db.get_value("Asset", {"purchase_receipt": purchase_receipt.name}, "name")
	tasks = get_maintenance_tasks()
	for task in tasks:
		task["next_due_date"] = nowdate()

	return frappe.get_doc(
		{
			"doctype": "Asset Maintenance",
			"asset_name": asset,
			"maintenance_team": "Team Awesome",
			"company": "_Test Company",
			"asset_maintenance_tasks": tasks,
		}
	).insert()
