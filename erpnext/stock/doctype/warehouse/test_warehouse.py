# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.test_runner import make_test_records
from frappe.tests.utils import FrappeTestCase

import erpnext
from erpnext.accounts.doctype.account.test_account import create_account
from erpnext.stock.doctype.item.test_item import create_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.doctype.warehouse.warehouse import convert_to_group_or_ledger, get_children

test_records = frappe.get_test_records("Warehouse")


class TestWarehouse(FrappeTestCase):
	def setUp(self):
		super().setUp()
		if not frappe.get_value("Item", "_Test Item"):
			make_test_records("Item")

		# Ensure _Test Company exists
		if not frappe.db.exists("Company", "_Test Company"):
			company = frappe.new_doc("Company")
			company.company_name = "_Test Company"
			company.default_currency = "INR"
			company.insert()

		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")

	def tearDown(self):
		frappe.db.rollback()

	def test_parent_warehouse(self):
		parent_warehouse = frappe.get_doc("Warehouse", "_Test Warehouse Group - _TC")
		self.assertEqual(parent_warehouse.is_group, 1)

	def test_warehouse_hierarchy(self):
		p_warehouse = frappe.get_doc("Warehouse", "_Test Warehouse Group - _TC")

		child_warehouses = frappe.db.sql(
			"""select name, is_group, parent_warehouse from `tabWarehouse` wh
			where wh.lft > %s and wh.rgt < %s""",
			(p_warehouse.lft, p_warehouse.rgt),
			as_dict=1,
		)

		for child_warehouse in child_warehouses:
			self.assertEqual(p_warehouse.name, child_warehouse.parent_warehouse)
			self.assertEqual(child_warehouse.is_group, 0)

	def test_naming(self):
		company_name = "Wind Power LLC"
		if not frappe.db.exists("Company", company_name):
			company = frappe.new_doc("Company")
			company.company_name = company_name
			company.default_currency = "INR"
			company.insert()
		else:
			company = frappe.get_doc("Company", company_name)

		# delete warehouses if already exist
		for wh_name in ["Named Warehouse", "Unnamed Warehouse"]:
			existing_whs = frappe.get_all(
				"Warehouse", filters={"warehouse_name": wh_name, "company": company.name}
			)
			for wh in existing_whs:
				frappe.delete_doc("Warehouse", wh.name, force=True)

		warehouse_name = "Named Warehouse"
		wh = frappe.get_doc(doctype="Warehouse", warehouse_name=warehouse_name, company=company.name).insert()
		self.assertTrue(wh.name.startswith(warehouse_name))

		warehouse_name = "Unnamed Warehouse"
		wh = frappe.get_doc(doctype="Warehouse", warehouse_name=warehouse_name, company=company.name).insert()
		self.assertTrue(wh.name.startswith(warehouse_name))

	def test_unlinking_warehouse_from_item_defaults(self):
		company = "_Test Company"

		warehouse_names = [f"_Test Warehouse {i} for Unlinking" for i in range(2)]
		warehouse_ids = []
		for warehouse in warehouse_names:
			warehouse_id = create_warehouse(warehouse, company=company)
			warehouse_ids.append(warehouse_id)

		item_names = [f"_Test Item {i} for Unlinking" for i in range(2)]
		for item, warehouse in zip(item_names, warehouse_ids, strict=False):
			create_item(item, warehouse=warehouse, company=company)

		# Delete warehouses
		for warehouse in warehouse_ids:
			frappe.delete_doc("Warehouse", warehouse)

		# Check Item existance
		for item in item_names:
			self.assertTrue(bool(frappe.db.exists("Item", item)), f"{item} doesn't exist")

			item_doc = frappe.get_doc("Item", item)
			for item_default in item_doc.item_defaults:
				self.assertNotIn(
					item_default.default_warehouse,
					warehouse_ids,
					f"{item} linked to {item_default.default_warehouse} in {warehouse_ids}.",
				)

	def test_group_non_group_conversion(self):
		warehouse = frappe.get_doc("Warehouse", create_warehouse("TestGroupConversion"))

		convert_to_group_or_ledger(warehouse.name)
		warehouse.reload()
		self.assertEqual(warehouse.is_group, 1)

		child = create_warehouse("GroupWHChild", {"parent_warehouse": warehouse.name})
		# chid exists
		self.assertRaises(frappe.ValidationError, convert_to_group_or_ledger, warehouse.name)
		frappe.delete_doc("Warehouse", child)

		convert_to_group_or_ledger(warehouse.name)
		warehouse.reload()
		self.assertEqual(warehouse.is_group, 0)

		make_stock_entry(item_code="_Test Item", target=warehouse.name, qty=1)
		# SLE exists
		self.assertRaises(frappe.ValidationError, convert_to_group_or_ledger, warehouse.name)

	def test_get_children(self):
		company = "_Test Company"

		children = get_children("Warehouse", parent=company, company=company, is_root=True)
		self.assertTrue(any(wh["value"] == "_Test Warehouse - _TC" for wh in children))

	def test_create_warehouse_TC_SCK_157(self):
		"""Test warehouse creation with valid inputs."""
		if not frappe.db.exists("Company", "_Test Company"):
			company = frappe.new_doc("Company")
			company.company_name = "_Test Company"
			company.default_currency = "INR"
			company.insert()
		warehouse = create_warehouse("_Test Warehouse", properties=None, company="_Test Company")

		# Fetch created warehouse
		created_warehouse = frappe.get_doc("Warehouse", warehouse)

		# Assertions
		self.assertEqual(created_warehouse.warehouse_name, "_Test Warehouse")
		self.assertEqual(created_warehouse.company, "_Test Company")
		self.assertFalse(created_warehouse.is_rejected_warehouse)

		warehouse_rej = create_warehouse(
			"_Test Warehouse - Rejected", properties={"is_rejected_warehouse": 1}, company="_Test Company"
		)

		# Fetch created warehouse
		created_warehouse = frappe.get_doc("Warehouse", warehouse_rej)

		# Assertions
		self.assertTrue(created_warehouse.is_rejected_warehouse)

		# Attempt to use this warehouse in a Stock Entry (should fail)
		stock_entry = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": "Material Receipt",
				"items": [{"item_code": "Test Item", "qty": 1, "t_warehouse": created_warehouse.name}],
			}
		)

		with self.assertRaises(frappe.ValidationError):
			stock_entry.insert()

	def test_on_trash_with_existing_quantity_TC_SCK_329(self):
		"""Test warehouse creation with valid inputs."""
		warehouse = create_warehouse("_Test Warehouse", company="_Test Company")

		# Create item with valid warehouse and company
		if not frappe.db.exists("Item", "_Test Item"):
			create_item("_Test Item", warehouse=warehouse, company="_Test Company")

		# Make sure the test item is stock item with valuation rate
		item = frappe.get_doc("Item", "_Test Item")
		item.is_stock_item = 1
		item.valuation_rate = 100
		item.save(ignore_permissions=True)

		se = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": "Material Receipt",
				"company": "_Test Company",
				"items": [
					{
						"item_code": "_Test Item",
						"qty": 5,
						"t_warehouse": warehouse,
						"uom": "Nos",
						"stock_uom": "Nos",
						"conversion_factor": 1,
					}
				],
			}
		)
		se.insert()
		se.submit()

		# Try to delete warehouse, should raise ValidationError
		with self.assertRaises(frappe.ValidationError, msg="can not be deleted as quantity exists"):
			frappe.delete_doc("Warehouse", warehouse)

	def test_on_trash_with_existing_stock_ledger_entry_TC_SCK_330(self):
		"""Test warehouse creation with valid inputs."""
		warehouse = create_warehouse("_Test Warehouse", company="_Test Company")

		# Create item with valid warehouse and company
		if not frappe.db.exists("Item", "_Test Item"):
			create_item("_Test Item", warehouse=warehouse, company="_Test Company")

		# setting item valuation rate
		item = frappe.get_doc("Item", "_Test Item")
		item.valuation_rate = 100  # or any positive float value
		item.save(ignore_permissions=True)

		# Create stock entry using your helper function
		make_stock_entry(item_code="_Test Item", qty=5, company="_Test Company", to_warehouse=warehouse)

		# clear all Bin quantities to allow on_trash to reach SLE check
		bin_doc = frappe.get_doc("Bin", {"warehouse": warehouse, "item_code": "_Test Item"})
		bin_doc.actual_qty = 0
		bin_doc.projected_qty = 0
		bin_doc.save(ignore_permissions=True)

		# Try deleting the warehouse - should fail due to SLE
		with self.assertRaises(frappe.ValidationError, msg="stock ledger entry exists"):
			frappe.delete_doc("Warehouse", warehouse)

	def test_onload_loads_account_if_perpetual_inventory_enabled_TC_SCK_331(self):
		# Ensure test company exists and enable perpetual inventory
		if not frappe.db.exists("Company", "_Test Company"):
			frappe.get_doc(
				{"doctype": "Company", "company_name": "_Test Company", "abbreviation": "_TC"}
			).insert()
		frappe.db.set_value("Company", "_Test Company", "enable_perpetual_inventory", 1)

		# Create warehouse
		warehouse = create_warehouse("_Test Warehouse", company="_Test Company")

		# Set account to the actual expected account
		expected_account = get_warehouse_account("_Test Warehouse", "_Test Company")
		frappe.db.set_value("Warehouse", warehouse, "account", expected_account)

		# Simulate reload and trigger onload
		doc = frappe.get_doc("Warehouse", warehouse)
		doc.onload()

		# Assert the correct account is loaded
		loaded_account = doc.get_onload("account")
		self.assertEqual(loaded_account, expected_account)

	def test_warn_about_multiple_warehouse_account_TC_SCK_332(self):
		company = "_Test Company"
		warehouse_name = "_Test Warehouse"
		account1 = "_Test Stock Account 1"
		account2 = "_Test Stock Account 2"

		stock_group_account = get_stock_assets_group(company)

		# Create two stock accounts if not exist
		for acc in [account1, account2]:
			if not frappe.db.exists("Account", erpnext.encode_company_abbr(acc, company)):
				frappe.get_doc(
					{
						"doctype": "Account",
						"account_name": acc,
						"company": company,
						"parent_account": stock_group_account,
						"account_type": "Stock",
						"is_group": 0,
					}
				).insert(ignore_if_duplicate=True)

				# Create parent warehouse group if not exist
		parent_warehouse_name = erpnext.encode_company_abbr("_Test Warehouse Group", company)
		if not frappe.db.exists("Warehouse", parent_warehouse_name):
			frappe.get_doc(
				{
					"doctype": "Warehouse",
					"warehouse_name": "_Test Warehouse Group",
					"company": company,
					"is_group": 1,
				}
			).insert()

		# Create the test warehouse
		test_warehouse_name = erpnext.encode_company_abbr("_Test Warehouse", company)
		if not frappe.db.exists("Warehouse", test_warehouse_name):
			warehouse_doc = frappe.get_doc(
				{
					"doctype": "Warehouse",
					"warehouse_name": warehouse_name,
					"company": company,
					"parent_warehouse": parent_warehouse_name,
					"account": erpnext.encode_company_abbr(account1, company),
				}
			).insert()

		warehouse_doc = frappe.get_doc("Warehouse", test_warehouse_name)

		if not frappe.db.exists("Item", "_Test Item"):
			create_item("_Test Item", warehouse=test_warehouse_name, company="_Test Company")

			# Make sure the test item is stock item with valuation rate
		item = frappe.get_doc("Item", "_Test Item")
		item.is_stock_item = 1
		item.valuation_rate = 100
		item.save(ignore_permissions=True)

		# Create and submit stock entry - this will auto-create SLE and GL entries
		s_entry = make_stock_entry(item_code="_Test Item", target=test_warehouse_name, qty=1)
		s_entry.submit()

		# Reload warehouse and assign a different account to trigger warning
		warehouse_doc.reload()
		warehouse_doc.account = erpnext.encode_company_abbr(account2, company)
		warehouse_doc.save()

		# Create third stock account if not exist (to test warning)
		account3 = "_Test Stock Account 3"
		if not frappe.db.exists("Account", erpnext.encode_company_abbr(account3, company)):
			frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": account3,
					"company": company,
					"parent_account": stock_group_account,
					"account_type": "Stock",
					"is_group": 0,
				}
			).insert()

			# Change warehouse account to third account to trigger warning
		warehouse_doc.account = erpnext.encode_company_abbr(account3, company)
		warehouse_doc.save()

		# Call method to cover warning logic
		warehouse_doc.warn_about_multiple_warehouse_account()

	def test_add_root_warehouse_node_TC_SCK_333(self):
		frappe.form_dict = frappe._dict(
			{
				"warehouse_name": "_Test Node Warehouse",
				"company": "_Test Company",
				"is_group": 1,
				"is_root": 1,
				"doctype": "Warehouse",
			}
		)

		from erpnext.stock.doctype.warehouse.warehouse import add_node

		node_warehouse_name = erpnext.encode_company_abbr("_Test Node Warehouse", "_Test Company")
		if frappe.db.exists("Warehouse", node_warehouse_name):
			frappe.delete_doc("Warehouse", node_warehouse_name, force=1)

		add_node()

		# Suffix should match company's abbr
		wh = frappe.get_doc("Warehouse", erpnext.encode_company_abbr("_Test Node Warehouse", "_Test Company"))
		self.assertEqual(wh.company, "_Test Company")
		self.assertIsNone(wh.parent_warehouse)
		self.assertTrue(wh.is_group)


