# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.selling.report.customer_group_explorer.customer_group_explorer import build_tree_rows, execute
from erpnext.tests.utils import ERPNextTestSuite


def create_customer_group(name, parent_customer_group, is_group):
	if frappe.db.exists("Customer Group", name):
		return frappe.get_doc("Customer Group", name)

	doc = frappe.get_doc(
		{
			"doctype": "Customer Group",
			"customer_group_name": name,
			"parent_customer_group": parent_customer_group,
			"is_group": is_group,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc


def create_customer(name, customer_group, territory=None):
	if frappe.db.exists("Customer", name):
		return frappe.get_doc("Customer", name)

	doc = frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": name,
			"customer_group": customer_group,
			"territory": territory or "All Territories",
			"customer_type": "Individual",
		}
	)
	doc.insert(ignore_permissions=True)
	return doc


class TestCustomerGroupExplorer(ERPNextTestSuite):
	def setUp(self):
		# root
		#   |- child (org node, no direct customers)
		#   |    |- grandchild (leaf) -> leaf_customer
		#   |- root_leaf (leaf) -> root_customer
		#
		# Customers can only be linked to a leaf (is_group=0) Customer Group, so only
		# `grandchild` and `root_leaf` hold customers directly, matching how real data
		# is organized (organizational groups stay empty; only leaves hold customers).
		self.root = create_customer_group("_Test Explorer Group Root", "All Customer Groups", is_group=1)
		self.child = create_customer_group("_Test Explorer Group Child", self.root.name, is_group=1)
		self.grandchild = create_customer_group("_Test Explorer Group Grandchild", self.child.name, is_group=0)
		self.root_leaf = create_customer_group("_Test Explorer Group Root Leaf", self.root.name, is_group=0)

		self.root_customer = create_customer("_Test Explorer Customer Root", self.root_leaf.name)
		self.leaf_customer = create_customer("_Test Explorer Customer Leaf", self.grandchild.name)

	def tearDown(self):
		frappe.delete_doc("Customer", self.root_customer.name, force=True)
		frappe.delete_doc("Customer", self.leaf_customer.name, force=True)
		frappe.delete_doc("Customer Group", self.grandchild.name, force=True)
		frappe.delete_doc("Customer Group", self.root_leaf.name, force=True)
		frappe.delete_doc("Customer Group", self.child.name, force=True)
		frappe.delete_doc("Customer Group", self.root.name, force=True)

	def run_report(self, customer_group=None):
		filters = frappe._dict({"customer_group": customer_group})
		return execute(filters)[1]

	def rows_by_name(self, data):
		return {row["name"]: row for row in data}

	def test_explores_full_hierarchy_from_selected_root(self):
		data = self.run_report(self.root.name)
		rows = self.rows_by_name(data)

		self.assertIn(self.root.name, rows)
		self.assertIn(self.child.name, rows)
		self.assertIn(self.grandchild.name, rows)
		self.assertIn(self.root_leaf.name, rows)
		self.assertIn(self.root_customer.name, rows)
		self.assertIn(self.leaf_customer.name, rows)

		self.assertEqual(rows[self.root.name]["entity_type"], "Customer Group")
		self.assertEqual(rows[self.root.name]["indent"], 0)

		self.assertEqual(rows[self.child.name]["indent"], 1)
		self.assertEqual(rows[self.grandchild.name]["indent"], 2)
		self.assertEqual(rows[self.root_leaf.name]["indent"], 1)

	def test_customer_sits_one_level_below_its_own_group(self):
		data = self.run_report(self.root.name)
		rows = self.rows_by_name(data)

		# A customer linked to the root's direct leaf group is one level below that leaf.
		self.assertEqual(rows[self.root_customer.name]["entity_type"], "Customer")
		self.assertEqual(rows[self.root_customer.name]["indent"], 2)
		self.assertEqual(rows[self.root_customer.name]["parent_customer_group"], self.root_leaf.name)

		# A customer linked to the grandchild group sits one level below it, three deep overall.
		self.assertEqual(rows[self.leaf_customer.name]["indent"], 3)
		self.assertEqual(rows[self.leaf_customer.name]["parent_customer_group"], self.grandchild.name)

	def test_blank_filter_starts_from_the_true_top_level_group(self):
		# self.root is parented under "All Customer Groups" (the actual top-level node),
		# so a blank filter shows that real root at indent 0 and self.root one level deeper.
		data = self.run_report()
		rows = self.rows_by_name(data)

		self.assertIn("All Customer Groups", rows)
		self.assertEqual(rows["All Customer Groups"]["indent"], 0)
		self.assertIn(self.root.name, rows)
		self.assertEqual(rows[self.root.name]["indent"], 1)

	def test_build_tree_rows_walks_groups_and_customers(self):
		children_map = {
			"": [frappe._dict(name="root", parent_customer_group=None)],
			"root": [frappe._dict(name="child", parent_customer_group="root")],
		}
		customers_by_group = {
			"root": [
				frappe._dict(name="cust-1", customer_name="Cust 1", customer_group="root", territory=None, disabled=0)
			],
			"child": [
				frappe._dict(
					name="cust-2", customer_name="Cust 2", customer_group="child", territory=None, disabled=0
				)
			],
		}

		data = []
		build_tree_rows(children_map[""][0], children_map, customers_by_group, data, indent=0)

		rows = self.rows_by_name(data)
		self.assertEqual(rows["root"]["indent"], 0)
		self.assertEqual(rows["child"]["indent"], 1)
		# root's own customer is nested directly below it...
		self.assertEqual(rows["cust-1"]["indent"], 1)
		# ...while child's customer is nested below child, one level deeper again.
		self.assertEqual(rows["cust-2"]["indent"], 2)
