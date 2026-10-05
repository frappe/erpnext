# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import add_months, getdate, nowdate

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
