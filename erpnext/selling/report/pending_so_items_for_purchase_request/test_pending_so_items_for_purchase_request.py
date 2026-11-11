# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
import frappe.permissions
from frappe.utils import add_months, nowdate

from erpnext.selling.doctype.product_bundle.test_product_bundle import make_product_bundle
from erpnext.selling.doctype.sales_order.mapper import make_delivery_note, make_material_request
from erpnext.selling.doctype.sales_order.test_sales_order import create_dn_against_so, make_sales_order
from erpnext.selling.report.pending_so_items_for_purchase_request.pending_so_items_for_purchase_request import (
	execute,
)
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.tests.utils import ERPNextTestSuite


class TestPendingSOItemsForPurchaseRequest(ERPNextTestSuite):
	def test_result_for_partial_material_request(self):
		so = make_sales_order()
		mr = make_material_request(so.name)
		mr.items[0].qty = 4
		mr.schedule_date = add_months(nowdate(), 1)
		mr.submit()
		row = self.get_row(execute(), so.name)
		self.assertEqual(so.items[0].qty - mr.items[0].qty, row["pending_qty"])

	def test_result_for_so_item(self):
		so = make_sales_order()
		row = self.get_row(execute(), so.name)
		self.assertEqual(so.items[0].qty, row["pending_qty"])

	def test_delivered_qty_excluded_from_pending(self):
		so = make_sales_order(qty=10)
		create_dn_against_so(so.name, delivered_qty=5)
		row = self.get_row(execute(), so.name)
		self.assertEqual(5, row["delivered_qty"])
		self.assertEqual(5, row["pending_qty"])

	def test_bundle_request_does_not_clear_direct_line(self):
		item = make_item("_Test PSO Direct", {"is_stock_item": 1}).name
		bundle = make_item("_Test PSO Bundle", {"is_stock_item": 0, "is_sales_item": 1}).name
		make_product_bundle(bundle, [item], qty=2)

		so = make_sales_order(
			item_list=[
				{"item_code": item, "warehouse": "_Test Warehouse - _TC", "qty": 4, "rate": 100},
				{"item_code": bundle, "qty": 3, "rate": 100},
			]
		)

		mr = make_material_request(so.name)
		mr.items = [d for d in mr.items if d.packed_item]  # request only the bundle's components
		mr.schedule_date = add_months(nowdate(), 1)
		mr.submit()

		rows = [r for r in execute()[1] if r["sales_order_no"] == so.name and r["item_code"] == item]
		self.assertEqual(len(rows), 1)
		self.assertEqual(4, rows[0]["so_qty"])
		self.assertEqual(4, rows[0]["pending_qty"])

	def test_duplicated_bundle_request_counted(self):
		item = make_item("_Test PSO Dup Comp", {"is_stock_item": 1}).name
		bundle = make_item("_Test PSO Dup Bundle", {"is_stock_item": 0, "is_sales_item": 1}).name
		make_product_bundle(bundle, [item], qty=2)
		so = make_sales_order(
			item_list=[{"item_code": bundle, "warehouse": "_Test Warehouse - _TC", "qty": 3, "rate": 100}]
		)

		# a duplicated bundle request loses its packed_item link but keeps the Sales Order
		mr = make_material_request(so.name)
		for d in mr.items:
			d.packed_item = None
		mr.schedule_date = add_months(nowdate(), 1)
		mr.submit()

		rows = [r for r in execute()[1] if r["sales_order_no"] == so.name and r["item_code"] == item]
		self.assertEqual(rows, [])

	def test_disabled_bundle_still_shows_components(self):
		item = make_item("_Test PSO Disabled Comp", {"is_stock_item": 1}).name
		bundle = make_item("_Test PSO Disabled Bundle", {"is_stock_item": 0, "is_sales_item": 1}).name
		pb = make_product_bundle(bundle, [item], qty=2)
		so = make_sales_order(
			item_list=[{"item_code": bundle, "warehouse": "_Test Warehouse - _TC", "qty": 3, "rate": 100}]
		)

		frappe.db.set_value("Product Bundle", pb.name, "is_active", 0)

		codes = {r["item_code"] for r in execute()[1] if r["sales_order_no"] == so.name}
		self.assertIn(item, codes)
		self.assertNotIn(bundle, codes)

	def test_linkless_request_counted(self):
		# a duplicated/amended request keeps only the Sales Order link
		so = make_sales_order(qty=10)
		mr = make_material_request(so.name)
		mr.items = mr.items[:1]
		mr.items[0].qty = 4
		mr.items[0].sales_order_item = None
		mr.items[0].packed_item = None
		mr.schedule_date = add_months(nowdate(), 1)
		mr.submit()
		row = self.get_row(execute(), so.name)
		self.assertEqual(4, row["requested_qty"])
		self.assertEqual(6, row["pending_qty"])

	def test_repeated_item_lines_count_linkless_request_once(self):
		frappe.db.set_single_value("Selling Settings", "allow_multiple_items", 1)
		item = make_item("_Test PSO Repeat", {"is_stock_item": 1}).name
		so = make_sales_order(
			item_list=[
				{"item_code": item, "warehouse": "_Test Warehouse - _TC", "qty": 10, "rate": 100},
				{"item_code": item, "warehouse": "_Test Warehouse - _TC", "qty": 10, "rate": 100},
			]
		)
		self.assertEqual(len(so.items), 2)

		mr = make_material_request(so.name)
		mr.items = mr.items[:1]
		mr.items[0].qty = 4
		mr.items[0].sales_order_item = None
		mr.items[0].packed_item = None
		mr.schedule_date = add_months(nowdate(), 1)
		mr.submit()

		rows = [r for r in execute()[1] if r["sales_order_no"] == so.name and r["item_code"] == item]
		self.assertEqual(4, sum(r["requested_qty"] for r in rows))
		self.assertEqual(16, sum(r["pending_qty"] for r in rows))

	def test_untouched_line_stays_pending(self):
		frappe.db.set_single_value("Selling Settings", "allow_multiple_items", 1)
		item = make_item("_Test PSO Uneven", {"is_stock_item": 1}).name
		so = make_sales_order(
			item_list=[
				{"item_code": item, "warehouse": "_Test Warehouse - _TC", "qty": 10, "rate": 100},
				{"item_code": item, "warehouse": "_Test Warehouse - _TC", "qty": 10, "rate": 100},
			]
		)
		self.assertEqual(len(so.items), 2)

		# fully request and deliver the first line only; the second line is untouched
		mr = make_material_request(so.name)
		mr.items = [d for d in mr.items if d.sales_order_item == so.items[0].name]
		mr.items[0].qty = 10
		mr.schedule_date = add_months(nowdate(), 1)
		mr.submit()

		frappe.db.set_single_value("Stock Settings", "allow_negative_stock", 1)
		dn = make_delivery_note(so.name)
		dn.items = [d for d in dn.items if d.so_detail == so.items[0].name]
		dn.items[0].qty = 10
		dn.insert()
		dn.submit()

		rows = [r for r in execute()[1] if r["sales_order_no"] == so.name and r["item_code"] == item]
		self.assertEqual(10, sum(r["pending_qty"] for r in rows))

	def test_user_permission_restricts_rows(self):
		item = make_item("_Test PSO Perm", {"is_stock_item": 0, "is_sales_item": 1}).name
		make_sales_order(customer="_Test Customer 1", item_code=item, qty=2, rate=100)
		make_sales_order(customer="_Test Customer 2", item_code=item, qty=3, rate=100)

		user = "_test_pso_perm@example.com"
		if not frappe.db.exists("User", user):
			u = frappe.new_doc("User")
			u.email = user
			u.first_name = "PSO Perm"
			u.append("roles", {"role": "Sales User"})
			u.insert()
		frappe.permissions.add_user_permission("Customer", "_Test Customer 1", user)

		frappe.set_user(user)
		try:
			data = execute()[1]
		finally:
			frappe.set_user("Administrator")

		customers = {r["customer"] for r in data}
		self.assertIn("_Test Customer 1", customers)
		self.assertNotIn("_Test Customer 2", customers)

	def get_row(self, report, sales_order):
		rows = [r for r in report[1] if r["sales_order_no"] == sales_order]
		self.assertTrue(rows, f"no report row for {sales_order}")
		return rows[0]
