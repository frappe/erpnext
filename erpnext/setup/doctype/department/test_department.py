# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils.nestedset import get_root_of

from erpnext.tests.utils import ERPNextTestSuite


class TestDepartment(ERPNextTestSuite):
	def test_remove_department_data(self):
		doc = create_department("Test Department", company="_Test Company")
		frappe.delete_doc("Department", doc.name)

	def test_parent_must_be_group_in_same_company(self):
		def new_department(name, company, parent, is_group=0):
			return frappe.get_doc(
				{
					"doctype": "Department",
					"department_name": name,
					"company": company,
					"parent_department": parent,
					"is_group": is_group,
				}
			)

		root = get_root_of("Department")
		group = new_department("Parent Group", "_Test Company", root, 1).insert()
		leaf = new_department("Parent Leaf", "_Test Company", group.name).insert()
		new_department("Valid Child", "_Test Company", group.name).insert()

		with self.assertRaisesRegex(frappe.ValidationError, "same company"):
			new_department("Cross Company Child", "_Test Company 1", group.name).insert()
		with self.assertRaisesRegex(frappe.ValidationError, "must be a group"):
			new_department("Child Under Leaf", "_Test Company", leaf.name).insert()


def create_department(department_name, parent_department=None, company=None):
	doc = frappe.get_doc(
		{
			"doctype": "Department",
			"is_group": 0,
			"parent_department": parent_department,
			"department_name": department_name,
			"company": frappe.defaults.get_defaults().company or company,
		}
	).insert()

	return doc
