# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals

import unittest

import frappe
from frappe.utils import cint
from frappe.test_runner import make_test_records

import erpnext
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.accounts.doctype.account.test_account import get_inventory_account, create_account
from erpnext.stock.doctype.item.test_item import create_item

test_records = frappe.get_test_records('Warehouse')

class TestWarehouse(unittest.TestCase):
	def setUp(self):
		if not frappe.get_value('Item', '_Test Item'):
			make_test_records('Item')

	def test_parent_warehouse(self):
		parent_warehouse = frappe.get_doc("Warehouse", "_Test Warehouse Group - _TC")
		self.assertEqual(parent_warehouse.is_group, 1)

	def test_warehouse_hierarchy(self):
		p_warehouse = frappe.get_doc("Warehouse", "_Test Warehouse Group - _TC")

		child_warehouses =  frappe.db.sql("""select name, is_group, parent_warehouse from `tabWarehouse` wh
			where wh.lft > %s and wh.rgt < %s""", (p_warehouse.lft, p_warehouse.rgt), as_dict=1)

		for child_warehouse in child_warehouses:
			self.assertEqual(p_warehouse.name, child_warehouse.parent_warehouse)
			self.assertEqual(child_warehouse.is_group, 0)

	def test_warehouse_renaming(self):
		create_warehouse("Test Warehouse for Renaming 1", company="_Test Company with perpetual inventory")
		account = get_inventory_account("_Test Company with perpetual inventory", "Test Warehouse for Renaming 1 - TCP1")
		self.assertTrue(frappe.db.get_value("Warehouse", filters={"account": account}))

		# Rename with abbr
		if frappe.db.exists("Warehouse", "Test Warehouse for Renaming 2 - TCP1"):
			frappe.delete_doc("Warehouse", "Test Warehouse for Renaming 2 - TCP1")
		frappe.rename_doc("Warehouse", "Test Warehouse for Renaming 1 - TCP1", "Test Warehouse for Renaming 2 - TCP1")

		self.assertTrue(frappe.db.get_value("Warehouse",
			filters={"account": "Test Warehouse for Renaming 1 - TCP1"}))

		# Rename without abbr
		if frappe.db.exists("Warehouse", "Test Warehouse for Renaming 3 - TCP1"):
			frappe.delete_doc("Warehouse", "Test Warehouse for Renaming 3 - TCP1")

		frappe.rename_doc("Warehouse", "Test Warehouse for Renaming 2 - TCP1", "Test Warehouse for Renaming 3")

		self.assertTrue(frappe.db.get_value("Warehouse",
			filters={"account": "Test Warehouse for Renaming 1 - TCP1"}))

		# Another rename with multiple dashes
		if frappe.db.exists("Warehouse", "Test - Warehouse - Company - TCP1"):
			frappe.delete_doc("Warehouse", "Test - Warehouse - Company - TCP1")
		frappe.rename_doc("Warehouse", "Test Warehouse for Renaming 3 - TCP1", "Test - Warehouse - Company")

	def test_warehouse_merging(self):
		company = "_Test Company with perpetual inventory"
		create_warehouse("Test Warehouse for Merging 1", company=company,
			properties={"parent_warehouse": "All Warehouses - TCP1"})
		create_warehouse("Test Warehouse for Merging 2", company=company,
			properties={"parent_warehouse": "All Warehouses - TCP1"})

		make_stock_entry(item_code="_Test Item", target="Test Warehouse for Merging 1 - TCP1",
			qty=1, rate=100, company=company)
		make_stock_entry(item_code="_Test Item", target="Test Warehouse for Merging 2 - TCP1",
			qty=1, rate=100, company=company)

		existing_bin_qty = (
			cint(frappe.db.get_value("Bin",
				{"item_code": "_Test Item", "warehouse": "Test Warehouse for Merging 1 - TCP1"}, "actual_qty"))
			+ cint(frappe.db.get_value("Bin",
				{"item_code": "_Test Item", "warehouse": "Test Warehouse for Merging 2 - TCP1"}, "actual_qty"))
		)

		frappe.rename_doc("Warehouse", "Test Warehouse for Merging 1 - TCP1",
			"Test Warehouse for Merging 2 - TCP1", merge=True)

		self.assertFalse(frappe.db.exists("Warehouse", "Test Warehouse for Merging 1 - TCP1"))

		bin_qty = frappe.db.get_value("Bin",
			{"item_code": "_Test Item", "warehouse": "Test Warehouse for Merging 2 - TCP1"}, "actual_qty")

		self.assertEqual(bin_qty, existing_bin_qty)

		self.assertTrue(frappe.db.get_value("Warehouse",
			filters={"account": "Test Warehouse for Merging 2 - TCP1"}))

	def test_unlinking_warehouse_from_item_defaults(self):
		company = "_Test Company"

		warehouse_names = [f'_Test Warehouse {i} for Unlinking' for i in range(2)]
		warehouse_ids = []
		for warehouse in warehouse_names:
			warehouse_id = create_warehouse(warehouse, company=company)
			warehouse_ids.append(warehouse_id)

		item_names = [f'_Test Item {i} for Unlinking' for i in range(2)]
		for item, warehouse in zip(item_names, warehouse_ids):
			create_item(item, warehouse=warehouse, company=company)

		# Delete warehouses
		for warehouse in warehouse_ids:
			frappe.delete_doc("Warehouse", warehouse)

		# Check Item existance
		for item in item_names:
			self.assertTrue(
				bool(frappe.db.exists("Item", item)),
				f"{item} doesn't exist"
			)

			item_doc = frappe.get_doc("Item", item)
			for item_default in item_doc.item_defaults:
				self.assertNotIn(
					item_default.default_warehouse,
					warehouse_ids,
					f"{item} linked to {item_default.default_warehouse} in {warehouse_ids}."
				)


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
	if(frappe.db.exists("Warehouse", args.warehouse_name + " - " + args.abbr)):
		return frappe.get_doc("Warehouse", args.warehouse_name + " - " + args.abbr)
	else:
		w = frappe.get_doc({
		"company": args.company or "_Test Company",
		"doctype": "Warehouse",
		"warehouse_name": args.warehouse_name,
		"is_group": 0,
		"account": get_warehouse_account(args.warehouse_name, args.company, args.abbr)
		})
		w.insert()
		return w

def get_warehouse_account(warehouse_name, company, company_abbr=None):
	if not company_abbr:
		company_abbr = frappe.get_cached_value("Company", company, 'abbr')

	if not frappe.db.exists("Account", warehouse_name + " - " + company_abbr):
		return create_account(
			account_name=warehouse_name,
			parent_account=get_group_stock_account(company, company_abbr),
			account_type='Stock',
			company=company)
	else:
		return warehouse_name + " - " + company_abbr


def get_group_stock_account(company, company_abbr=None):
	group_stock_account = frappe.db.get_value("Account",
		filters={'account_type': 'Stock', 'is_group': 1, 'company': company}, fieldname='name')
	if not group_stock_account:
		if not company_abbr:
			company_abbr = frappe.get_cached_value("Company", company, 'abbr')
		group_stock_account = "Current Assets - " + company_abbr
	return group_stock_account