# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe.utils import add_days, today

from erpnext.assets.doctype.asset.test_asset import create_asset_data
from erpnext.hr.doctype.employee.test_employee import make_employee
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt


class TestFullandFinalStatement(unittest.TestCase):

	def setUp(self):
		create_asset_data()

	def tearDown(self):
		frappe.db.sql("Delete from `tabFull and Final Statement`")
		frappe.db.sql("Delete from `tabAsset`")
		frappe.db.sql("Delete from `tabAsset Movement`")

	def test_check_bootstraped_data_asset_movement_and_jv_creation(self):
		employee = make_employee("test_fnf@example.com", company="_Test Company")
		movement = create_asset_movement(employee)
		frappe.db.set_value("Employee", employee, "relieving_date", add_days(today(), 30))
		fnf = create_full_and_final_statement(employee)

		payables_bootstraped_component = ["Salary Slip", "Gratuity",
			"Expense Claim", "Bonus", "Leave Encashment"]

		receivable_bootstraped_component = ["Loan", "Employee Advance"]

		#checking payable s and receivables bootstraped value
		self.assertEqual([payable.component for payable in fnf.payables], payables_bootstraped_component)
		self.assertEqual([receivable.component for receivable in fnf.receivables], receivable_bootstraped_component)

		#checking allocated asset
		self.assertIn(movement, [asset.reference for asset in fnf.assets_allocated])

def create_full_and_final_statement(employee):
	fnf = frappe.new_doc("Full and Final Statement")
	fnf.employee = employee
	fnf.transaction_date = today()
	fnf.save()
	return fnf

def create_asset_movement(employee):
	asset_name = create_asset()
	movement = frappe.new_doc("Asset Movement")
	movement.company = "_Test Company"
	movement.purpose = "Issue"
	movement.transaction_date = today()

	movement.append("assets", {
		"asset": asset_name,
		"to_employee": employee
	})

	movement.save()
	movement.submit()
	return movement.name

def create_asset():
	pr = make_purchase_receipt(item_code="Macbook Pro",
			qty=1, rate=100000.0, location="Test Location")

	asset_name = frappe.db.get_value("Asset", {"purchase_receipt": pr.name}, "name")
	asset = frappe.get_doc("Asset", asset_name)
	asset.calculate_depreciation = 0
	asset.available_for_use_date = today()
	asset.submit()
	return asset_name
