# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import add_days, today
from frappe.utils.nestedset import get_descendants_of

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.quick_stock_balance.quick_stock_balance import get_stock_item_details
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.tests.permission_test_utils import (
	OTHER_COMPANY,
	as_user,
	assert_refused,
	assert_refused_for_names,
	assert_refused_without,
	insert_test_record,
	make_fenced_user,
)
from erpnext.tests.utils import ERPNextTestSuite

STOCK_USER = "test_quick_stock_balance_stock_user@example.com"
PROJECTS_USER = "test_quick_stock_balance_projects_user@example.com"
WAREHOUSE = "Stores - _TC"
OTHER_COMPANY_WAREHOUSE = "Stores - _TC3"
GROUP_WAREHOUSE = "_Test Warehouse Group - _TC"
UNKNOWN_BARCODE = "_Test Unknown Barcode 59360"
INSIDE_BARCODE = "_Test QSB UP Barcode Inside"
OUTSIDE_BARCODE = "_Test QSB UP Barcode Outside"


def get_warehouse_details(warehouse):
	return get_stock_item_details(warehouse, today(), item="_Test Item")


def get_item_details(item):
	return get_stock_item_details(WAREHOUSE, today(), item=item)


def get_barcode_details(warehouse, barcode=UNKNOWN_BARCODE):
	return get_stock_item_details(warehouse, today(), barcode=barcode)


def warehouse_kwargs(name):
	return {"warehouse": name}


def item_kwargs(name):
	return {"item": name}


def get_link_values(doctype, name, fields):
	values = []
	row = frappe.db.get_value(doctype, name, fields, as_dict=True)
	for field in fields:
		if row.get(field):
			values.append(row.get(field))
	return values


def add_barcode(item, barcode):
	insert_test_record(
		"Item Barcode",
		{"parent": item, "parenttype": "Item", "parentfield": "barcodes", "barcode": barcode},
	)


