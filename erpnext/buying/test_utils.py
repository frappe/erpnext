# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import json

import frappe
import frappe.permissions

from erpnext.buying.utils import get_linked_material_requests
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.material_request.test_material_request import make_material_request
from erpnext.tests.utils import ERPNextTestSuite


def create_user_with_roles(email, *roles):
	if frappe.db.exists("User", email):
		user = frappe.get_doc("User", email)
	else:
		user = frappe.new_doc("User")
		user.email = email
		user.first_name = email.split("@", 1)[0]
		user.insert(ignore_permissions=True)

	user.set("roles", [])
	for role in roles:
		user.append("roles", {"role": role})
	user.save(ignore_permissions=True)

	# a user left without roles is downgraded to a Website User on save
	frappe.db.set_value("User", email, "user_type", "System User")

	return user


class TestGetLinkedMaterialRequests(ERPNextTestSuite):
	def setUp(self):
		self.material_request = make_material_request(item_code="_Test Item")

	def test_permitted_role_can_fetch_linked_material_requests(self):
		create_user_with_roles("test_buying_purchase_user@example.com", "Purchase User")

		with self.set_user("test_buying_purchase_user@example.com"):
			rows = get_linked_material_requests(["_Test Item"])

		self.assertIn(self.material_request.name, {row.mr_name for row in rows})

	def test_populated_result_is_a_flat_list_of_rows(self):
		"""Both callers iterate the response directly, so it has to stay a flat list of rows
		rather than a list of lists."""
		create_user_with_roles("test_buying_purchase_user@example.com", "Purchase User")

		with self.set_user("test_buying_purchase_user@example.com"):
			rows = get_linked_material_requests(["_Test Item"])

		self.assertIsInstance(rows, list)
		self.assertTrue(rows)
		for row in rows:
			self.assertNotIsInstance(row, list | tuple)
			self.assertIsInstance(row, dict)
			for fieldname in ("mr_name", "mr_item", "item_code", "qty"):
				self.assertIn(fieldname, row)

	def test_empty_result_is_a_flat_empty_list(self):
		item_without_request = make_item("_Test Item Without Material Request").name
		create_user_with_roles("test_buying_purchase_user@example.com", "Purchase User")

		with self.set_user("test_buying_purchase_user@example.com"):
			rows = get_linked_material_requests([item_without_request])

		self.assertEqual(rows, [])

	def test_a_single_item_code_is_treated_as_one_code(self):
		"""A lone code must be read as one item code, not iterated character by character."""
		create_user_with_roles("test_buying_purchase_user@example.com", "Purchase User")

		with self.set_user("test_buying_purchase_user@example.com"):
			rows = get_linked_material_requests(json.dumps("_Test Item"))

		self.assertIn(self.material_request.name, {row.mr_name for row in rows})

	def test_items_that_are_not_item_codes_are_rejected(self):
		"""Anything that is not a `str` or a `list` is already refused by the type annotation,
		so these are the malformed inputs that reach the method."""
		create_user_with_roles("test_buying_purchase_user@example.com", "Purchase User")
		bad_inputs = (
			"not json at all",
			[{"item_code": "_Test Item"}],
			[["_Test Item"]],
			[None],
		)

		with self.set_user("test_buying_purchase_user@example.com"):
			for bad_items in bad_inputs:
				with self.subTest(items=bad_items):
					self.assertRaises(frappe.ValidationError, get_linked_material_requests, bad_items)

	def test_manufacturing_manager_can_fetch_linked_material_requests(self):
		"""Manufacturing Manager holds write on Supplier Quotation and Request for Quotation,
		both of which call this method, so it must hold Material Request read as well."""
		create_user_with_roles("test_buying_mfg_manager@example.com", "Manufacturing Manager")

		with self.set_user("test_buying_mfg_manager@example.com"):
			rows = get_linked_material_requests(["_Test Item"])

		self.assertIn(self.material_request.name, {row.mr_name for row in rows})

	def test_unpermitted_role_cannot_fetch_linked_material_requests(self):
		create_user_with_roles("test_buying_sales_user@example.com", "Sales User")

		with self.set_user("test_buying_sales_user@example.com"):
			self.assertRaises(frappe.PermissionError, get_linked_material_requests, ["_Test Item"])

	def test_role_with_only_select_permission_cannot_fetch_linked_material_requests(self):
		"""Material Request grants Delivery and Maintenance roles `select` and nothing else.
		`select` is enough to list names, so the permitted set must be resolved through a
		filter on the child table, which requires `read`."""
		create_user_with_roles("test_buying_delivery_user@example.com", "Delivery User")

		with self.set_user("test_buying_delivery_user@example.com"):
			self.assertRaises(frappe.PermissionError, get_linked_material_requests, ["_Test Item"])

	def test_results_are_restricted_by_user_permissions(self):
		other_company_request = make_material_request(
			item_code="_Test Item",
			company="_Test Company 1",
			warehouse="_Test Warehouse 2 - _TC1",
			cost_center="Main - _TC1",
		)
		user = create_user_with_roles("test_buying_restricted_user@example.com", "Purchase User")
		frappe.permissions.add_user_permission("Company", "_Test Company", user.name)

		try:
			with self.set_user(user.name):
				mr_names = {row.mr_name for row in get_linked_material_requests(["_Test Item"])}
		finally:
			frappe.permissions.remove_user_permission("Company", "_Test Company", user.name)

		self.assertIn(self.material_request.name, mr_names)
		self.assertNotIn(other_company_request.name, mr_names)