def create_warehouse(warehouse_name, properties=None, company=None):
	if not company:
		company = "_Test Company"

	parent_warehouse = "_Test Warehouse Group"
	parent_warehouse_name = erpnext.encode_company_abbr(parent_warehouse, company)

	# Ensure the parent warehouse exists
	if not frappe.db.exists("Warehouse", parent_warehouse_name):
		parent_w = frappe.new_doc("Warehouse")
		parent_w.warehouse_name = parent_warehouse
		parent_w.company = company
		parent_w.is_group = 1  # Set as a group warehouse
		parent_w.save()

	warehouse_id = erpnext.encode_company_abbr(warehouse_name, company)

	if not frappe.db.exists("Warehouse", warehouse_id):
		w = frappe.new_doc("Warehouse")
		w.warehouse_name = warehouse_name
		w.parent_warehouse = parent_warehouse_name
		w.company = company
		w.account = get_warehouse_account(warehouse_name, company)

		if properties:
			w.update(properties)

		w.save()
		return w.name
	else:
		return warehouse_id


def get_warehouse(**args):
	args = frappe._dict(args)
	if frappe.db.exists("Warehouse", args.warehouse_name + " - " + args.abbr):
		return frappe.get_doc("Warehouse", args.warehouse_name + " - " + args.abbr)
	else:
		w = frappe.get_doc(
			{
				"company": args.company or "_Test Company",
				"doctype": "Warehouse",
				"warehouse_name": args.warehouse_name,
				"is_group": 0,
				"account": get_warehouse_account(args.warehouse_name, args.company, args.abbr),
			}
		)
		w.insert()
		return w


