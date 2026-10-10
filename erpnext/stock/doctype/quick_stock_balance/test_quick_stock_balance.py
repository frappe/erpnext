import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today

from erpnext.stock.doctype.quick_stock_balance.quick_stock_balance import get_stock_item_details
from erpnext.tests.permission_test_utils import (
	as_user,
	assert_refused,
	assert_refused_for_names,
	assert_refused_without,
	make_fenced_user,
)


class TestQuickStockBalance(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def warehouse_kwargs(self, name):
		return {"warehouse": name, "date": today(), "item": "_Test Item"}

	def item_kwargs(self, name):
		return {"warehouse": "_Test Warehouse - _TC", "date": today(), "item": name}

	def test_get_stock_item_details_refuses_a_warehouse_outside_the_fence(self):
		fenced = make_fenced_user(
			"quick-stock-warehouse@example.com", ["Stock User"], [("Warehouse", "_Test Warehouse - _TC")]
		)
		with as_user(fenced):
			assert_refused_for_names(
				self, get_stock_item_details, self.warehouse_kwargs, ["Stores - _TC"], caller_supplied=True
			)
			details = get_stock_item_details(**self.warehouse_kwargs("_Test Warehouse - _TC"))
		self.assertEqual(details["item"], "_Test Item")

	def test_get_stock_item_details_refuses_an_item_outside_the_fence(self):
		fenced = make_fenced_user(
			"quick-stock-item@example.com", ["Stock User"], [("Item", "_Test Item Home Desktop 100")]
		)
		with as_user(fenced):
			assert_refused_for_names(
				self, get_stock_item_details, self.item_kwargs, ["_Test Item"], caller_supplied=True
			)

	def test_get_stock_item_details_refuses_a_group_with_hidden_descendants(self):
		fenced = make_fenced_user(
			"quick-stock-group-hidden@example.com", ["Stock User"], [("Warehouse", "All Warehouses - _TC", 1)]
		)
		hidden = frappe.get_all(
			"Warehouse", filters={"parent_warehouse": "All Warehouses - _TC"}, pluck="name"
		)
		with as_user(fenced):
			assert_refused_without(
				self, hidden, get_stock_item_details, **self.warehouse_kwargs("All Warehouses - _TC")
			)

	def test_get_stock_item_details_allows_a_group_with_visible_descendants(self):
		fenced = make_fenced_user(
			"quick-stock-group@example.com", ["Stock User"], [("Warehouse", "All Warehouses - _TC", 0)]
		)
		with as_user(fenced):
			details = get_stock_item_details(**self.warehouse_kwargs("All Warehouses - _TC"))
		self.assertEqual(details["item"], "_Test Item")

	def test_get_stock_item_details_requires_item_read(self):
		user = make_fenced_user("quick-stock-no-role@example.com", [])
		with as_user(user):
			assert_refused(self, get_stock_item_details, **self.warehouse_kwargs("_Test Warehouse - _TC"))

	def test_get_stock_item_details_allows_an_unfenced_stock_user(self):
		user = make_fenced_user("quick-stock-open@example.com", ["Stock User"])
		with as_user(user):
			details = get_stock_item_details(**self.warehouse_kwargs("Stores - _TC"))
		self.assertIn("qty", details)
