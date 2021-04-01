# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals
import unittest
import frappe

test_records = frappe.get_test_records('Cost Center')

class TestCostCenter(unittest.TestCase):
	def test_cost_center_creation_against_child_node(self):

		if not frappe.db.get_value('Cost Center', {'name': '_Test Cost Center 2 - _TC'}):
			frappe.get_doc(test_records[1]).insert()

		cost_center = frappe.get_doc({
			'doctype': 'Cost Center',
			'cost_center_name': '_Test Cost Center 3',
			'parent_cost_center': '_Test Cost Center 2 - _TC',
			'is_group': 0,
			'company': '_Test Company'
		})

		self.assertRaises(frappe.ValidationError, cost_center.save)

	def test_validate_distributed_cost_center(self):

		if not frappe.db.get_value('Cost Center', {'name': '_Test Cost Center - _TC'}):
			frappe.get_doc(test_records[0]).insert()

		if not frappe.db.get_value('Cost Center', {'name': '_Test Cost Center 2 - _TC'}):
			frappe.get_doc(test_records[1]).insert()

		invalid_distributed_cost_center = frappe.get_doc({
			"company": "_Test Company",
			"cost_center_name": "_Test Distributed Cost Center",
			"doctype": "Cost Center",
			"is_group": 0,
			"parent_cost_center": "_Test Company - _TC",
			"enable_distributed_cost_center": 1,
			"distributed_cost_center": [{
				"cost_center": "_Test Cost Center - _TC",
				"percentage_allocation": 40
				}, {
				"cost_center": "_Test Cost Center 2 - _TC",
				"percentage_allocation": 50
				}
			]
		})

		self.assertRaises(frappe.ValidationError, invalid_distributed_cost_center.save)

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