def get_warehouse_account(warehouse_name, company, company_abbr=None):
	if not company_abbr:
		company_abbr = frappe.get_cached_value("Company", company, "abbr")

	if not frappe.db.exists("Account", warehouse_name + " - " + company_abbr):
		return create_account(
			account_name=warehouse_name,
			parent_account=get_group_stock_account(company, company_abbr),
			account_type="Stock",
			company=company,
		)
	else:
		return warehouse_name + " - " + company_abbr


def get_group_stock_account(company, company_abbr=None):
	group_stock_account = frappe.db.get_value(
		"Account", filters={"account_type": "Stock", "is_group": 1, "company": company}, fieldname="name"
	)
	if not group_stock_account:
		if not company_abbr:
			company_abbr = frappe.get_cached_value("Company", company, "abbr")
		group_stock_account = "Current Assets - " + company_abbr
	return group_stock_account


def get_stock_assets_group(company):
	stock_group = frappe.db.get_value(
		"Account", {"company": company, "account_type": "Stock", "is_group": 1}, "name"
	)
	if not stock_group:
		abbr = erpnext.get_company_abbr(company)
		stock_group = f"Stock Assets - {abbr}"
	return stock_group


def create_stock_account(account_name, company, parent_account):
	if not frappe.db.exists("Account", account_name):
		frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": account_name,
				"company": company,
				"parent_account": parent_account,
				"account_type": "Stock",
				"is_group": 0,
			}
		).insert(ignore_if_duplicate=True)
