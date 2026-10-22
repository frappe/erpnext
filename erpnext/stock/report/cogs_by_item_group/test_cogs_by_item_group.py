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

	def test_rows_booked_to_another_account_are_not_cogs(self):
		cogs_group = make_item_group(f"_Test COGS Item Group {frappe.generate_hash(length=6)}")
		other_group = make_item_group(f"_Test COGS Item Group {frappe.generate_hash(length=6)}")
		items = [
			make_item(properties={"is_stock_item": 1, "item_group": group}).name
			for group in (cogs_group, other_group)
		]
		for item in items:
			make_stock_entry(
				item_code=item,
				to_warehouse="Stores - TCP1",
				qty=10,
				rate=100,
				company=COMPANY,
				posting_date="2026-06-01",
			)

		invoice = create_sales_invoice(
			item_code=items[0],
			qty=2,
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
			do_not_save=1,
		)
		invoice.append(
			"items",
			{
				**invoice.items[0].as_dict(),
				"name": None,
				"item_code": items[1],
				"expense_account": "Stock Adjustment - TCP1",
			},
		)
		invoice.insert()
		invoice.submit()

		data = self.run_report()
		values = {
			group: [row.cogs_debit for row in data if group in row.item_group]
			for group in (cogs_group, other_group)
		}
		self.assertEqual(values, {cogs_group: [200], other_group: []})

	def test_reconciliation_booked_to_cogs_is_counted(self):
		from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation import (
			create_stock_reconciliation,
		)

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
		create_stock_reconciliation(
			item_code=item,
			warehouse="Stores - TCP1",
			qty=7,
			rate=100,
			company=COMPANY,
			cost_center="Main - TCP1",
			expense_account="Cost of Goods Sold - TCP1",
			posting_date="2026-06-02",
		)

		data = self.run_report()

		self.assertEqual([row.cogs_debit for row in data if item_group in row.item_group], [300])


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
