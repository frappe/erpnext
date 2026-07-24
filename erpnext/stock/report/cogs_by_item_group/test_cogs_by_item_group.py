# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.cogs_by_item_group.cogs_by_item_group import execute
from erpnext.tests.utils import ERPNextTestSuite

COMPANY = "_Test Company with perpetual inventory"


class TestCogsByItemGroup(ERPNextTestSuite):
	def run_report(self, **extra) -> list:
		filters = frappe._dict(
			company=COMPANY,
			from_date="2026-01-01",
			to_date="2026-12-31",
		)
		filters.update(extra)
		return execute(filters)[1]

	def test_cogs_for_item_group(self):
		# A dedicated item group with a single item keeps `agg_value` scoped to this
		# test's COGS. The report sums COGS up the whole item-group tree keyed on the
		# company's default expense account, so a shared group would accumulate COGS
		# booked by any other test/fixture for the same company within the date range.
		# The group name is unique per run so items created by earlier runs (which
		# reuse a fixed group name) can't inflate the total either.
		item_group = make_item_group(f"_Test COGS Item Group {frappe.generate_hash(length=6)}")
		item = make_item(properties={"is_stock_item": 1, "item_group": item_group}).name

		make_stock_entry(
			item_code=item,
			to_warehouse="Stores - TCP1",
			qty=10,
			rate=100,
			company=COMPANY,
			posting_date="2026-06-01",
		)

		# A Sales Invoice with update_stock delivers the goods and books the COGS
		# against the company's default expense account, which the report keys on.
		create_sales_invoice(
			item_code=item,
			qty=4,
			rate=150,
			warehouse="Stores - TCP1",
			company=COMPANY,
			update_stock=1,
			cost_center="Main - TCP1",
			parent_cost_center="Main - TCP1",
			debit_to="Debtors - TCP1",
			income_account="Sales - TCP1",
			expense_account="Cost of Goods Sold - TCP1",
			posting_date="2026-06-02",
		)

		data = self.run_report()
		rows = [row for row in data if item_group in row.get("item_group")]
		self.assertTrue(rows, "No row found for the dedicated item group")
		# 4 units delivered at 100 valuation rate -> 400 COGS.
		self.assertEqual(rows[0].get("cogs_debit"), 400)


def make_item_group(name: str) -> str:
	if not frappe.db.exists("Item Group", name):
		frappe.get_doc(
			{
				"doctype": "Item Group",
				"item_group_name": name,
				"parent_item_group": "All Item Groups",
				"is_group": 0,
			}
		).insert()
	return name
