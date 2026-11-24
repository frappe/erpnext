import unittest
from functools import partial

import frappe
from frappe.core.doctype.user_permission.test_user_permission import create_user
from frappe.core.doctype.user_permission.user_permission import add_user_permissions
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

from erpnext.controllers import queries
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.subcontracting.doctype.subcontracting_order.test_subcontracting_order import (
	make_subcontracted_variant,
)
from erpnext.tests.permission_test_utils import as_user, make_company_fenced_user
from erpnext.tests.utils import ERPNextTestSuite


def add_default_params(func, doctype):
	return partial(func, doctype=doctype, txt="", searchfield="name", start=0, page_len=20, filters=None)


class TestQueries(ERPNextTestSuite):
	def assert_nested_in(self, item, container):
		self.assertIn(item, [vals for tuples in container for vals in tuples])

	def test_employee_query(self):
		query = add_default_params(queries.employee_query, "Employee")

		self.assertGreaterEqual(len(query(txt="_Test Employee")), 3)
		self.assertGreaterEqual(len(query(txt="_Test Employee 1")), 1)

	def test_lead_query(self):
		query = add_default_params(queries.lead_query, "Lead")

		self.assertGreaterEqual(len(query(txt="_Test Lead")), 4)
		self.assertEqual(len(query(txt="_Test Lead 4")), 1)

	def test_item_query(self):
		query = add_default_params(queries.item_query, "Item")

		self.assertGreaterEqual(len(query(txt="_Test Item")), 7)
		self.assertEqual(len(query(txt="_Test Item Home Desktop 100 3")), 1)

		fg_item = "_Test FG Item"
		stock_items = query(txt=fg_item, filters={"is_stock_item": 1})
		self.assert_nested_in("_Test FG Item", stock_items)

		bundled_stock_items = query(txt="_test product bundle item 5", filters={"is_stock_item": 1})
		self.assertEqual(len(bundled_stock_items), 0)

		# empty customer/supplier should be stripped of instead of failure
		query(txt="", filters={"customer": None})
		query(txt="", filters={"customer": ""})
		query(txt="", filters={"supplier": None})
		query(txt="", filters={"supplier": ""})

	def test_item_query_with_percent_in_permitted_company(self):
		company = frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": "_Test 100% Company",
				"abbr": "_T100",
				"default_currency": "INR",
				"country": "India",
			}
		).insert()
		item = make_item(
			properties={
				"is_stock_item": 0,
				"restrict_to_companies": 1,
				"allowed_companies": [{"company": company.name}],
			}
		)
		user = make_company_fenced_user("item-query-percent@example.com", ["Stock User"], company.name)

		with as_user(user):
			items = queries.item_query("Item", item.name, "name", 0, 20, {})

		self.assertIn(item.name, [row[0] for row in items])

	def test_item_manufacturer_query_requires_item_read_permission(self):
		item = make_item("Steel Sheet With Manufacturer", {"is_stock_item": 1})
		if not frappe.db.exists("Manufacturer", "Northwind Steel"):
			frappe.get_doc({"doctype": "Manufacturer", "short_name": "Northwind Steel"}).insert()
		frappe.get_doc(
			{
				"doctype": "Item Manufacturer",
				"item_code": item.name,
				"manufacturer": "Northwind Steel",
				"manufacturer_part_no": "NS-4242",
			}
		).insert()

		query = add_default_params(queries.item_manufacturer_query, "Manufacturer")
		purchase_user = create_user("item_manufacturer_purchase_user@example.com", "Purchase User")
		website_manager = create_user("item_manufacturer_website_manager@example.com", "Website Manager")

		with self.set_user(purchase_user.name):
			self.assertEqual(query(filters={"item_code": item.name}), (("Northwind Steel", "NS-4242"),))

		with self.set_user(website_manager.name), self.assertRaises(frappe.PermissionError):
			query(filters={"item_code": item.name})

	def test_item_manufacturer_query_needs_a_single_item_code(self):
		query = add_default_params(queries.item_manufacturer_query, "Manufacturer")
		purchase_user = create_user("item_manufacturer_purchase_user@example.com", "Purchase User")
		website_manager = create_user("item_manufacturer_website_manager@example.com", "Website Manager")

		for filters in ({}, {"item_code": None}, {"item_code": ""}, {"item_code": ["like", "%"]}):
			for user in (purchase_user.name, website_manager.name):
				with self.subTest(filters=filters, user=user), self.set_user(user):
					self.assertEqual(query(filters=filters), [])

	def test_subcontracted_item_query(self):
		variant, _ = make_subcontracted_variant()
		item_without_bom = make_item(
			"Subcontracted Item Without BOM", {"is_stock_item": 1, "is_sub_contracted_item": 1}
		)
		query = add_default_params(queries.subcontracted_item_query, "Item")

		items = query(txt="Subcontracted", page_len=100)

		self.assert_nested_in(variant.name, items)
		self.assertNotIn(item_without_bom.name, [row[0] for row in items])

	def test_bom_qury(self):
		query = add_default_params(queries.bom, "BOM")

		self.assertGreaterEqual(len(query(txt="_Test Item Home Desktop Manufactured")), 1)

	def test_project_query(self):
		query = add_default_params(queries.get_project_name, "Project")

		self.assertGreaterEqual(len(query(txt="_Test Project")), 1)

	def test_tax_template_query_requires_item_read_permission(self):
		query = add_default_params(queries.get_tax_template, "Item Tax Template")
		item_code = "_Test Item Home Desktop 100"
		sales_user = create_user("tax_template_sales_user@example.com", "Sales User")
		website_manager = create_user("tax_template_website_manager@example.com", "Website Manager")

		with self.set_user(sales_user.name):
			templates = query(filters={"item_code": item_code, "company": "_Test Company"})
			self.assertEqual([row[0] for row in templates], ["_Test Account Excise Duty @ 10 - _TC"])

			with self.assertRaises(frappe.PermissionError):
				query(filters={"item_code": {"name": item_code}, "company": "_Test Company"})

		with self.set_user(website_manager.name), self.assertRaises(frappe.PermissionError):
			query(filters={"item_code": item_code, "company": "_Test Company"})

	def test_tax_template_query_applies_company_user_permission(self):
		query = add_default_params(queries.get_tax_template, "Item Tax Template")
		filters = {"item_code": "_Test Item Home Desktop 100", "company": "_Test Company"}
		user = create_user("tax_template_company_user@example.com", "Sales User")
		unrestricted_user = create_user("tax_template_sales_user@example.com", "Sales User")
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": user.name,
				"allow": "Company",
				"for_value": "_Test Company 1",
			}
		).insert()

		with self.set_user(user.name):
			self.assertFalse(query(filters=filters))

		with self.set_user(unrestricted_user.name):
			self.assertEqual(
				[row[0] for row in query(filters=filters)], ["_Test Account Excise Duty @ 10 - _TC"]
			)

	def test_account_query(self):
		query = add_default_params(queries.get_account_list, "Account")

		debtor_accounts = query(txt="Debtors", filters={"company": "_Test Company"})
		self.assert_nested_in("Debtors - _TC", debtor_accounts)

	def test_income_account_query(self):
		query = add_default_params(queries.get_income_account, "Account")

		self.assertGreaterEqual(len(query(filters={"company": "_Test Company"})), 1)

	def test_income_account_query_requires_account_permission(self):
		query = add_default_params(queries.get_income_account, "Account")
		accounts_user = create_user("income_account_accounts_user@example.com", "Accounts User")
		website_manager = create_user("income_account_website_manager@example.com", "Website Manager")

		restricted_user = create_user("income_account_restricted_user@example.com", "Accounts User")
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": restricted_user.name,
				"allow": "Company",
				"for_value": "_Test Company 1",
			}
		).insert()

		with self.set_user(accounts_user.name):
			self.assert_nested_in("Sales - _TC", query(filters={"company": "_Test Company"}))

		with self.set_user(restricted_user.name):
			self.assertFalse(query(filters={"company": "_Test Company"}))

		with self.set_user(website_manager.name), self.assertRaises(frappe.PermissionError):
			query(filters={"company": "_Test Company"})

	def test_expense_account_query(self):
		query = add_default_params(queries.get_expense_account, "Account")

		self.assertGreaterEqual(len(query(filters={"company": "_Test Company"})), 1)

	def test_expense_account_query_requires_account_permission(self):
		query = add_default_params(queries.get_expense_account, "Account")
		purchase_user = create_user("expense_account_purchase_user@example.com", "Purchase User")
		website_manager = create_user("expense_account_website_manager@example.com", "Website Manager")

		with self.set_user(purchase_user.name):
			self.assert_nested_in("Cost of Goods Sold - _TC", query(filters={"company": "_Test Company"}))

		with self.set_user(website_manager.name), self.assertRaises(frappe.PermissionError):
			query(filters={"company": "_Test Company"})

	def test_warehouse_address_query_requires_warehouse_read_permission(self):
		address = frappe.get_doc(
			{
				"doctype": "Address",
				"address_title": "Riverside Depot",
				"address_type": "Shipping",
				"address_line1": "12 River Road",
				"city": "Pune",
				"country": "India",
				"links": [{"link_doctype": "Warehouse", "link_name": "Stores - _TC"}],
			}
		).insert()

		query = add_default_params(queries.get_warehouse_address, "Address")
		stock_user = create_user("warehouse_address_stock_user@example.com", "Stock User")
		website_manager = create_user("warehouse_address_website_manager@example.com", "Website Manager")

		with self.set_user(stock_user.name):
			self.assertEqual(query(filters={"warehouse": "Stores - _TC"}), [[address.name]])

		with self.set_user(website_manager.name), self.assertRaises(frappe.PermissionError):
			query(filters={"warehouse": "Stores - _TC"})

	def test_warehouse_query(self):
		query = add_default_params(queries.warehouse_query, "Account")

		wh = query(filters=[["Bin", "item_code", "=", "_Test Item"]])
		self.assertGreaterEqual(len(wh), 1)

	def test_warehouse_query_shows_stock_only_with_bin_permission(self):
		query = add_default_params(queries.warehouse_query, "Warehouse")
		stock_user = create_user("warehouse_query_stock_user@example.com", "Stock User")
		website_manager = create_user("warehouse_query_website_manager@example.com", "Website Manager")

		with self.set_user(stock_user.name):
			rows = query(txt="_Test Warehouse - _TC", filters=[])
			self.assertTrue(rows)
			self.assertTrue(all(row[1].startswith("Actual Qty : ") for row in rows))

		with self.set_user(website_manager.name):
			rows = query(txt="_Test Warehouse - _TC", filters=[])
			self.assert_nested_in("_Test Warehouse - _TC", rows)
			self.assertTrue(all(len(row) == 1 for row in rows))

	def test_get_delivery_notes_to_be_billed_skips_fully_returned(self):
		from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_return
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note

		returned_dn = create_delivery_note(qty=2)
		dn_return = make_sales_return(returned_dn.name)
		dn_return.submit()
		# a new doc misses the is_return part of status_updater, so update the original DN explicitly
		frappe.get_doc("Delivery Note", dn_return.name).update_prevdoc_status()
		returned_dn.reload()
		self.assertEqual(returned_dn.status, "Return Issued")

		open_dn = create_delivery_note(qty=2)

		query = add_default_params(queries.get_delivery_notes_to_be_billed, "Delivery Note")
		result = query(filters={"name": ["in", [returned_dn.name, open_dn.name]]})

		self.assert_nested_in(open_dn.name, result)
		self.assertNotIn(returned_dn.name, [row[0] for row in result])

	def test_get_filtered_child_rows_checks_linked_document_permission(self):
		from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

		so = make_sales_order(do_not_submit=True)
		po = create_purchase_order(do_not_save=True)
		po.items[0].sales_order = so.name
		po.insert()

		user = create_user("child_rows_purchase_user@example.com", "Purchase User")
		params = {
			"doctype": "Purchase Order Item",
			"txt": "",
			"searchfield": "name",
			"start": 0,
			"page_len": 20,
		}

		with self.set_user(user.name):
			rows = queries.get_filtered_child_rows(**params, filters={"parent": po.name})
			self.assertEqual([row[0] for row in rows], [po.items[0].name])

			with self.assertRaises(frappe.PermissionError):
				queries.get_filtered_child_rows(
					**params, filters={"parent": po.name, "sales_order.grand_total": so.grand_total}
				)

	def test_default_uoms(self):
		self.assertGreaterEqual(frappe.db.count("UOM", {"enabled": 1}), 10)

	def test_employee_query_with_user_permissions(self):
		employee = frappe.db.get_all("Employee", {"first_name": "_Test Employee"})[0].name

		# party field is a dynamic link field in Payment Entry doctype with ignore_user_permissions=0
		ps = make_property_setter(
			doctype="Payment Entry",
			fieldname="party",
			property="ignore_user_permissions",
			value=1,
			property_type="Check",
		)

		user = create_user("test_employee_query@example.com", "Accounts User", "HR User")
		add_user_permissions(
			{
				"user": user.name,
				"doctype": "Employee",
				"docname": employee,
				"is_default": 1,
				"apply_to_all_doctypes": 1,
				"applicable_doctypes": [],
				"hide_descendants": 0,
			}
		)

		with ERPNextTestSuite.set_user(self, user.name):
			params = {
				"doctype": "Employee",
				"txt": "",
				"searchfield": "name",
				"start": 0,
				"page_len": 20,
				"filters": None,
				"reference_doctype": "Payment Entry",
				"ignore_user_permissions": 1,
			}

			result = queries.employee_query(**params)
			self.assertGreater(len(result), 1)

			ps.delete(ignore_permissions=1, force=1, delete_permanently=1)

			# only one employee should be returned even though ignore_user_permissions is passed as 1
			result = queries.employee_query(**params)
			self.assertEqual(len(result), 1)
