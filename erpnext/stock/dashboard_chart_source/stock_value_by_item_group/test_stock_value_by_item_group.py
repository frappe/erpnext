import frappe

from erpnext.stock.dashboard_chart_source.stock_value_by_item_group.stock_value_by_item_group import get
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.tests.permission_test_utils import (
	as_user,
	assert_refused,
	make_company_fenced_user,
	make_fenced_user,
	malformed_names,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestStockValueByItemGroup(ERPNextTestSuite):
	def make_grouped_stock(self, item_code, item_group, rate):
		if not frappe.db.exists("Item Group", item_group):
			frappe.get_doc(
				{
					"doctype": "Item Group",
					"item_group_name": item_group,
					"parent_item_group": "All Item Groups",
				}
			).insert()
		make_item(item_code, {"item_group": item_group, "is_stock_item": 1})
		make_stock_entry(item_code=item_code, target="_Test Warehouse - _TC", qty=1, rate=rate)

	def chart(self, company):
		return get(chart_name="Stock Value by Item Group", filters={"company": company}, no_cache=1)

	def test_item_fence_limits_the_item_groups(self):
		self.make_grouped_stock("UP Chart Item A", "UP Chart Group A", 7000)
		self.make_grouped_stock("UP Chart Item B", "UP Chart Group B", 6000)
		fenced = make_fenced_user("chart-fenced@example.com", ["Stock User"], [("Item", "UP Chart Item A")])
		with as_user(fenced):
			labels = self.chart("_Test Company")["labels"]
		self.assertIn("UP Chart Group A", labels)
		self.assertNotIn("UP Chart Group B", labels)
		unfenced = make_fenced_user("chart-unfenced@example.com", ["Stock User"])
		with as_user(unfenced):
			labels = self.chart("_Test Company")["labels"]
		self.assertIn("UP Chart Group A", labels)
		self.assertIn("UP Chart Group B", labels)

	def test_company_fence_filters_and_malformed_company_yields_nothing(self):
		self.make_grouped_stock("UP Chart Item A", "UP Chart Group A", 7000)
		fenced = make_company_fenced_user("chart-fenced@example.com", ["Stock User"], "_Test Company 1")
		with as_user(fenced):
			self.assertEqual(self.chart("_Test Company")["labels"], [])
			for name in malformed_names():
				self.assertEqual(self.chart(name)["labels"], [])
		unfenced = make_fenced_user("chart-unfenced@example.com", ["Stock User"])
		with as_user(unfenced):
			self.assertIn("UP Chart Group A", self.chart("_Test Company")["labels"])
			for name in malformed_names():
				self.assertEqual(self.chart(name)["labels"], [])
