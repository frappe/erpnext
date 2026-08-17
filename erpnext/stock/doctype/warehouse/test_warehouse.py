# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

import erpnext
from erpnext.accounts.doctype.account.test_account import create_account
from erpnext.stock.doctype.item.test_item import create_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.doctype.warehouse.warehouse import convert_to_group_or_ledger, get_children
from erpnext.tests.utils import ERPNextTestSuite


class TestWarehouse(ERPNextTestSuite):
	def test_parent_warehouse(self):
		parent_warehouse = frappe.get_doc("Warehouse", "_Test Warehouse Group - _TC")
		self.assertEqual(parent_warehouse.is_group, 1)

	def test_warehouse_hierarchy(self):
		p_warehouse = frappe.get_doc("Warehouse", "_Test Warehouse Group - _TC")

		child_warehouses = frappe.get_all(
			"Warehouse",
			filters={"lft": [">", p_warehouse.lft], "rgt": ["<", p_warehouse.rgt]},
			fields=["name", "is_group", "parent_warehouse"],
		)

		for child_warehouse in child_warehouses:
			self.assertEqual(p_warehouse.name, child_warehouse.parent_warehouse)
			self.assertEqual(child_warehouse.is_group, 0)

	def test_naming(self):
		company = "Wind Power LLC"
		warehouse_name = "Named Warehouse - WP"
		wh = frappe.get_doc(doctype="Warehouse", warehouse_name=warehouse_name, company=company).insert()
		self.assertEqual(wh.name, warehouse_name)

		warehouse_name = "Unnamed Warehouse"
		wh = frappe.get_doc(doctype="Warehouse", warehouse_name=warehouse_name, company=company).insert()
		self.assertIn(warehouse_name, wh.name)

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

	def test_inventory_account_fallback_with_multiple_stock_accounts(self):
		from erpnext.stock import get_warehouse_account

		company = create_inventory_fallback_company()
		frappe.db.set_value("Company", company, "default_inventory_account", None)
		if frappe.db.exists("Account", "Extra Inventory Account - _TCIF"):
			frappe.delete_doc("Account", "Extra Inventory Account - _TCIF")

		warehouse = frappe.get_doc("Warehouse", {"company": company, "is_group": 0})
		single_account = frappe.db.get_value(
			"Account", {"account_type": "Stock", "is_group": 0, "company": company}, "name"
		)
		self.assertEqual(get_warehouse_account(warehouse), single_account)

		create_account(
			account_name="Extra Inventory Account",
			parent_account=frappe.db.get_value("Account", single_account, "parent_account"),
			account_type="Stock",
			company=company,
		)
		self.assertRaises(frappe.ValidationError, get_warehouse_account, warehouse)

	def test_unrelated_warehouse_without_inventory_account_is_ignored(self):
		from erpnext.stock import get_warehouse_account_map

		company, warehouse = create_ambiguous_inventory_account_warehouse()
		warehouse_account_map = get_warehouse_account_map(company)
		resolved_warehouse = next(iter(warehouse_account_map))
		stock_entry = frappe.get_doc({"doctype": "Stock Entry", "company": company})

		self.assertNotIn(warehouse.name, warehouse_account_map)
		self.assertTrue(
			stock_entry.get_inventory_account_dict(
				frappe._dict(warehouse=resolved_warehouse), warehouse_account_map
			).account
		)
		self.assertFalse(
			stock_entry.get_inventory_account_dict(
				frappe._dict(supplier_warehouse=warehouse.name),
				warehouse_account_map,
				"supplier_warehouse",
				raise_error=False,
			)
		)

	def test_warehouse_without_inventory_account_is_validated_when_used(self):
		from erpnext.stock import get_warehouse_account_map

		company, warehouse = create_ambiguous_inventory_account_warehouse()
		stock_entry = frappe.get_doc({"doctype": "Stock Entry", "company": company})

		with self.assertRaises(frappe.ValidationError):
			stock_entry.get_inventory_account_dict(
				frappe._dict(warehouse=warehouse.name), get_warehouse_account_map(company)
			)

	def test_new_warehouse_requires_inventory_account(self):
		company, _warehouse = create_ambiguous_inventory_account_warehouse()
		frappe.db.set_value("Company", company, "enable_perpetual_inventory", 1)
		parent_warehouse = frappe.db.get_value("Warehouse", {"company": company, "is_group": 1}, "name")
		frappe.db.set_value("Warehouse", parent_warehouse, "account", None)
		warehouse = frappe.get_doc(
			{
				"doctype": "Warehouse",
				"warehouse_name": "Missing Inventory Account",
				"parent_warehouse": parent_warehouse,
				"company": company,
			}
		)

		self.assertRaisesRegex(frappe.ValidationError, "Missing Inventory Account - _TCIF", warehouse.insert)

	def test_new_warehouse_can_inherit_inventory_account(self):
		from erpnext.stock import get_warehouse_account

		company, _warehouse = create_ambiguous_inventory_account_warehouse()
		frappe.db.set_value("Company", company, "enable_perpetual_inventory", 1)
		parent_warehouse = frappe.db.get_value("Warehouse", {"company": company, "is_group": 1}, "name")
		inventory_account = frappe.db.get_value(
			"Account", {"company": company, "account_type": "Stock", "is_group": 0}, "name"
		)
		frappe.db.set_value("Warehouse", parent_warehouse, "account", inventory_account)

		warehouse = frappe.get_doc(
			{
				"doctype": "Warehouse",
				"warehouse_name": "Inherited Inventory Account",
				"parent_warehouse": parent_warehouse,
				"company": company,
			}
		).insert()

		self.assertEqual(get_warehouse_account(warehouse), inventory_account)

	def test_new_warehouse_inherits_from_parent_created_in_same_transaction(self):
		from erpnext.stock import get_warehouse_account

		company, _warehouse = create_ambiguous_inventory_account_warehouse()
		frappe.db.set_value("Company", company, "enable_perpetual_inventory", 1)
		root_warehouse = frappe.db.get_value("Warehouse", {"company": company, "is_group": 1}, "name")
		inventory_account = frappe.db.get_value(
			"Account", {"company": company, "account_type": "Stock", "is_group": 0}, "name"
		)

		parent_warehouse = frappe.get_doc(
			{
				"doctype": "Warehouse",
				"warehouse_name": "New Parent Warehouse",
				"parent_warehouse": root_warehouse,
				"company": company,
				"is_group": 1,
				"account": inventory_account,
			}
		).insert()
		child_warehouse = frappe.get_doc(
			{
				"doctype": "Warehouse",
				"warehouse_name": "New Child Warehouse",
				"parent_warehouse": parent_warehouse.name,
				"company": company,
			}
		).insert()

		self.assertEqual(get_warehouse_account(child_warehouse), inventory_account)

	def test_warehouse_onload_allows_missing_inventory_account(self):
		company, warehouse = create_ambiguous_inventory_account_warehouse()
		frappe.db.set_value("Company", company, "enable_perpetual_inventory", 1)

		warehouse.run_method("onload")

		self.assertNotIn("account", warehouse.get_onload())


