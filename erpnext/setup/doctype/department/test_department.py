# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
import unittest

import frappe
from frappe.tests import IntegrationTestCase

IGNORE_TEST_RECORD_DEPENDENCIES = ["Leave Block List"]


class TestDepartment(IntegrationTestCase):
	def test_remove_department_data(self):
		doc = create_department("Test Department")
		frappe.delete_doc("Department", doc.name)


def create_department(department_name, parent_department=None):
	doc = frappe.get_doc(
		{
			"doctype": "Department",
			"is_group": 0,
			"parent_department": parent_department,
			"department_name": department_name,
			"company": frappe.defaults.get_defaults().company,
		}
	).insert()

	return doc
