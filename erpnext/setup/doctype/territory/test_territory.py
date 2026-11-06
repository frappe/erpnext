# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.nestedset import get_root_of

test_records = frappe.get_test_records("Territory")

test_ignore = ["Item Group"]


class TestTerritory(FrappeTestCase):
	def test_root_tree_records_can_be_saved(self):
		for doctype in ("Territory", "Customer Group", "Supplier Group", "Sales Person"):
			with self.subTest(doctype=doctype):
				root = frappe.get_doc(doctype, get_root_of(doctype))
				root.save()
				self.assertFalse(root.get(root.nsm_parent_field))
