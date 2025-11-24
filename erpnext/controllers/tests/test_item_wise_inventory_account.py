# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import copy
from collections import defaultdict

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, cint, today

from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry
from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt


class TestItemWiseInventoryAccount(IntegrationTestCase):
	def setUp(self):
		self.company = make_company()
		self.company_abbr = frappe.db.get_value("Company", self.company, "abbr")
		self.default_warehouse = frappe.db.get_value(
			"Warehouse",
			{"company": self.company, "is_group": 0, "warehouse_name": ("like", "%Stores%")},
		)

	def test_item_account_for_purchase_receipt_entry(self):
		items = {
			"Stock Item A": {"is_stock_item": 1},
			"Stock Item B": {"is_stock_item": 1, "has_serial_no": 1, "serial_no_series": "SER-TT-.####"},
		}

		for item_name, item_data in items.items():
			item = make_item(
				item_name,
				properties=item_data,
			)

			account = self.add_inventory_account(item)
			items[item_name]["account"] = account

		pr = make_purchase_receipt(
			item_code="Stock Item A",
			qty=5,
			rate=100,
			warehouse=self.default_warehouse,
			company=self.company,
			do_not_submit=True,
		)

		pr.append(
			"items",
			{
				"item_code": "Stock Item B",
				"qty": 2,
				"rate": 200,
				"warehouse": self.default_warehouse,
			},
		)

		pr.submit()

		for row in items:
			item_code = row
			account = items[item_code]["account"]

			sle_value = frappe.db.get_value(
				"Stock Ledger Entry",
				{"voucher_type": "Purchase Receipt", "voucher_no": pr.name, "item_code": item_code},
				"stock_value_difference",
			)

			gl_value = frappe.db.get_value(
				"GL Entry",
				{
					"voucher_type": "Purchase Receipt",
					"voucher_no": pr.name,
					"account": account,
				},
				"debit",
			)

			self.assertEqual(sle_value, gl_value, f"GL Entry not created for {item_code} correctly")

	def test_item_account_for_delivery_note_entry(self):
		items = {
			"Stock Item A": {"is_stock_item": 1},
			"Stock Item B": {"is_stock_item": 1, "has_serial_no": 1, "serial_no_series": "SER-TT-.####"},
		}

		for item_name, item_data in items.items():
			item = make_item(
				item_name,
				properties=item_data,
			)

			account = self.add_inventory_account(item)
			items[item_name]["account"] = account

		pr = make_purchase_receipt(
			item_code="Stock Item A",
			qty=5,
			rate=100,
			warehouse=self.default_warehouse,
			company=self.company,
			do_not_submit=True,
		)

		pr.append(
			"items",
			{
				"item_code": "Stock Item B",
				"qty": 2,
				"rate": 200,
				"warehouse": self.default_warehouse,
			},
		)

		pr.submit()

		dn = create_delivery_note(
			item_code="Stock Item A",
			qty=5,
			rate=200,
			warehouse=self.default_warehouse,
			company=self.company,
			cost_center=frappe.db.get_value("Company", self.company, "cost_center"),
			expense_account=frappe.db.get_value("Company", self.company, "default_expense_account"),
			do_not_submit=True,
		)

		dn.append(
			"items",
			{
				"item_code": "Stock Item B",
				"qty": 2,
				"rate": 300,
				"warehouse": self.default_warehouse,
			},
		)

		dn.submit()

		for row in items:
			item_code = row
			account = items[item_code]["account"]

			sle_value = frappe.db.get_value(
				"Stock Ledger Entry",
				{"voucher_type": "Delivery Note", "voucher_no": dn.name, "item_code": item_code},
				"stock_value_difference",
			)

			gl_value = (
				frappe.db.get_value(
					"GL Entry",
					{
						"voucher_type": "Delivery Note",
						"voucher_no": dn.name,
						"account": account,
					},
					"credit",
				)
				* -1
			)

			self.assertEqual(sle_value, gl_value, f"GL Entry not created for {item_code} correctly")

	def test_item_account_for_backdated_purchase_receipt(self):
		items = {
			"Bottle Item A": {"is_stock_item": 1},
		}

		for item_name, item_data in items.items():
			item = make_item(
				item_name,
				properties=item_data,
			)

			account = self.add_inventory_account(item)
			items[item_name]["account"] = account

		make_purchase_receipt(
			item_code="Bottle Item A",
			qty=5,
			rate=100,
			warehouse=self.default_warehouse,
			company=self.company,
		)

		dn = create_delivery_note(
			item_code="Bottle Item A",
			qty=5,
			rate=200,
			warehouse=self.default_warehouse,
			company=self.company,
			cost_center=frappe.db.get_value("Company", self.company, "cost_center"),
			expense_account=frappe.db.get_value("Company", self.company, "default_expense_account"),
		)

		for row in items:
			item_code = row
			account = items[item_code]["account"]

			sle_value = frappe.db.get_value(
				"Stock Ledger Entry",
				{"voucher_type": "Delivery Note", "voucher_no": dn.name, "item_code": item_code},
				"stock_value_difference",
			)

			gl_value = (
				frappe.db.get_value(
					"GL Entry",
					{
						"voucher_type": "Delivery Note",
						"voucher_no": dn.name,
						"account": account,
					},
					"credit",
				)
				* -1
			)

			self.assertEqual(sle_value, gl_value, f"GL Entry not created for {item_code} correctly")

		make_purchase_receipt(
			item_code="Bottle Item A",
			posting_date=add_days(today(), -1),
			qty=5,
			rate=200,
			warehouse=self.default_warehouse,
			company=self.company,
		)

		for row in items:
			item_code = row
			account = items[item_code]["account"]

			sle_value = frappe.db.get_value(
				"Stock Ledger Entry",
				{"voucher_type": "Delivery Note", "voucher_no": dn.name, "item_code": item_code},
				"stock_value_difference",
			)

			gl_value = (
				frappe.db.get_value(
					"GL Entry",
					{
						"voucher_type": "Delivery Note",
						"voucher_no": dn.name,
						"account": account,
					},
					"credit",
				)
				* -1
			)

			self.assertEqual(sle_value, gl_value, f"GL Entry not created for {item_code} correctly")
			self.assertEqual(sle_value, 1000.0 * -1, f"GL Entry not created for {item_code} correctly")

	def test_item_group_account_for_purchase_receipt_entry(self):
		items = {
			"Stock Item C": {"is_stock_item": 1, "item_group": "Test Item Group C"},
			"Stock Item C1": {"is_stock_item": 1, "item_group": "Test Item Group C", "qty": 3, "rate": 150},
			"Stock Item D": {
				"is_stock_item": 1,
				"has_serial_no": 1,
				"serial_no_series": "SER-TT-.####",
				"item_group": "Test Item Group D",
				"qty": 2,
				"rate": 250,
			},
			"Stock Item D1": {"is_stock_item": 1, "item_group": "Test Item Group D", "qty": 4, "rate": 300},
		}

		for row in items:
			self.make_item_group(items[row]["item_group"])

		inventory_account_dict = frappe._dict()
		for item_name, item_data in items.items():
			item_data = frappe._dict(item_data)
			make_item(
				item_name,
				properties=item_data,
			)

			item_group = frappe.get_doc("Item Group", item_data.item_group)
			account = self.add_inventory_account(item_group, "item_group_defaults")
			inventory_account_dict[item_data.item_group] = account

		pr = make_purchase_receipt(
			item_code="Stock Item C",
			qty=5,
			rate=100,
			warehouse=self.default_warehouse,
			company=self.company,
			do_not_submit=True,
		)

		for item_code, values in items.items():
			if item_code == "Stock Item C":
				continue

			pr.append(
				"items",
				{
					"item_code": item_code,
					"qty": values.get("qty", 1),
					"rate": values.get("rate", 200),
					"warehouse": self.default_warehouse,
				},
			)

		pr.submit()

		for item_group, account in inventory_account_dict.items():
			items = frappe.get_all(
				"Item",
				filters={"item_group": item_group},
				pluck="name",
			)

			sle_value = frappe.get_all(
				"Stock Ledger Entry",
				filters={
					"voucher_type": "Purchase Receipt",
					"voucher_no": pr.name,
					"item_code": ("in", items),
				},
				fields=[{"SUM": "stock_value_difference", "as": "value"}],
			)

			gl_value = frappe.db.get_value(
				"GL Entry",
				{
					"voucher_type": "Purchase Receipt",
					"voucher_no": pr.name,
					"account": account,
				},
				"debit",
			)

			self.assertEqual(sle_value[0].value, gl_value, f"GL Entry not created for {item_code} correctly")

	def test_item_group_account_for_delivery_note_entry(self):
		items = {
			"Stock Item E": {"is_stock_item": 1, "item_group": "Test Item Group E"},
			"Stock Item E1": {"is_stock_item": 1, "item_group": "Test Item Group E", "qty": 3, "rate": 150},
			"Stock Item F": {
				"is_stock_item": 1,
				"has_serial_no": 1,
				"serial_no_series": "SER-TT-.####",
				"item_group": "Test Item Group F",
				"qty": 2,
				"rate": 250,
			},
			"Stock Item F1": {"is_stock_item": 1, "item_group": "Test Item Group F", "qty": 4, "rate": 300},
		}

		for row in items:
			self.make_item_group(items[row]["item_group"])

		inventory_account_dict = frappe._dict()
		for item_name, item_data in items.items():
			item_data = frappe._dict(item_data)
			make_item(
				item_name,
				properties=item_data,
			)

			item_group = frappe.get_doc("Item Group", item_data.item_group)
			account = self.add_inventory_account(item_group, "item_group_defaults")
			inventory_account_dict[item_data.item_group] = account

		pr = make_purchase_receipt(
			item_code="Stock Item E",
			qty=5,
			rate=100,
			warehouse=self.default_warehouse,
			company=self.company,
			do_not_submit=True,
		)

		for item_code, values in items.items():
			if item_code == "Stock Item E":
				continue

			pr.append(
				"items",
				{
					"item_code": item_code,
					"qty": values.get("qty", 1),
					"rate": values.get("rate", 200),
					"warehouse": self.default_warehouse,
				},
			)

		pr.submit()

		dn = create_delivery_note(
			item_code="Stock Item E",
			qty=5,
			rate=200,
			warehouse=self.default_warehouse,
			company=self.company,
			cost_center=frappe.db.get_value("Company", self.company, "cost_center"),
			expense_account=frappe.db.get_value("Company", self.company, "default_expense_account"),
			do_not_submit=True,
		)

		for item_code, values in items.items():
			if item_code == "Stock Item E":
				continue

			dn.append(
				"items",
				{
					"item_code": item_code,
					"qty": values.get("qty", 1),
					"rate": values.get("rate", 200),
					"warehouse": self.default_warehouse,
				},
			)

		dn.submit()

		for item_group, account in inventory_account_dict.items():
			items = frappe.get_all(
				"Item",
				filters={"item_group": item_group},
				pluck="name",
			)

			sle_value = frappe.get_all(
				"Stock Ledger Entry",
				filters={"voucher_type": "Delivery Note", "voucher_no": dn.name, "item_code": ("in", items)},
				fields=[{"SUM": "stock_value_difference", "as": "value"}],
			)

			gl_value = (
				frappe.db.get_value(
					"GL Entry",
					{
						"voucher_type": "Delivery Note",
						"voucher_no": dn.name,
						"account": account,
					},
					"credit",
				)
				* -1
			)

			self.assertEqual(sle_value[0].value, gl_value, f"GL Entry not created for {item_code} correctly")

	def make_item_group(self, item_name):
		if not frappe.db.exists("Item Group", item_name):
			item_group = frappe.get_doc(
				{
					"doctype": "Item Group",
					"item_group_name": item_name,
					"is_group": 0,
				}
			)
			item_group.insert()
			return item_group

		return frappe.get_doc("Item Group", item_name)

	def add_inventory_account(self, item, table_name=None):
		if not table_name:
			table_name = "item_defaults"

		account = item.name + " - " + self.company_abbr
		if not frappe.db.exists("Account", account):
			account_doc = frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": item.name,
					"account_type": "Stock",
					"company": self.company,
					"is_group": 0,
					"parent_account": "Stock Assets - " + self.company_abbr,
				}
			)
			account_doc.insert()

		if not frappe.db.get_value("Item Default", {"parent": item.name, "company": self.company}):
			item.append(
				table_name,
				{
					"company": self.company,
					"default_inventory_account": account,
					"default_warehouse": self.default_warehouse,
				},
			)
			item.save()

		return account

	def test_item_account_for_manufacture_entry(self):
		items = {
			"Stock Item A1": {"is_stock_item": 1},
			"Stock Item B1": {"is_stock_item": 1, "has_serial_no": 1, "serial_no_series": "SER-TT-.####"},
		}

		for item_name, item_data in items.items():
			item = make_item(
				item_name,
				properties=item_data,
			)

			account = self.add_inventory_account(item)
			items[item_name]["account"] = account

		make_purchase_receipt(
			item_code="Stock Item B1",
			qty=5,
			rate=100,
			warehouse=self.default_warehouse,
			company=self.company,
		)

		bom = make_bom(
			item="Stock Item A1",
			company=self.company,
			source_warehouse=self.default_warehouse,
			raw_materials=["Stock Item B1"],
		)

		wip_warehouse = frappe.db.get_value(
			"Warehouse",
			{"company": self.company, "is_group": 0, "warehouse_name": ("like", "%Work In Progress%")},
		)

		fg_warehouse = frappe.db.get_value(
			"Warehouse",
			{"company": self.company, "is_group": 0, "warehouse_name": ("like", "%Finished Goods%")},
		)

		wo_order = make_wo_order_test_record(
			item="Stock Item A1",
			qty=5,
			company=self.company,
			source_warehouse=self.default_warehouse,
			bom=bom.name,
			wip_warehouse=wip_warehouse,
			fg_warehouse=fg_warehouse,
		)

		stock_entry = frappe.get_doc(make_stock_entry(wo_order.name, "Material Transfer for Manufacture", 5))
		stock_entry.submit()

		stock_entry = frappe.get_doc(make_stock_entry(wo_order.name, "Manufacture", 5))
		stock_entry.submit()

		for row in stock_entry.items:
			item_code = row.item_code
			account = items[item_code]["account"]

			sle_value = frappe.db.get_value(
				"Stock Ledger Entry",
				{"voucher_type": "Stock Entry", "voucher_no": stock_entry.name, "item_code": item_code},
				"stock_value_difference",
			)

			field = "debit" if row.t_warehouse == fg_warehouse else "credit"
			gl_value = frappe.db.get_value(
				"GL Entry",
				{
					"voucher_type": "Stock Entry",
					"voucher_no": stock_entry.name,
					"account": account,
				},
				field,
			)

			if row.s_warehouse:
				gl_value = gl_value * -1

			self.assertEqual(sle_value, gl_value, f"GL Entry not created for {item_code} correctly")


def make_company():
	company = "_Test Company for Item Wise Inventory Account"
	if frappe.db.exists("Company", company):
		return company

	company = frappe.get_doc(
		{
			"doctype": "Company",
			"company_name": "_Test Company for Item Wise Inventory Account",
			"abbr": "_TCIWIA",
			"default_currency": "INR",
			"country": "India",
			"enable_perpetual_inventory": 1,
			"enable_item_wise_inventory_account": 1,
		}
	).insert()

	return company.name
