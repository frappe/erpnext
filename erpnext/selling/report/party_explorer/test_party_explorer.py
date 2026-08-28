# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.selling.report.party_explorer.party_explorer import execute
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


def create_customer(name, customer_group, territory=None, customer_type="Individual"):
	if frappe.db.exists("Customer", name):
		return frappe.get_doc("Customer", name)

	doc = frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": name,
			"customer_group": customer_group,
			"territory": territory or "All Territories",
			"customer_type": customer_type,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc


def create_supplier_group(name, parent_supplier_group, is_group):
	if frappe.db.exists("Supplier Group", name):
		return frappe.get_doc("Supplier Group", name)

	doc = frappe.get_doc(
		{
			"doctype": "Supplier Group",
			"supplier_group_name": name,
			"parent_supplier_group": parent_supplier_group,
			"is_group": is_group,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc


def create_supplier(name, supplier_group, supplier_type="Individual"):
	if frappe.db.exists("Supplier", name):
		return frappe.get_doc("Supplier", name)

	doc = frappe.get_doc(
		{
			"doctype": "Supplier",
			"supplier_name": name,
			"supplier_group": supplier_group,
			"supplier_type": supplier_type,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc


class TestPartyExplorer(ERPNextTestSuite):
	def setUp(self):
		# Customer side
		#   root
		#     |- child (org node, no direct customers)
		#     |    |- grandchild (leaf) -> leaf_customer
		#     |- root_leaf (leaf) -> root_customer
		self.customer_root = create_customer_group("_Test Party Explorer Cust Root", "All Customer Groups", is_group=1)
		self.customer_child = create_customer_group(
			"_Test Party Explorer Cust Child", self.customer_root.name, is_group=1
		)
		self.customer_grandchild = create_customer_group(
			"_Test Party Explorer Cust Grandchild", self.customer_child.name, is_group=0
		)
		self.customer_root_leaf = create_customer_group(
			"_Test Party Explorer Cust Root Leaf", self.customer_root.name, is_group=0
		)
		self.root_customer = create_customer(
			"_Test Party Explorer Customer Root", self.customer_root_leaf.name, customer_type="Company"
		)
		self.leaf_customer = create_customer("_Test Party Explorer Customer Leaf", self.customer_grandchild.name)

		# Supplier side (simple two-level tree, same shape principle)
		self.supplier_root = create_supplier_group("_Test Party Explorer Supp Root", "All Supplier Groups", is_group=1)
		self.supplier_leaf_group = create_supplier_group(
			"_Test Party Explorer Supp Leaf Group", self.supplier_root.name, is_group=0
		)
		self.supplier = create_supplier(
			"_Test Party Explorer Supplier", self.supplier_leaf_group.name, supplier_type="Company"
		)

	def tearDown(self):
		frappe.delete_doc("Customer", self.root_customer.name, force=True)
		frappe.delete_doc("Customer", self.leaf_customer.name, force=True)
		frappe.delete_doc("Customer Group", self.customer_grandchild.name, force=True)
		frappe.delete_doc("Customer Group", self.customer_root_leaf.name, force=True)
		frappe.delete_doc("Customer Group", self.customer_child.name, force=True)
		frappe.delete_doc("Customer Group", self.customer_root.name, force=True)

		frappe.delete_doc("Supplier", self.supplier.name, force=True)
		frappe.delete_doc("Supplier Group", self.supplier_leaf_group.name, force=True)
		frappe.delete_doc("Supplier Group", self.supplier_root.name, force=True)

	def run_report(self, party_type, customer_group=None, supplier_group=None):
		filters = frappe._dict(
			{"party_type": party_type, "customer_group": customer_group, "supplier_group": supplier_group}
		)
		return execute(filters)[1]

	def rows_by_name(self, data):
		return {row["name"]: row for row in data}

	def test_customer_hierarchy_and_columns(self):
		data = self.run_report("Customer", customer_group=self.customer_root.name)
		rows = self.rows_by_name(data)

		self.assertIn(self.customer_root.name, rows)
		self.assertIn(self.customer_child.name, rows)
		self.assertIn(self.customer_grandchild.name, rows)
		self.assertIn(self.root_customer.name, rows)
		self.assertIn(self.leaf_customer.name, rows)

		self.assertEqual(rows[self.customer_root.name]["entity_type"], "Customer Group")
		self.assertEqual(rows[self.customer_root.name]["indent"], 0)
		self.assertEqual(rows[self.customer_child.name]["indent"], 1)
		self.assertEqual(rows[self.customer_grandchild.name]["indent"], 2)

		self.assertEqual(rows[self.root_customer.name]["entity_type"], "Customer")
		self.assertEqual(rows[self.root_customer.name]["indent"], 2)
		self.assertEqual(rows[self.root_customer.name]["customer_type"], "Company")
		self.assertEqual(rows[self.leaf_customer.name]["indent"], 3)

	def test_supplier_hierarchy_and_columns(self):
		data = self.run_report("Supplier", supplier_group=self.supplier_root.name)
		rows = self.rows_by_name(data)

		self.assertIn(self.supplier_root.name, rows)
		self.assertIn(self.supplier_leaf_group.name, rows)
		self.assertIn(self.supplier.name, rows)

		self.assertEqual(rows[self.supplier_root.name]["entity_type"], "Supplier Group")
		self.assertEqual(rows[self.supplier_leaf_group.name]["indent"], 1)

		self.assertEqual(rows[self.supplier.name]["entity_type"], "Supplier")
		self.assertEqual(rows[self.supplier.name]["indent"], 2)
		self.assertEqual(rows[self.supplier.name]["supplier_type"], "Company")
		self.assertIn("blocked", rows[self.supplier.name])
		self.assertIn("is_frozen", rows[self.supplier.name])

	def test_blank_filter_starts_from_the_true_top_level_group(self):
		data = self.run_report("Customer")
		rows = self.rows_by_name(data)

		self.assertIn("All Customer Groups", rows)
		self.assertEqual(rows["All Customer Groups"]["indent"], 0)
		self.assertIn(self.customer_root.name, rows)
		self.assertEqual(rows[self.customer_root.name]["indent"], 1)

	def test_defaults_to_customer_when_party_type_missing(self):
		data = execute(frappe._dict({"customer_group": self.customer_root.name}))[1]
		rows = self.rows_by_name(data)
		self.assertIn(self.customer_root.name, rows)
