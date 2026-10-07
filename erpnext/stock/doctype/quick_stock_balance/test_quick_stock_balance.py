import frappe
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
from erpnext.tests.utils import ERPNextTestSuite


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
		for qty, posting_time in ((10, "00:00:01"), (5, "23:59:58")):
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

		self.assertEqual((details["qty"], details["value"]), (15, 1500))

	def test_warehouse_and_item_fences(self):
		def stock_kwargs(name):
			return {"warehouse": name, "date": today(), "item": "_Test Item"}

		outside = make_fenced_user(
			"qsb-fenced@example.com", ["Stock User"], [("Warehouse", "_Test Warehouse 1 - _TC")]
		)
		with as_user(outside):
			assert_refused_for_names(
				self,
				get_stock_item_details,
				stock_kwargs,
				["_Test Warehouse - _TC"],
				type_gated=True,
				caller_supplied=True,
			)
		item_outside = make_fenced_user("qsb-fenced@example.com", ["Stock User"], [("Item", "_Test Item 2")])
		with as_user(item_outside):
			assert_refused(self, get_stock_item_details, **stock_kwargs("_Test Warehouse - _TC"))
		item = frappe.get_doc("Item", "_Test Item")
		item.append("barcodes", {"barcode": "UPQSB-0001"})
		item.save()
		with as_user(item_outside):
			assert_refused_without(
				self,
				["_Test Item"],
				get_stock_item_details,
				"_Test Warehouse - _TC",
				today(),
				barcode="UPQSB-0001",
			)
		inside = make_fenced_user(
			"qsb-fenced@example.com", ["Stock User"], [("Warehouse", "_Test Warehouse - _TC")]
		)
		with as_user(inside):
			self.assertEqual(
				get_stock_item_details("_Test Warehouse - _TC", today(), "_Test Item")["item"], "_Test Item"
			)

	def test_group_warehouse_requires_every_descendant(self):
		group = self.make_warehouse("UP QSB Group", "All Warehouses - _TC", is_group=1)
		children = [
			self.make_warehouse("UP QSB Child A", group),
			self.make_warehouse("UP QSB Child B", group),
		]
		user = make_fenced_user("qsb-group@example.com", ["Stock User"], [("Warehouse", group, 1)])
		with as_user(user):
			assert_refused_without(self, children, get_stock_item_details, group, today(), "_Test Item")
		allowed = make_fenced_user("qsb-group@example.com", ["Stock User"], [("Warehouse", group)])
		with as_user(allowed):
			self.assertEqual(get_stock_item_details(group, today(), "_Test Item")["item"], "_Test Item")
