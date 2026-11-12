import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.quick_stock_balance.quick_stock_balance import get_stock_item_details
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
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
