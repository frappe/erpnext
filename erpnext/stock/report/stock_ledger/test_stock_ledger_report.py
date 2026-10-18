# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.core.doctype.user_permission.test_user_permission import create_user
from frappe.utils import add_days, today

from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.stock_ledger.stock_ledger import execute
from erpnext.stock.serial_batch_bundle import get_serial_nos_from_bundle
from erpnext.tests.utils import ERPNextTestSuite

WAREHOUSE = "Stores - _TC"


class TestStockLedgerReport(ERPNextTestSuite):
	"""Correctness tests for the Stock Ledger report.

	A shared `make_movements`/`run` pair keeps each test small without persisting
	any data: movements are created per test and rolled back, while the report runs
	read-only. Tests reuse bootstrap items and transact in `Stores - _TC`, which
	starts clean (zero balance) for these items.
	"""

	def make_movements(self, item_code, movements):
		for movement in movements:
			make_stock_entry(item_code=item_code, **movement)

	def run_report(self, item_code, from_date=None, to_date=None):
		filters = frappe._dict(
			company="_Test Company",
			from_date=from_date or add_days(today(), -1),
			to_date=to_date or today(),
			item_code=[item_code],
			warehouse=WAREHOUSE,
		)
		return list(execute(filters)[1])

	def test_in_out_quantities_and_running_balance(self):
		item = "_Test Item"
		self.make_movements(
			item,
			[
				{"qty": 10, "to_warehouse": WAREHOUSE, "basic_rate": 100},
				{"qty": 4, "from_warehouse": WAREHOUSE},
			],
		)

		rows = self.run_report(item)
		receipt = next(row for row in rows if row.get("in_qty"))
		issue = next(row for row in rows if row.get("out_qty"))

		self.assertEqual(receipt["in_qty"], 10)
		self.assertEqual(receipt["qty_after_transaction"], 10)
		self.assertEqual(issue["out_qty"], -4)
		self.assertEqual(issue["qty_after_transaction"], 6)

	def test_opening_balance_reflects_movements_before_from_date(self):
		item = "_Test Item"
		self.make_movements(
			item,
			[
				{
					"qty": 10,
					"to_warehouse": WAREHOUSE,
					"basic_rate": 100,
					"posting_date": add_days(today(), -10),
				},
				{"qty": 4, "from_warehouse": WAREHOUSE, "posting_date": today()},
			],
		)

		rows = self.run_report(item, from_date=add_days(today(), -5), to_date=today())

		# the receipt predates the range, so it surfaces as the opening balance
		self.assertEqual(rows[0]["item_code"], "'Opening'")
		self.assertEqual(rows[0]["qty_after_transaction"], 10)

		# the in-range issue draws down from the opening balance
		issue = next(row for row in rows if row.get("out_qty"))
		self.assertEqual(issue["qty_after_transaction"], 6)

	def test_stock_user_can_view_rows_with_serial_nos_as_text(self):
		item = "_Test Serialized Item With Series"
		entry = make_stock_entry(item_code=item, qty=1, to_warehouse=WAREHOUSE, basic_rate=100)
		serial_no = get_serial_nos_from_bundle(entry.items[0].serial_and_batch_bundle)[0]
		frappe.db.set_value("Stock Ledger Entry", {"voucher_no": entry.name}, "serial_no", serial_no)

		with self.set_user(create_user("_test_stock_ledger_user@example.com", "Stock User").name):
			rows = self.run_report(item)

		self.assertIn(entry.name, [row.get("voucher_no") for row in rows])

	def test_filters_to_requested_item_only(self):
		item_a = "_Test Item"
		item_b = "_Test Item 2"
		self.make_movements(item_a, [{"qty": 5, "to_warehouse": WAREHOUSE, "basic_rate": 100}])
		self.make_movements(item_b, [{"qty": 7, "to_warehouse": WAREHOUSE, "basic_rate": 100}])

		rows = self.run_report(item_a)
		item_codes = {row["item_code"] for row in rows if row.get("voucher_no")}
		self.assertEqual(item_codes, {item_a})

	def test_multi_item_opening_balance_with_and_without_transactions(self):
		item_a = "_Test Item"
		item_b = "_Test Item 2"
		self.make_movements(
			item_a,
			[
				{
					"qty": 10,
					"to_warehouse": WAREHOUSE,
					"basic_rate": 100,
					"posting_date": add_days(today(), -10),
				}
			],
		)
		self.make_movements(
			item_b,
			[{"qty": 5, "to_warehouse": WAREHOUSE, "basic_rate": 50, "posting_date": add_days(today(), -10)}],
		)
		self.make_movements(
			item_a,
			[{"qty": 2, "from_warehouse": WAREHOUSE, "posting_date": today()}],
		)

		filters = frappe._dict(
			company="_Test Company",
			from_date=add_days(today(), -5),
			to_date=today(),
			item_code=[item_a, item_b],
			warehouse=WAREHOUSE,
		)
		columns, rows = execute(filters)

		opening_rows = [row for row in rows if row.get("item_code") == "'Opening'"]
		self.assertEqual(len(opening_rows), 1)
		self.assertEqual(opening_rows[0]["qty_after_transaction"], 15)

	def test_multi_warehouse_opening_balance_aggregation(self):
		item = "_Test Item"
		warehouse_1 = "Stores - _TC"
		warehouse_2 = "Finished Goods - _TC"

		self.make_movements(
			item,
			[
				{
					"qty": 10,
					"to_warehouse": warehouse_1,
					"basic_rate": 100,
					"posting_date": add_days(today(), -10),
				},
				{
					"qty": 20,
					"to_warehouse": warehouse_2,
					"basic_rate": 100,
					"posting_date": add_days(today(), -10),
				},
			],
		)

		filters = frappe._dict(
			company="_Test Company",
			from_date=add_days(today(), -5),
			to_date=today(),
			item_code=[item],
			warehouse=[warehouse_1, warehouse_2],
		)
		columns, rows = execute(filters)

		opening_rows = [row for row in rows if row.get("item_code") == "'Opening'"]
		self.assertEqual(len(opening_rows), 1)
		self.assertEqual(opening_rows[0]["qty_after_transaction"], 30)

	def test_opening_stock_reconciliation_on_from_date_non_midnight_time(self):
		from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation import (
			create_stock_reconciliation,
		)

		item = "_Test Item"
		from_date = today()

		sr = create_stock_reconciliation(
			item_code=item,
			warehouse=WAREHOUSE,
			qty=25,
			rate=100,
			posting_date=from_date,
			posting_time="10:30:00",
			purpose="Opening Stock",
			do_not_submit=False,
		)

		filters = frappe._dict(
			company="_Test Company",
			from_date=from_date,
			to_date=from_date,
			item_code=[item],
			warehouse=WAREHOUSE,
		)
		columns, rows = execute(filters)

		opening_rows = [row for row in rows if row.get("item_code") == "'Opening'"]
		self.assertEqual(len(opening_rows), 1)
		self.assertEqual(opening_rows[0]["qty_after_transaction"], 25)

		# Ensure the Opening Stock Reconciliation is not duplicated in detail transaction rows
		reco_rows = [row for row in rows if row.get("voucher_no") == sr.name]
		self.assertEqual(len(reco_rows), 0)

	def test_backdated_sle_independent_maxima_handling(self):
		item = "_Test Item"
		# Entry 1: Later posting date (2026-07-20), created first
		self.make_movements(
			item,
			[
				{
					"qty": 10,
					"to_warehouse": WAREHOUSE,
					"basic_rate": 100,
					"posting_date": add_days(today(), -10),
				}
			],
		)
		# Entry 2: Backdated posting date (2026-07-15), created LATER
		self.make_movements(
			item,
			[
				{
					"qty": 5,
					"to_warehouse": WAREHOUSE,
					"basic_rate": 100,
					"posting_date": add_days(today(), -15),
				}
			],
		)

		filters = frappe._dict(
			company="_Test Company",
			from_date=add_days(today(), -5),
			to_date=today(),
			item_code=[item],
			warehouse=WAREHOUSE,
		)
		columns, rows = execute(filters)

		opening_rows = [row for row in rows if row.get("item_code") == "'Opening'"]
		self.assertEqual(len(opening_rows), 1)
		# Should correctly pick the latest posting date entry (15 Qty) despite backdated creation order
		self.assertEqual(opening_rows[0]["qty_after_transaction"], 15)

	def test_filtered_opening_balance_does_not_pick_excluded_creation_entry(self):
		item = "_Test Item"
		posting_date = add_days(today(), -10)
		posting_time = "09:00:00"

		included_entry = make_stock_entry(
			item_code=item,
			qty=10,
			to_warehouse=WAREHOUSE,
			basic_rate=100,
			posting_date=posting_date,
			posting_time=posting_time,
		)
		make_stock_entry(
			item_code=item,
			qty=50,
			to_warehouse=WAREHOUSE,
			basic_rate=100,
			posting_date=posting_date,
			posting_time=posting_time,
		)

		filters = frappe._dict(
			company="_Test Company",
			from_date=add_days(today(), -5),
			to_date=today(),
			item_code=[item],
			warehouse=WAREHOUSE,
			voucher_no=included_entry.name,
		)
		columns, rows = execute(filters)

		opening_rows = [row for row in rows if row.get("item_code") == "'Opening'"]
		self.assertEqual(len(opening_rows), 1)
		self.assertEqual(opening_rows[0]["qty_after_transaction"], 10)

	def test_tied_creation_terminal_sle_is_not_summed_twice(self):
		item = "_Test Item"
		posting_date = add_days(today(), -10)
		posting_time = "09:00:00"

		stock_entry_1 = make_stock_entry(
			item_code=item,
			qty=10,
			to_warehouse=WAREHOUSE,
			basic_rate=100,
			posting_date=posting_date,
			posting_time=posting_time,
		)
		stock_entry_2 = make_stock_entry(
			item_code=item,
			qty=5,
			to_warehouse=WAREHOUSE,
			basic_rate=100,
			posting_date=posting_date,
			posting_time=posting_time,
		)

		sle_rows = frappe.get_all(
			"Stock Ledger Entry",
			filters={
				"voucher_type": "Stock Entry",
				"voucher_no": ("in", [stock_entry_1.name, stock_entry_2.name]),
				"item_code": item,
				"warehouse": WAREHOUSE,
				"is_cancelled": 0,
			},
			fields=["name", "qty_after_transaction"],
			order_by="name desc",
		)
		self.assertEqual(len(sle_rows), 2)

		for sle in sle_rows:
			frappe.db.set_value(
				"Stock Ledger Entry",
				sle.name,
				"creation",
				"2026-01-01 00:00:00.000000",
				update_modified=False,
			)

		filters = frappe._dict(
			company="_Test Company",
			from_date=add_days(today(), -5),
			to_date=today(),
			item_code=[item],
			warehouse=WAREHOUSE,
		)
		columns, rows = execute(filters)

		opening_rows = [row for row in rows if row.get("item_code") == "'Opening'"]
		self.assertEqual(len(opening_rows), 1)
		self.assertEqual(opening_rows[0]["qty_after_transaction"], sle_rows[0].qty_after_transaction)
		self.assertNotEqual(
			opening_rows[0]["qty_after_transaction"],
			sum(sle.qty_after_transaction for sle in sle_rows),
		)

	def test_opening_row_keeps_its_balance_in_the_stock_uom(self):
		from erpnext.stock.doctype.item.test_item import make_item

		item = make_item(properties={"is_stock_item": 1, "stock_uom": "Nos"}).name
		make_stock_entry(
			item_code=item, to_warehouse=WAREHOUSE, qty=17, basic_rate=100, posting_date=add_days(today(), -3)
		)

		filters = frappe._dict(
			company="_Test Company",
			from_date=add_days(today(), -1),
			to_date=today(),
			item_code=[item],
			warehouse=WAREHOUSE,
			include_uom="Nos",
		)
		opening = execute(filters)[1][0]

		self.assertEqual(opening["qty_after_transaction_nos"], 17)

	def test_opening_of_a_warehouse_the_user_may_not_read_is_hidden(self):
		from frappe.permissions import add_user_permission

		item = "_Test Item"
		self.make_movements(
			item,
			[
				{
					"qty": 20,
					"to_warehouse": WAREHOUSE,
					"basic_rate": 100,
					"posting_date": add_days(today(), -5),
				}
			],
		)
		user = create_user("stock-ledger-opening@example.com", "Stock User")
		add_user_permission("Warehouse", "Finished Goods - _TC", user.name)

		with self.set_user(user.name):
			rows = self.run_report(item)

		self.assertEqual(rows, [])

	def test_batch_opening_includes_the_warehouses_of_a_group(self):
		from erpnext.stock.doctype.item.test_item import make_item

		item = make_item(properties={"is_stock_item": 1, "has_batch_no": 1}).name
		batch = frappe.get_doc(
			{"doctype": "Batch", "item": item, "batch_id": frappe.generate_hash(length=10)}
		).insert()
		self.make_movements(
			item,
			[
				{
					"qty": 10,
					"to_warehouse": WAREHOUSE,
					"basic_rate": 200,
					"batch_no": batch.name,
					"use_serial_batch_fields": 1,
					"posting_date": add_days(today(), -9),
				}
			],
		)

		filters = frappe._dict(
			company="_Test Company",
			from_date=add_days(today(), -5),
			to_date=today(),
			item_code=[item],
			batch_no=batch.name,
			warehouse=[frappe.db.get_value("Warehouse", WAREHOUSE, "parent_warehouse")],
		)
		rows = list(execute(filters)[1])

		self.assertEqual(rows[0]["qty_after_transaction"], 10)

	def test_project_filter_keeps_the_opening_without_a_warehouse(self):
		from erpnext.stock.doctype.item.test_item import make_item

		item = make_item(properties={"is_stock_item": 1}).name
		project = frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": frappe.generate_hash(length=10),
				"company": "_Test Company",
			}
		).insert()
		for qty, days in ((10, -10), (2, -2)):
			entry = make_stock_entry(
				item_code=item,
				to_warehouse=WAREHOUSE,
				qty=qty,
				basic_rate=100,
				posting_date=add_days(today(), days),
				do_not_submit=True,
			)
			entry.project = project.name
			for row in entry.items:
				row.project = project.name
			entry.save()
			entry.submit()

		filters = frappe._dict(
			company="_Test Company",
			from_date=add_days(today(), -5),
			to_date=today(),
			item_code=[item],
			project=project.name,
		)
		rows = list(execute(filters)[1])

		self.assertEqual([row["qty_after_transaction"] for row in rows], [10, 12])

	def test_include_uom_works_with_segregated_bundles(self):
		from erpnext.stock.doctype.item.test_item import make_item

		item = make_item(
			properties={
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "SLU-.#####",
				"stock_uom": "Nos",
				"uoms": [{"uom": "Box", "conversion_factor": 10}],
			}
		).name
		for _receipt in range(3):
			make_stock_entry(item_code=item, to_warehouse=WAREHOUSE, qty=10, basic_rate=100)

		filters = frappe._dict(
			company="_Test Company",
			from_date=add_days(today(), -1),
			to_date=today(),
			item_code=[item],
			warehouse=WAREHOUSE,
			include_uom="Box",
			segregate_serial_batch_bundle=1,
		)
		rows = list(execute(filters)[1])

		self.assertEqual([row.get("in_qty_box") for row in rows if row.get("in_qty")], [1, 1, 1])

	def test_opening_row_is_converted_to_the_include_uom(self):
		from erpnext.stock.doctype.item.test_item import make_item

		item = make_item(
			properties={
				"is_stock_item": 1,
				"stock_uom": "Nos",
				"uoms": [{"uom": "Box", "conversion_factor": 10}],
			}
		).name
		make_stock_entry(
			item_code=item, to_warehouse=WAREHOUSE, qty=17, basic_rate=100, posting_date=add_days(today(), -3)
		)

		filters = frappe._dict(
			company="_Test Company",
			from_date=add_days(today(), -1),
			to_date=today(),
			item_code=[item],
			warehouse=WAREHOUSE,
			include_uom="Box",
		)
		opening = execute(filters)[1][0]

		self.assertEqual(opening["qty_after_transaction_box"], 1.7)

	def test_reconciliation_first_in_the_range_shows_its_change(self):
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation import (
			create_stock_reconciliation,
		)

		item = make_item(properties={"is_stock_item": 1}).name
		make_stock_entry(
			item_code=item,
			to_warehouse=WAREHOUSE,
			qty=10,
			basic_rate=100,
			posting_date=add_days(today(), -10),
		)
		create_stock_reconciliation(
			item_code=item, warehouse=WAREHOUSE, qty=15, rate=100, posting_date=add_days(today(), -2)
		)

		rows = self.run_report(item, from_date=add_days(today(), -5))
		reconciliation = next(row for row in rows if row.get("voucher_type") == "Stock Reconciliation")

		self.assertEqual(reconciliation["in_qty"], 5)

	def test_batch_rows_show_the_batch_valuation_rate(self):
		from erpnext.stock.doctype.item.test_item import make_item

		item = make_item(properties={"is_stock_item": 1, "has_batch_no": 1}).name
		batches = [
			frappe.get_doc({"doctype": "Batch", "item": item, "batch_id": frappe.generate_hash(length=10)})
			.insert()
			.name
			for _batch in range(2)
		]
		for batch_no, rate in zip(batches, (100, 200), strict=True):
			make_stock_entry(
				item_code=item,
				to_warehouse=WAREHOUSE,
				qty=10,
				basic_rate=rate,
				batch_no=batch_no,
				use_serial_batch_fields=1,
			)
		make_stock_entry(
			item_code=item, from_warehouse=WAREHOUSE, qty=3, batch_no=batches[1], use_serial_batch_fields=1
		)

		for segregate in (0, 1):
			filters = frappe._dict(
				company="_Test Company",
				from_date=add_days(today(), -1),
				to_date=today(),
				item_code=[item],
				warehouse=WAREHOUSE,
				batch_no=batches[1],
				segregate_serial_batch_bundle=segregate,
			)
			rows = [row for row in execute(filters)[1] if row.get("voucher_no")]

			self.assertEqual([row["valuation_rate"] for row in rows], [200, 200], f"segregate={segregate}")

	def test_midnight_entry_on_from_date_is_not_in_the_opening(self):
		from erpnext.stock.doctype.item.test_item import make_item

		item = make_item(properties={"is_stock_item": 1}).name
		self.make_movements(
			item,
			[
				{
					"qty": 10,
					"to_warehouse": WAREHOUSE,
					"basic_rate": 100,
					"posting_date": add_days(today(), -20),
				},
				{
					"qty": 4,
					"to_warehouse": WAREHOUSE,
					"basic_rate": 100,
					"posting_date": add_days(today(), -5),
					"posting_time": "00:00:00",
				},
			],
		)

		rows = self.run_report(item, from_date=add_days(today(), -5))

		self.assertEqual([row["qty_after_transaction"] for row in rows], [10, 14])

	def test_reconciliation_after_opening_stock_on_from_date_shows_its_change(self):
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.stock_reconciliation.test_stock_reconciliation import (
			create_stock_reconciliation,
		)

		item = make_item(properties={"is_stock_item": 1}).name
		from_date = add_days(today(), -2)
		for qty, posting_time, purpose in ((25, "10:00:00", "Opening Stock"), (30, "12:00:00", None)):
			create_stock_reconciliation(
				item_code=item,
				warehouse=WAREHOUSE,
				qty=qty,
				rate=100,
				posting_date=from_date,
				posting_time=posting_time,
				purpose=purpose,
			)

		rows = self.run_report(item, from_date=from_date)
		reconciliation = next(row for row in rows if row.get("voucher_type") == "Stock Reconciliation")

		self.assertEqual(reconciliation["in_qty"], 5)

	def test_project_opening_counts_only_permitted_items(self):
		from frappe.permissions import add_user_permission

		from erpnext.stock.doctype.item.test_item import make_item

		items = [make_item(properties={"is_stock_item": 1}).name for _item in range(2)]
		project = frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": frappe.generate_hash(length=10),
				"company": "_Test Company",
			}
		).insert()
		for item, qty in zip(items, (4, 9), strict=True):
			entry = make_stock_entry(
				item_code=item,
				to_warehouse=WAREHOUSE,
				qty=qty,
				basic_rate=100,
				posting_date=add_days(today(), -10),
				do_not_submit=True,
			)
			entry.project = project.name
			for row in entry.items:
				row.project = project.name
			entry.save()
			entry.submit()

		user = create_user("stock-ledger-project-item@example.com", "Stock User")
		add_user_permission("Item", items[0], user.name)
		filters = frappe._dict(
			company="_Test Company",
			from_date=add_days(today(), -5),
			to_date=today(),
			project=project.name,
		)
		with self.set_user(user.name):
			rows = list(execute(filters)[1])

		self.assertEqual([row["qty_after_transaction"] for row in rows], [4])

	def test_item_group_filter_lists_only_permitted_items(self):
		from frappe.permissions import add_user_permission

		from erpnext.stock.report.stock_ledger.stock_ledger import get_items

		user = create_user("stock-ledger-item-group@example.com", "Stock User")
		add_user_permission("Item", "_Test Item", user.name)
		with self.set_user(user.name):
			items = get_items(frappe._dict(item_group="_Test Item Group"))

		self.assertEqual(items, ["_Test Item"])

	def test_project_opening_counts_only_permitted_warehouses(self):
		from frappe.permissions import add_user_permission

		from erpnext.stock.doctype.item.test_item import make_item

		item = make_item(properties={"is_stock_item": 1}).name
		project = frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": frappe.generate_hash(length=10),
				"company": "_Test Company",
			}
		).insert()
		for warehouse, qty in ((WAREHOUSE, 10), ("Finished Goods - _TC", 3)):
			entry = make_stock_entry(
				item_code=item,
				to_warehouse=warehouse,
				qty=qty,
				basic_rate=100,
				posting_date=add_days(today(), -10),
				do_not_submit=True,
			)
			entry.project = project.name
			for row in entry.items:
				row.project = project.name
			entry.save()
			entry.submit()

		user = create_user("stock-ledger-project@example.com", "Stock User")
		add_user_permission("Warehouse", "Finished Goods - _TC", user.name)
		filters = frappe._dict(
			company="_Test Company",
			from_date=add_days(today(), -5),
			to_date=today(),
			item_code=[item],
			project=project.name,
		)
		with self.set_user(user.name):
			rows = list(execute(filters)[1])

		self.assertEqual([row["qty_after_transaction"] for row in rows], [3])
