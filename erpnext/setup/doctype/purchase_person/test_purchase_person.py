# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestPurchasePerson(ERPNextTestSuite):
	def setUp(self):
		frappe.db.delete("Purchase Person", {"purchase_person_name": "_Test Purchase Person"})
		frappe.db.delete("Purchase Person", {"purchase_person_name": "_Test Purchase Person Group"})

	def tearDown(self):
		frappe.db.delete("Purchase Person", {"purchase_person_name": "_Test Purchase Person"})
		frappe.db.delete("Purchase Person", {"purchase_person_name": "_Test Purchase Person Group"})

	def test_create_purchase_person(self):
		purchase_person = frappe.get_doc(
			{
				"doctype": "Purchase Person",
				"purchase_person_name": "_Test Purchase Person",
				"commission_rate": "10",
				"enabled": 1,
			}
		)
		purchase_person.insert(ignore_permissions=True)

		self.assertEqual(purchase_person.purchase_person_name, "_Test Purchase Person")
		self.assertTrue(purchase_person.enabled)

	def test_create_purchase_person_group(self):
		group = frappe.get_doc(
			{
				"doctype": "Purchase Person",
				"purchase_person_name": "_Test Purchase Person Group",
				"is_group": 1,
				"enabled": 1,
			}
		)
		group.insert(ignore_permissions=True)

		self.assertTrue(group.is_group)
		self.assertTrue(group.lft)
		self.assertTrue(group.rgt)

	def test_duplicate_employee_raises_error(self):
		employee = frappe.db.get_value("Employee", {"status": "Active"}, "name")
		if not employee:
			return

		pp1 = frappe.get_doc(
			{
				"doctype": "Purchase Person",
				"purchase_person_name": "_Test Purchase Person",
				"employee": employee,
				"enabled": 1,
			}
		)
		pp1.insert(ignore_permissions=True)

		pp2 = frappe.get_doc(
			{
				"doctype": "Purchase Person",
				"purchase_person_name": "_Test Purchase Person 2",
				"employee": employee,
				"enabled": 1,
			}
		)
		self.assertRaises(frappe.ValidationError, pp2.insert)

		frappe.db.delete("Purchase Person", {"purchase_person_name": "_Test Purchase Person 2"})