class TestQuickStockBalance(ERPNextTestSuite):
	def make_warehouse(self, name, parent, is_group=0):
		full_name = f"{name} - _TC"
		if not frappe.db.exists("Warehouse", full_name):
			frappe.get_doc(
				{
					"doctype": "Warehouse",
					"warehouse_name": name,
					"company": "_Test Company",
					"parent_warehouse": parent,
					"is_group": is_group,
				}
			).insert()
		return full_name

	def test_past_date_balance_covers_whole_day(self):
		item = make_item(properties={"is_stock_item": 1}).name
		posting_date = add_days(today(), -1)
		for qty, posting_time in ((10, "00:00:01"), (5, "23:59:58"), (2, "23:59:59.500000")):
			make_stock_entry(
				item_code=item,
				target="_Test Warehouse - _TC",
				qty=qty,
				rate=100,
				posting_date=posting_date,
				posting_time=posting_time,
				set_posting_time=1,
			)

		details = get_stock_item_details("_Test Warehouse - _TC", posting_date, item)

		self.assertEqual((details["qty"], details["value"]), (17, 1700))

	def test_group_warehouse_balance_sums_children(self):
		item = make_item(properties={"is_stock_item": 1}).name
		group = self.make_warehouse("_Test QSB Group", "All Warehouses - _TC", is_group=1)
		for name, qty in (("_Test QSB Child 1", 10), ("_Test QSB Child 2", 5)):
			warehouse = self.make_warehouse(name, group)
			make_stock_entry(item_code=item, target=warehouse, qty=qty, rate=100)

		details = get_stock_item_details(group, today(), item)

		self.assertEqual((details["qty"], details["value"]), (15, 1500))

	def assert_details(self, warehouse, item="_Test Item"):
		out = get_stock_item_details(warehouse, today(), item=item)
		self.assertEqual(out["item"], item)
		self.assertIn("qty", out)

	def test_warehouse_outside_company_fence_is_refused(self):
		user = make_fenced_user(STOCK_USER, ["Stock User"], [("Company", "_Test Company")])
		hidden = get_link_values("Warehouse", OTHER_COMPANY_WAREHOUSE, ["company", "parent_warehouse"])
		self.assertIn(OTHER_COMPANY, hidden)

		with as_user(user):
			assert_refused_without(self, hidden, get_warehouse_details, OTHER_COMPANY_WAREHOUSE)
			self.assert_details(WAREHOUSE)

	def test_warehouse_outside_warehouse_fence_is_refused(self):
		user = make_fenced_user(STOCK_USER, ["Stock User"], [("Warehouse", WAREHOUSE)])
		hidden = get_link_values("Warehouse", "Finished Goods - _TC", ["parent_warehouse"])

		with as_user(user):
			assert_refused_without(self, hidden, get_warehouse_details, "Finished Goods - _TC")
			self.assert_details(WAREHOUSE)

	def test_item_outside_item_fence_is_refused(self):
		user = make_fenced_user(STOCK_USER, ["Stock User"], [("Item", "_Test Item")])
		hidden = get_link_values("Item", "_Test Item 2", ["item_group", "brand"])

		with as_user(user):
			assert_refused_without(self, hidden, get_item_details, "_Test Item 2")
			self.assert_details(WAREHOUSE)

	def test_group_warehouse_follows_hide_descendants(self):
		descendants = get_descendants_of("Warehouse", GROUP_WAREHOUSE, ignore_permissions=True)
		self.assertTrue(descendants)
		user = make_fenced_user(STOCK_USER, ["Stock User"], [("Warehouse", GROUP_WAREHOUSE, 1)])
		with as_user(user):
			assert_refused_without(self, descendants, get_warehouse_details, GROUP_WAREHOUSE)

		make_fenced_user(STOCK_USER, ["Stock User"], [("Warehouse", GROUP_WAREHOUSE, 0)])
		with as_user(user):
			self.assert_details(GROUP_WAREHOUSE)

	def test_barcode_item_outside_item_fence_is_refused(self):
		add_barcode("_Test Item", INSIDE_BARCODE)
		add_barcode("_Test Item 2", OUTSIDE_BARCODE)
		user = make_fenced_user(STOCK_USER, ["Stock User"], [("Item", "_Test Item")])

		with as_user(user):
			assert_refused_without(self, ["_Test Item 2"], get_barcode_details, WAREHOUSE, OUTSIDE_BARCODE)
			out = get_barcode_details(WAREHOUSE, INSIDE_BARCODE)
		self.assertEqual(out["item"], "_Test Item")
		self.assertEqual(out["barcodes"], [INSIDE_BARCODE])

	def test_outside_warehouse_is_refused_before_the_barcode_lookup(self):
		user = make_fenced_user(STOCK_USER, ["Stock User"], [("Warehouse", WAREHOUSE)])

		with as_user(user):
			assert_refused(self, get_barcode_details, "Finished Goods - _TC")
			self.assertRaises(frappe.ValidationError, get_barcode_details, WAREHOUSE)

	def test_missing_names_are_refused(self):
		user = make_fenced_user(STOCK_USER, ["Stock User"], [("Warehouse", WAREHOUSE)])

		with as_user(user):
			assert_refused_for_names(
				self, get_warehouse_details, warehouse_kwargs, [], type_gated=True, caller_supplied=True
			)
			assert_refused_for_names(
				self, get_item_details, item_kwargs, [], type_gated=True, caller_supplied=True
			)

	def test_role_without_item_read_is_refused_and_unfenced_stock_user_is_allowed(self):
		with as_user(make_fenced_user(PROJECTS_USER, ["Projects User"])):
			assert_refused(self, get_barcode_details, WAREHOUSE)
			assert_refused(self, get_item_details, "_Test Item")

		with as_user(make_fenced_user(STOCK_USER, ["Stock User"])):
			self.assert_details(OTHER_COMPANY_WAREHOUSE, "_Test Item 2")
			self.assert_details(GROUP_WAREHOUSE)
