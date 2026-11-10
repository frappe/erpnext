# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.core.doctype.user_permission.test_user_permission import create_user
from frappe.permissions import add_user_permission
from frappe.utils import add_days, today

from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
from erpnext.manufacturing.doctype.work_order.mapper import make_stock_entry
from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
from erpnext.manufacturing.report.work_order_summary.work_order_summary import execute
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry import test_stock_entry
from erpnext.tests.utils import ERPNextTestSuite


class TestWorkOrderSummary(ERPNextTestSuite):
	def run_report(self, **extra):
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"from_date": add_days(today(), -1),
				"to_date": today(),
			}
		)
		filters.update(extra)
		return execute(filters)[1]

	def test_work_order_appears_with_expected_fields(self):
		wo = make_wo_order_test_record(production_item="_Test FG Item", qty=10, company="_Test Company")

		rows = {row["name"]: row for row in self.run_report()}
		self.assertIn(wo.name, rows)

		row = rows[wo.name]
		self.assertEqual(row["production_item"], "_Test FG Item")
		self.assertEqual(row["qty"], 10)
		self.assertEqual(row["produced_qty"], 0)
		self.assertEqual(row["status"], "Not Started")

	def test_status_filter_excludes_other_statuses(self):
		wo = make_wo_order_test_record(production_item="_Test FG Item", qty=10, company="_Test Company")
		self.assertEqual(wo.status, "Not Started")

		# A "Completed" filter must not return a "Not Started" work order.
		names = {row["name"] for row in self.run_report(status="Completed")}
		self.assertNotIn(wo.name, names)

		# The matching status still returns it.
		names = {row["name"] for row in self.run_report(status="Not Started")}
		self.assertIn(wo.name, names)

	def test_date_range_excludes_work_order_outside_window(self):
		wo = make_wo_order_test_record(production_item="_Test FG Item", qty=10, company="_Test Company")

		# A window entirely in the past cannot contain a WO created today.
		names = {
			row["name"]
			for row in self.run_report(from_date=add_days(today(), -10), to_date=add_days(today(), -5))
		}
		self.assertNotIn(wo.name, names)

		# A window that includes today does contain it.
		names = {row["name"] for row in self.run_report()}
		self.assertIn(wo.name, names)

	def test_work_order_planned_for_later_is_listed(self):
		wo = make_wo_order_test_record(
			production_item="_Test FG Item",
			qty=10,
			company="_Test Company",
			planned_start_date=add_days(today(), 5),
		)

		rows = {row["name"]: row for row in self.run_report(to_date=add_days(today(), 30))}

		self.assertIn(wo.name, rows)
		self.assertEqual(rows[wo.name]["age"], 0)

	def test_work_order_ending_later_on_the_to_date_is_listed(self):
		wo = make_wo_order_test_record(
			production_item="_Test FG Item",
			qty=10,
			company="_Test Company",
			planned_start_date=f"{today()} 08:00:00",
		)
		wo.db_set("planned_end_date", f"{today()} 18:00:00")

		names = {row["name"] for row in self.run_report(based_on="Planned Date", from_date=today())}

		self.assertIn(wo.name, names)

	def test_chart_counts_only_permitted_work_orders(self):
		make_wo_order_test_record(production_item="_Test FG Item", qty=10, company="_Test Company")
		make_wo_order_test_record(production_item="_Test FG Item 2", qty=10, company="_Test Company")
		user = create_user("work-order-summary-user@example.com", "Manufacturing User")
		add_user_permission("Item", "_Test FG Item", user.name)

		with self.set_user(user.name):
			_columns, data, _message, chart = execute(
				frappe._dict(
					{
						"company": "_Test Company",
						"from_date": add_days(today(), -1),
						"to_date": today(),
						"charts_based_on": "Status",
					}
				)
			)

		self.assertEqual({row.production_item for row in data}, {"_Test FG Item"})
		self.assertEqual(sum(chart["data"]["datasets"][0]["values"]), len(data))

	def test_age_chart_puts_new_work_orders_in_the_first_bucket(self):
		wo = make_wo_order_test_record(production_item="_Test FG Item", qty=10, company="_Test Company")

		_columns, data, _message, chart = execute(
			frappe._dict(
				{
					"company": "_Test Company",
					"from_date": add_days(today(), -1),
					"to_date": today(),
					"production_item": ["_Test FG Item"],
					"status": "Not Started",
					"charts_based_on": "Age",
				}
			)
		)

		self.assertIn(wo.name, {row.name for row in data})
		self.assertEqual(chart["data"]["datasets"][0]["values"][3], 0)
		self.assertEqual(chart["data"]["datasets"][0]["values"][0], len(data))

	def test_pending_qty_by_status_and_process_loss(self):
		from erpnext.manufacturing.report.work_order_summary.work_order_summary import get_pending_qty

		cases = {
			"In Process": 3,
			"Not Started": 3,
			"Closed": 0,
			"Stopped": 0,
			"Completed": 0,
		}
		for status, expected in cases.items():
			order = frappe._dict(status=status, qty=10, produced_qty=5, process_loss_qty=2)
			self.assertEqual(get_pending_qty(order), expected, status)

	def test_quantity_chart_has_nothing_pending_for_finished_orders(self):
		material = make_item(properties={"is_stock_item": 1, "valuation_rate": 10}).name
		fg_item = make_item(properties={"is_stock_item": 1}).name
		bom = make_bom(item=fg_item, raw_materials=[material])
		test_stock_entry.make_stock_entry(
			item_code=material, target="_Test Warehouse - _TC", qty=2, basic_rate=10
		)
		wo = make_wo_order_test_record(
			item=fg_item, bom_no=bom.name, qty=2, source_warehouse="_Test Warehouse - _TC", skip_transfer=1
		)
		manufacture = frappe.get_doc(make_stock_entry(wo.name, "Manufacture", 2))
		for row in manufacture.items:
			if row.is_finished_item:
				row.qty = 1
		manufacture.submit()
		wo.reload()
		self.assertEqual((wo.status, wo.produced_qty, wo.process_loss_qty), ("Completed", 1, 1))

		_columns, _data, _message, chart = execute(
			frappe._dict(
				{
					"company": "_Test Company",
					"from_date": add_days(today(), -1),
					"to_date": today(),
					"production_item": [fg_item],
					"charts_based_on": "Quantity",
				}
			)
		)

		pending, completed = (dataset["values"] for dataset in chart["data"]["datasets"])
		self.assertEqual((sum(pending), sum(completed)), (0, 1))
