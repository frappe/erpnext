# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import json

import frappe
from frappe.utils import flt

from erpnext.stock.dashboard_chart_source.stock_value_by_item_group.stock_value_by_item_group import (
	get,
	get_stock_value_by_item_group,
)
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.tests.permission_test_utils import as_user, make_fenced_user
from erpnext.tests.utils import ERPNextTestSuite

STOCK_USER = "test_stock_value_by_item_group_user@example.com"
ROOT_GROUP = "_Test SVBIG Root"
OUTSIDE_GROUP = "_Test SVBIG Outside"
WAREHOUSE = "Stores - _TC"
GROUP_VALUES = {
	"_Test SVBIG 01": [400, 500],
	"_Test SVBIG 02": [800],
	"_Test SVBIG 03": [700],
	"_Test SVBIG 04": [600],
	"_Test SVBIG 05": [500],
	"_Test SVBIG 06": [400],
	"_Test SVBIG 07": [300],
	"_Test SVBIG 08": [200],
	"_Test SVBIG 09": [0],
	"_Test SVBIG 10": [-10],
	"_Test SVBIG 11": [-20],
	"_Test SVBIG 12": [-30],
}


class TestStockValueByItemGroup(ERPNextTestSuite):
	def setUp(self):
		self.make_item_group(ROOT_GROUP, "All Item Groups", 1)
		self.make_item_group(OUTSIDE_GROUP, "All Item Groups", 0)
		self.make_stock(OUTSIDE_GROUP, 0, 10000)
		for item_group, values in GROUP_VALUES.items():
			self.make_item_group(item_group, ROOT_GROUP, 0)
			for idx, value in enumerate(values):
				self.make_stock(item_group, idx, value)

		frappe.db.sql(
			"""insert into `tabBin` (name, item_code, warehouse, stock_value, creation, modified)
			values ('_Test SVBIG Orphan Bin', '_Test SVBIG Missing Item', %s, 5000, now(), now())""",
			WAREHOUSE,
		)

	def make_item_group(self, item_group, parent, is_group):
		frappe.get_doc(
			{
				"doctype": "Item Group",
				"item_group_name": item_group,
				"parent_item_group": parent,
				"is_group": is_group,
			}
		).insert(ignore_permissions=True)

	def make_stock(self, item_group, idx, value):
		item_code = f"{item_group} Item {idx}"
		make_item(item_code, {"item_group": item_group, "is_stock_item": 1, "stock_uom": "Nos"})
		bin_name = frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": WAREHOUSE})
		if not bin_name:
			bin_name = (
				frappe.get_doc({"doctype": "Bin", "item_code": item_code, "warehouse": WAREHOUSE})
				.insert(ignore_permissions=True)
				.name
			)
		frappe.db.set_value("Bin", bin_name, "stock_value", value, update_modified=False)
		return item_code

	def get_values_as(self, user_permissions, company="_Test Company"):
		with as_user(make_fenced_user(STOCK_USER, ["Stock User"], user_permissions)):
			labels, values = get_stock_value_by_item_group(company)
		return labels, self.get_float_values(values)

	def get_upstream_result(self, company):
		labels = []
		values = []
		for row in frappe.db.sql(
			"""select item.item_group, sum(bin.stock_value) as stock_value
			from `tabBin` bin
			inner join `tabItem` item on bin.item_code = item.name
			where bin.warehouse in (
				select name from `tabWarehouse` where company = %s and is_group = 0
			)
			group by item.item_group
			order by sum(bin.stock_value) desc
			limit 10""",
			company,
			as_dict=True,
		):
			if not row.stock_value:
				continue
			labels.append(row.item_group)
			values.append(flt(row.stock_value))
		return labels, values

	def get_float_values(self, values):
		floats = []
		for value in values:
			floats.append(flt(value))
		return floats

	def test_item_group_fence_keeps_the_aggregation(self):
		labels, values = self.get_values_as([("Item Group", ROOT_GROUP)])

		self.assertEqual(
			labels,
			[
				"_Test SVBIG 01",
				"_Test SVBIG 02",
				"_Test SVBIG 03",
				"_Test SVBIG 04",
				"_Test SVBIG 05",
				"_Test SVBIG 06",
				"_Test SVBIG 07",
				"_Test SVBIG 08",
				"_Test SVBIG 10",
			],
		)
		self.assertEqual(values, [900.0, 800.0, 700.0, 600.0, 500.0, 400.0, 300.0, 200.0, -10.0])

	def test_item_fence_hides_other_items(self):
		labels, values = self.get_values_as([("Item", "_Test SVBIG 01 Item 0")])

		self.assertEqual(labels, ["_Test SVBIG 01"])
		self.assertEqual(values, [400.0])

	def test_company_fence_returns_nothing_for_another_company(self):
		fence = [("Company", "_Test Company")]

		self.assertEqual(self.get_values_as(fence, "_Test Company 1"), ([], []))
		self.assertIn(OUTSIDE_GROUP, self.get_values_as(fence)[0])

	def test_chart_get_applies_the_fence(self):
		with as_user(make_fenced_user(STOCK_USER, ["Stock User"], [("Item", "_Test SVBIG 01 Item 0")])):
			result = get(
				chart_name="Stock Value by Item Group",
				filters=json.dumps({"company": "_Test Company"}),
			)

		self.assertEqual(result["labels"], ["_Test SVBIG 01"])
		self.assertEqual(self.get_float_values(result["datasets"][0]["values"]), [400.0])

	def test_unfenced_stock_user_matches_the_upstream_query(self):
		self.assertNotIn(OUTSIDE_GROUP, self.get_values_as([("Item Group", ROOT_GROUP)])[0])

		labels, values = self.get_values_as([])
		expected_labels, expected_values = self.get_upstream_result("_Test Company")

		self.assertEqual(labels, expected_labels)
		self.assertEqual(values, expected_values)
		self.assertIn(OUTSIDE_GROUP, labels)
		self.assertNotIn(None, labels)
