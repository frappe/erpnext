# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from erpnext.accounts.utils import update_cost_center
from erpnext.tests.utils import ERPNextTestSuite


class TestCostCenter(ERPNextTestSuite):
	def test_cost_center_creation_against_child_node(self):
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

	def test_cost_center_save_restrictions(self):
		from erpnext.accounts.doctype.cost_center_allocation.test_cost_center_allocation import (
			create_cost_center_allocation,
		)
		from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry

		create_cost_center(cost_center_name="_Test Save Restrictions")
		cost_center = frappe.get_doc("Cost Center", "_Test Save Restrictions - _TC")
		self.assertEqual(cost_center.convert_ledger_to_group(), 1)
		create_cost_center(cost_center_name="_Test Conversion Child", parent_cost_center=cost_center.name)
		cost_center.is_group = 0
		with self.assertRaisesRegex(frappe.ValidationError, "child nodes"):
			cost_center.save()
		frappe.delete_doc("Cost Center", "_Test Conversion Child - _TC")
		cost_center.reload()
		self.assertEqual(cost_center.convert_group_to_ledger(), 1)
		make_journal_entry("Cash - _TC", "Sales - _TC", 100, cost_center=cost_center.name, submit=True)

		for field, value, message in (
			("company", "_Test Company 1", "Company cannot be changed"),
			("parent_cost_center", "_Test Company 1 - _TC1", "same Company"),
			("is_group", 1, "existing transactions"),
		):
			with self.subTest(field=field):
				cost_center.reload()
				cost_center.set(field, value)
				with self.assertRaisesRegex(frappe.ValidationError, message):
					cost_center.save()

		create_cost_center(cost_center_name="_Test Allocation Main")
		create_cost_center(cost_center_name="_Test Allocation Child")
		main, child = "_Test Allocation Main - _TC", "_Test Allocation Child - _TC"
		create_cost_center_allocation("_Test Company", main, {child: 100})
		for name in (main, child):
			with self.subTest(cost_center=name):
				cost_center = frappe.get_doc("Cost Center", name)
				cost_center.is_group = 1
				with self.assertRaisesRegex(frappe.ValidationError, "Allocation"):
					cost_center.save()

	def test_rename_preserves_numeric_names_and_explicit_numbers(self):
		create_cost_center(cost_center_name="2026 Projects")
		name = "2026 Projects - _TC"
		for number, title in (("", "2027 Projects"), ("100", "2027 Projects"), ("", "2028 - Projects")):
			with self.subTest(number=number, title=title):
				name = update_cost_center(name, title, number, "_Test Company", False)
				cost_center = frappe.get_doc("Cost Center", name)
				self.assertEqual(cost_center.cost_center_name, title)
				self.assertEqual(cost_center.cost_center_number, number)

		name = update_cost_center(name, "Projects", "200", "_Test Company", False)
		name = frappe.rename_doc("Cost Center", name, "2029 Projects", force=True)
		cost_center = frappe.get_doc("Cost Center", name)
		self.assertEqual(cost_center.name, "200 - 2029 Projects - _TC")
		self.assertEqual(cost_center.cost_center_name, "2029 Projects")
		self.assertEqual(cost_center.cost_center_number, "200")

		for number in ("300", "1.1", "4100-01", "A100"):
			with self.subTest(number=number):
				name = update_cost_center(name, "Projects", number, "_Test Company", False)
				name = frappe.rename_doc("Cost Center", name, "Sales - East", force=True)
				cost_center = frappe.get_doc("Cost Center", name)
				self.assertEqual(cost_center.name, f"{number} - Sales - East - _TC")
				self.assertEqual(cost_center.cost_center_name, "Sales - East")
				self.assertEqual(cost_center.cost_center_number, number)

		create_cost_center(cost_center_name="_Test Number Collision")
		update_cost_center(
			"_Test Number Collision - _TC", "_Test Number Collision", "A200", "_Test Company", False
		)
		with self.assertRaisesRegex(frappe.ValidationError, "Number A200 is already used"):
			update_cost_center(name, "Projects", "A200", "_Test Company", False)


def create_cost_center(**args):
	args = frappe._dict(args)
	if args.cost_center_name:
		company = args.company or "_Test Company"
		company_abbr = frappe.db.get_value("Company", company, "abbr")
		cc_name = args.cost_center_name + " - " + company_abbr
		if not frappe.db.exists("Cost Center", cc_name):
			cc = frappe.new_doc("Cost Center")
			cc.company = company
			cc.cost_center_name = args.cost_center_name
			cc.is_group = args.is_group or 0
			cc.parent_cost_center = args.parent_cost_center or frappe.db.get_value(
				"Cost Center", {"company": company, "is_group": 1, "parent_cost_center": ["is", "not set"]}
			)
			cc.insert()
