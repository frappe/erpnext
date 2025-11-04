# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import unittest

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, get_last_day, nowdate

from erpnext.assets.doctype.asset_maintenance.asset_maintenance import calculate_next_due_date
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt


class TestAssetMaintenance(IntegrationTestCase):
	def setUp(self):
		set_depreciation_settings_in_company()
		self.pr = make_purchase_receipt(
			item_code="Photocopier", qty=1, rate=100000.0, location="Test Location"
		)
		self.asset_name = frappe.db.get_value("Asset", {"purchase_receipt": self.pr.name}, "name")
		self.asset_doc = frappe.get_doc("Asset", self.asset_name)

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

		asset_maintenance = frappe.get_doc(
			{
				"doctype": "Asset Maintenance",
				"asset_name": self.asset_name,
				"maintenance_team": "Team Awesome",
				"company": "_Test Company",
				"asset_maintenance_tasks": get_maintenance_tasks(),
			}
		).insert()

		next_due_date = calculate_next_due_date(nowdate(), "Monthly")
		self.assertEqual(asset_maintenance.asset_maintenance_tasks[0].next_due_date, next_due_date)

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
		next_due_date = calculate_next_due_date(asset_maintenance_log_doc.completion_date, "Monthly")

		asset_maintenance.reload()
		self.assertEqual(asset_maintenance.asset_maintenance_tasks[0].next_due_date, next_due_date)


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
