# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils.nestedset import get_root_of

from erpnext.tests.utils import ERPNextTestSuite


class TestTerritory(ERPNextTestSuite):
	def test_root_is_not_set_as_its_own_parent(self):
		root = frappe.get_doc("Territory", get_root_of("Territory"))
		root.save()

		self.assertFalse(root.parent_territory)

	def test_territory_without_parent_is_placed_under_root(self):
		territory = frappe.get_doc({"doctype": "Territory", "territory_name": "Western Europe"}).insert()

		self.assertEqual(territory.parent_territory, get_root_of("Territory"))