def create_inventory_fallback_company():
	company = "_Test Company Inventory Fallback"
	if not frappe.db.exists("Company", company):
		frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": company,
				"abbr": "_TCIF",
				"default_currency": "INR",
				"enable_perpetual_inventory": 0,
				"country": "India",
			}
		).insert(ignore_permissions=True)
	return company


def create_ambiguous_inventory_account_warehouse():
	company = create_inventory_fallback_company()
	frappe.db.set_value("Company", company, "default_inventory_account", None)

	single_account = frappe.db.get_value(
		"Account", {"account_type": "Stock", "is_group": 0, "company": company}, "name"
	)
	warehouses = frappe.get_all(
		"Warehouse", filters={"company": company, "is_group": 0}, pluck="name", order_by="name"
	)
	for warehouse_name in warehouses:
		frappe.db.set_value("Warehouse", warehouse_name, "account", single_account)

	warehouse = frappe.get_doc("Warehouse", warehouses[0])
	warehouse.db_set({"account": None, "disabled": 0})

	if not frappe.db.exists("Account", "Extra Inventory Account - _TCIF"):
		create_account(
			account_name="Extra Inventory Account",
			parent_account=frappe.db.get_value("Account", single_account, "parent_account"),
			account_type="Stock",
			company=company,
		)

	return company, warehouse


def create_warehouse(warehouse_name, properties=None, company=None):
	if not company:
		company = "_Test Company"

	warehouse_id = erpnext.encode_company_abbr(warehouse_name, company)
	if not frappe.db.exists("Warehouse", warehouse_id):
		w = frappe.new_doc("Warehouse")
		w.warehouse_name = warehouse_name
		w.parent_warehouse = "_Test Warehouse Group - _TC"
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
