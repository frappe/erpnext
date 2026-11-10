# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.desk.search import search_link

from erpnext.accounts.custom.address import address_query
from erpnext.setup.install import (
	create_address_and_contact_custom_fields,
	setup_company_address_permissions,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestERPNextAddress(ERPNextTestSuite):
	def setUp(self):
		super().setUp()
		# inside the test transaction, so the per-test rollback removes the permission rows again
		create_address_and_contact_custom_fields()
		setup_company_address_permissions()
		frappe.clear_cache(doctype="Address")
		self.addCleanup(frappe.set_user, "Administrator")

	def make_address(self, title, company_link=False, **values):
		doc = frappe.get_doc(
			{
				"doctype": "Address",
				"address_title": title,
				"address_type": "Billing",
				"address_line1": "1 Review Street",
				"city": "Chennai",
				"country": "India",
				"links": [{"link_doctype": "Company", "link_name": "_Test Company"}] if company_link else [],
				**values,
			}
		)
		return doc.insert()

	def test_sales_user_cannot_mark_company_address(self):
		frappe.set_user(make_user("address-sales-user@example.com", "Sales User"))

		address = self.make_address("_Test Sales User Address", is_your_company_address=1)
		self.assertEqual(address.is_your_company_address, 0)

		self.assertRaises(
			frappe.PermissionError, self.make_address, "_Test Sales User Company Address", company_link=True
		)

	def test_accounts_manager_can_mark_company_address(self):
		frappe.set_user(make_user("address-accounts-manager@example.com", "Accounts Manager"))

		address = self.make_address("_Test Accounts Manager Company Address", company_link=True)
		self.assertEqual(address.is_your_company_address, 1)

	def test_sales_user_can_edit_existing_company_address(self):
		address = self.make_address("_Test Existing Company Address", company_link=True)
		self.assertEqual(address.is_your_company_address, 1)

		frappe.set_user(make_user("address-sales-user@example.com", "Sales User"))
		address = frappe.get_doc("Address", address.name)
		address.address_line1 = "2 Review Street"
		address.save()
		self.assertEqual(address.is_your_company_address, 1)

	def test_sales_user_cannot_change_company_links_of_company_address(self):
		address = self.make_address("_Test Linked Company Address", company_link=True)

		frappe.set_user(make_user("address-sales-user@example.com", "Sales User"))

		# the flag is already set, so only the stored Company links may stay
		address = frappe.get_doc("Address", address.name)
		address.append("links", {"link_doctype": "Company", "link_name": "_Test Company 1"})
		self.assertRaises(frappe.PermissionError, address.save)

		address = frappe.get_doc("Address", address.name)
		address.links[0].link_name = "_Test Company 1"
		self.assertRaises(frappe.PermissionError, address.save)

		address = frappe.get_doc("Address", address.name)
		address.append("links", {"link_doctype": "Customer", "link_name": "_Test Customer"})
		address.save()
		self.assertEqual(address.is_your_company_address, 1)

	def test_sales_user_cannot_remove_company_link_of_company_address(self):
		address = self.make_address("_Test Shared Company Address", company_link=True)
		address.append("links", {"link_doctype": "Company", "link_name": "_Test Company 1"})
		address.save()

		frappe.set_user(make_user("address-sales-user@example.com", "Sales User"))

		address = frappe.get_doc("Address", address.name)
		address.links = [row for row in address.links if row.link_name != "_Test Company 1"]
		self.assertRaises(frappe.PermissionError, address.save)

		address = frappe.get_doc("Address", address.name)
		address.links = []
		self.assertRaises(frappe.ValidationError, address.save)

	def test_address_lookup_preserves_filters_and_permissions(self):
		company_address = self.make_address("_Test Address Lookup Company", company_link=True)
		other_company_address = self.make_address(
			"_Test Address Lookup Other Company",
			links=[{"link_doctype": "Company", "link_name": "_Test Company 1"}],
		)
		customer_address = self.make_address(
			"_Test Address Lookup Customer",
			links=[{"link_doctype": "Customer", "link_name": "_Test Customer"}],
		)
		self.make_address("_Test Address Lookup Disabled", company_link=True, disabled=1)
		user = make_user("address-lookup-user@example.com", "Sales User")
		frappe.get_doc("User", user).add_roles("Stock Manager", "Delivery Manager")

		with self.set_user(user):
			self.assertNotIn(1, company_address.get_permlevel_access("read"))
			for filters, expected in (
				({"is_your_company_address": 1}, {company_address.name, other_company_address.name}),
				({"is_your_company_address": 0}, {customer_address.name}),
				(
					{"is_your_company_address": 1, "link_doctype": "Company", "link_name": "_Test Company"},
					{company_address.name},
				),
				(
					{"is_your_company_address": 0, "link_doctype": "Customer", "link_name": "_Test Customer"},
					{customer_address.name},
				),
				({"is_your_company_address": 1, "name": customer_address.name}, set()),
				({"is_your_company_address": 1, "country": "Canada"}, set()),
			):
				with self.subTest(filters=filters):
					rows = search_link(
						"Address",
						"_Test Address Lookup",
						query="erpnext.accounts.custom.address.address_query",
						filters=filters,
					)
					self.assertEqual({row["value"] for row in rows}, expected)

			filters = {"is_your_company_address": 1}
			rows = address_query("Address", "_Test Address Lookup", "name", 0, 2, filters)
			self.assertEqual(
				address_query("Address", "_Test Address Lookup", "name", 1, 1, filters), rows[1:]
			)
			self.assertEqual(filters, {"is_your_company_address": 1})

		frappe.get_doc(
			doctype="User Permission", user=user, allow="Address", for_value=company_address.name
		).insert()
		with self.set_user(user):
			rows = address_query("Address", "_Test Address Lookup", "name", 0, 10, filters)
			self.assertEqual([row[0] for row in rows], [company_address.name])
		with self.set_user("Guest"):
			self.assertRaises(frappe.PermissionError, frappe.is_whitelisted, address_query)


def make_user(email, role):
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": email.split("@")[0],
				"send_welcome_email": 0,
				"roles": [{"role": role}],
			}
		).insert()
	return email
