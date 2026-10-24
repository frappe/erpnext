# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import unittest
from unittest.mock import patch

import frappe

test_records = frappe.get_test_records("Cost Center")


class TestCostCenter(unittest.TestCase):
	def test_autoname_requires_company_abbreviation(self):
		cost_center = frappe.get_doc(
			{
				"doctype": "Cost Center",
				"cost_center_name": "_Test Abbreviation",
				"company": "_Test Missing Abbreviation Company",
			}
		)
		self.assertFalse(frappe.db.exists("Company", cost_center.company))
		with self.assertRaisesRegex(
			frappe.ValidationError,
			"Company _Test Missing Abbreviation Company does not exist or has no abbreviation",
		):
			cost_center.autoname()

		cost_center.company = "_Test Company"
		with patch("frappe.get_cached_value", return_value=""):
			with self.assertRaisesRegex(
				frappe.ValidationError, "Company _Test Company does not exist or has no abbreviation"
			):
				cost_center.autoname()

		for number, name in (("", "_Test Abbreviation - _TC"), ("100", "100 - _Test Abbreviation - _TC")):
			with self.subTest(number=number):
				cost_center.cost_center_number = number
				cost_center.autoname()
				self.assertEqual(cost_center.name, name)

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
