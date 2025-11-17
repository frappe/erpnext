# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import unittest

import frappe

test_records = frappe.get_test_records("Cost Center")


class TestCostCenter(unittest.TestCase):
	def test_cost_center_creation_against_child_node(self):
		if not frappe.db.get_value("Cost Center", {"name": "_Test Cost Center 2 - _TC"}):
			frappe.get_doc(test_records[1]).insert()

		cost_center = frappe.get_doc(
			{
				"doctype": "Cost Center",
				"cost_center_name": "_Test Cost Center 3",
				"parent_cost_center": "_Test Cost Center 2 - _TC",
				"is_group": 0,
				"company": "_Test Company",
			}
		)

		self.assertRaises(frappe.ValidationError, cost_center.save)

	def setUp(self):
		self.company = "_Test Company"
		self.company_abbr = "_TC"
		self.root_cost_center = f"{self.company} - {self.company_abbr}"

		# Ensure the parent exists
		if not frappe.db.exists("Cost Center", self.root_cost_center):
			frappe.get_doc(
				{
					"doctype": "Cost Center",
					"cost_center_name": self.company,
					"company": self.company,
					"is_group": 1,
				}
			).insert()

	def test_validate_mandatory_TC_ACC_277(self):
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "Cost Center",
					"cost_center_name": self.company,
					"company": self.company,
					"parent_cost_center": self.root_cost_center,
					"is_group": 1,
				}
			).insert()

		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "Cost Center",
					"cost_center_name": "Test No Parent",
					"company": self.company,
					"is_group": 0,
				}
			).insert()

	def test_convert_group_to_ledger_TC_ACC_278(self):
		parent_name = "Parent Group CC - _TC"
		child_name = "Child of Group CC - _TC"

		# Ensure parent exists and is a group
		if frappe.db.exists("Cost Center", parent_name):
			parent = frappe.get_doc("Cost Center", parent_name)
		else:
			parent = frappe.get_doc(
				{
					"doctype": "Cost Center",
					"cost_center_name": "Parent Group CC",
					"company": "_Test Company",
					"is_group": 1,
					"parent_cost_center": "_Test Company - _TC",
				}
			).insert()

		# Ensure child exists under parent
		if not frappe.db.exists("Cost Center", child_name):
			frappe.get_doc(
				{
					"doctype": "Cost Center",
					"cost_center_name": "Child of Group CC",
					"company": "_Test Company",
					"is_group": 0,
					"parent_cost_center": parent.name,
				}
			).insert()

		# Reload parent to ensure child is linked
		parent.reload()

		with self.assertRaises(frappe.ValidationError):
			parent.convert_group_to_ledger()

		cost_center_name = "GL Used Group CC - " + self.company_abbr
		account_name = "_Test Account Receivable - " + self.company_abbr
		parent_account = "Accounts Receivable - " + self.company_abbr
		voucher_no = "Test-Voucher"

		# Ensure parent account exists
		if not frappe.db.exists("Account", parent_account):
			frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": "Accounts Receivable",
					"parent_account": "Application of Funds - " + self.company_abbr,
					"account_type": "Receivable",
					"is_group": 1,
					"company": self.company,
				}
			).insert()

		# Ensure child account exists
		if not frappe.db.exists("Account", account_name):
			frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": "_Test Account Receivable",
					"parent_account": parent_account,
					"account_type": "Receivable",
					"is_group": 0,
					"company": self.company,
				}
			).insert()

		# Ensure customer exists
		if not frappe.db.exists("Customer", "_Test Customer"):
			frappe.get_doc(
				{
					"doctype": "Customer",
					"customer_name": "_Test Customer",
					"customer_group": "Commercial",
					"territory": "_Test Territory",
				}
			).insert()

		# Ensure cost center exists
		if frappe.db.exists("Cost Center", cost_center_name):
			cc = frappe.get_doc("Cost Center", cost_center_name)
			if cc.is_group:
				cc.is_group = 0
				cc.save()
		else:
			cc = frappe.get_doc(
				{
					"doctype": "Cost Center",
					"cost_center_name": "GL Used Group CC",
					"company": self.company,
					"is_group": 0,  # Set as ledger initially
					"parent_cost_center": self.root_cost_center,
				}
			).insert()

		# Insert Journal Entry
		if not frappe.db.exists("Journal Entry", voucher_no):
			je = frappe.get_doc(
				{
					"doctype": "Journal Entry",
					"voucher_type": "Journal Entry",
					"posting_date": frappe.utils.nowdate(),
					"company": self.company,
					"accounts": [
						{
							"account": account_name,
							"debit_in_account_currency": 100,
							"party_type": "Customer",
							"party": "_Test Customer",
							"cost_center": cc.name,
						},
						{
							"account": account_name,
							"credit_in_account_currency": 100,
							"party_type": "Customer",
							"party": "_Test Customer",
							"cost_center": cc.name,
						},
					],
				}
			)
			je.insert()
			je.submit()

		# This should fail because GL entries now exist for the cost center
		with self.assertRaises(frappe.ValidationError):
			cc.convert_group_to_ledger()

	def test_convert_ledger_to_group_TC_ACC_279(self):
		main_cost_center_name = "Ledger CC Allocated - " + self.company_abbr
		target_cost_center_name = "Target CC - " + self.company_abbr

		# Ensure main ledger cost center exists
		if not frappe.db.exists("Cost Center", main_cost_center_name):
			main_cc = frappe.get_doc(
				{
					"doctype": "Cost Center",
					"cost_center_name": "Ledger CC Allocated",
					"company": self.company,
					"is_group": 0,
					"parent_cost_center": self.root_cost_center,
				}
			).insert()
		else:
			main_cc = frappe.get_doc("Cost Center", main_cost_center_name)

		# Ensure another cost center exists to allocate to
		if not frappe.db.exists("Cost Center", target_cost_center_name):
			target_cc = frappe.get_doc(
				{
					"doctype": "Cost Center",
					"cost_center_name": "Target CC",
					"company": self.company,
					"is_group": 0,
					"parent_cost_center": self.root_cost_center,
				}
			).insert()
		else:
			target_cc = frappe.get_doc("Cost Center", target_cost_center_name)

		# Create Cost Center Allocation from main_cc to target_cc
		if not frappe.db.exists("Cost Center Allocation", {"main_cost_center": main_cc.name, "docstatus": 1}):
			frappe.get_doc(
				{
					"doctype": "Cost Center Allocation",
					"company": self.company,
					"main_cost_center": main_cc.name,
					"valid_from": frappe.utils.nowdate(),
					"allocation_percentages": [{"cost_center": target_cc.name, "percentage": 100}],
				}
			).insert().submit()

		# Attempt conversion — must fail
		with self.assertRaises(frappe.ValidationError) as cm:
			main_cc.convert_ledger_to_group()

		self.assertIn("Allocation records", str(cm.exception))

	def test_before_after_rename_TC_ACC_280(self):
		unique_suffix = frappe.generate_hash(length=6)
		original_base = f"998 - Rename Test {unique_suffix}"
		renamed_base = f"999 - Renamed {unique_suffix}"

		original_name = original_base + " - " + self.company_abbr
		new_name = renamed_base + " - " + self.company_abbr

		# Clean up if either already exists
		for name in [original_name, new_name]:
			if frappe.db.exists("Cost Center", name):
				frappe.delete_doc("Cost Center", name, force=1)

		# Create original cost center
		cc = frappe.get_doc(
			{
				"doctype": "Cost Center",
				"cost_center_name": f"Rename Test {unique_suffix}",
				"cost_center_number": "998",
				"company": self.company,
				"is_group": 0,
				"parent_cost_center": self.root_cost_center,
			}
		).insert()

		old_name = cc.name

		# Simulate rename manually
		cc.before_rename(old_name, renamed_base)

		frappe.db.sql("UPDATE `tabCost Center` SET name = %s WHERE name = %s", (new_name, old_name))

		cc.name = new_name
		cc.after_rename(old_name, new_name)

		# Reload and verify updated values
		updated_cc = frappe.get_doc("Cost Center", new_name)
		self.assertEqual(updated_cc.cost_center_number, "999")
		self.assertEqual(updated_cc.cost_center_name, f"Renamed {unique_suffix}")

	def tearDown(self):
		frappe.db.rollback()

		# Delete children first
		child_names = [
			"Child of Group CC - _TC",
		]
		parent_names = [
			"Parent Group CC - _TC",
			"GL Used Group CC - _TC",
			"Ledger CC Allocated - _TC",
		]

		for name in child_names:
			if frappe.db.exists("Cost Center", name):
				frappe.delete_doc("Cost Center", name, force=1)

		for name in parent_names:
			if frappe.db.exists("Cost Center", name):
				frappe.delete_doc("Cost Center", name, force=1)


def create_cost_center(**args):
	args = frappe._dict(args)
	if args.cost_center_name:
		company = args.company or "_Test Company"
		company_abbr = frappe.db.get_value("Company", company, "abbr")
		cc_name = args.cost_center_name + " - " + company_abbr
		if not frappe.db.exists("Cost Center", cc_name):
			cc = frappe.new_doc("Cost Center")
			cc.company = args.company or "_Test Company"
			cc.cost_center_name = args.cost_center_name
			cc.is_group = args.is_group or 0
			cc.parent_cost_center = args.parent_cost_center or "_Test Company - _TC"
			cc.insert()
