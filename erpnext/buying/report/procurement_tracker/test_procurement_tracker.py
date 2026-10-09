# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe.utils import add_days, getdate, nowdate

from erpnext.buying.doctype.purchase_order.mapper import make_purchase_invoice
from erpnext.buying.doctype.purchase_order.test_purchase_order import (
	create_pr_against_po,
	create_purchase_order,
)
from erpnext.buying.report.procurement_tracker.procurement_tracker import execute
from erpnext.controllers.tests.test_subcontracting_controller import (
	make_bom_for_subcontracted_items,
	make_raw_materials,
	make_service_items,
	make_subcontracted_items,
)
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.material_request.mapper import make_purchase_order
from erpnext.stock.doctype.material_request.test_material_request import (
	make_material_request,
	make_material_request_for_items,
)
from erpnext.stock.doctype.purchase_receipt.mapper import make_purchase_invoice as make_invoice_from_receipt
from erpnext.tests.utils import ERPNextTestSuite


class TestProcurementTracker(ERPNextTestSuite):
	def run_report(self, **filters):
		return execute({"company": "_Test Company", **filters})[1]

	def test_report_executes_and_lists_po(self):
		po = create_purchase_order(company="_Test Company")

		self.assertIn(po.name, {row.get("purchase_order") for row in self.run_report()})

	def make_priced_request(self, **args):
		mr = make_material_request(do_not_submit=True, **args)
		mr.items[0].update({"rate": 90, "amount": 900})
		mr.submit()
		return mr

	def test_request_item_ordered_on_two_lines_is_estimated_once(self):
		mr = self.make_priced_request()
		po = make_purchase_order(mr.name)
		po.supplier = "_Test Supplier"
		po.items[0].qty = 4
		po.append("items", {**po.items[0].as_dict(no_default_fields=True), "qty": 6})
		with self.change_settings("Buying Settings", {"allow_multiple_items": 1}):
			po.submit()

		rows = [row for row in self.run_report() if row.get("purchase_order") == po.name]
		self.assertCountEqual([row["estimated_cost"] for row in rows], [360, 540])
		self.assertEqual(sum(row["estimated_cost"] for row in rows), mr.items[0].amount)

	def test_subcontracted_estimate_is_shared_by_finished_good_qty(self):
		make_subcontracted_items()
		make_raw_materials()
		make_service_items()
		make_bom_for_subcontracted_items()
		mr = self.make_priced_request(
			material_request_type="Subcontracting", item_code="Subcontracted Item SA7"
		)
		orders = [
			create_purchase_order(
				is_subcontracted=1,
				supplier_warehouse="_Test Warehouse 1 - _TC",
				rm_items=[
					{
						"item_code": "Subcontracted Service Item 7",
						"warehouse": "_Test Warehouse - _TC",
						"qty": 1,
						"rate": 100,
						"fg_item": "Subcontracted Item SA7",
						"fg_item_qty": fg_item_qty,
						"material_request": mr.name,
						"material_request_item": mr.items[0].name,
					}
				],
			).name
			for fg_item_qty in (4, 6)
		]

		rows = {row.get("purchase_order"): row["estimated_cost"] for row in self.run_report()}
		self.assertEqual([rows[order] for order in orders], [360, 540])

	def test_filtered_out_order_keeps_its_share_of_the_estimate(self):
		mr = self.make_priced_request()
		for qty, transaction_date in ((4, add_days(nowdate(), -1)), (6, nowdate())):
			po = make_purchase_order(mr.name)
			po.update({"supplier": "_Test Supplier", "transaction_date": transaction_date})
			po.items[0].qty = qty
			po.submit()

		data = self.run_report(from_date=nowdate(), to_date=nowdate())
		rows = [row for row in data if row.get("material_request_no") == mr.name]
		self.assertEqual([(row["purchase_order"], row["estimated_cost"]) for row in rows], [(po.name, 540)])

	def test_each_po_line_is_a_row(self):
		second_item = make_item("_Test Procurement Tracker Item", {"is_stock_item": 1}).name
		po = create_purchase_order(do_not_submit=True)
		po.append(
			"items",
			{
				"item_code": second_item,
				"warehouse": "_Test Warehouse - _TC",
				"qty": 5,
				"rate": 100,
				"schedule_date": add_days(nowdate(), 1),
			},
		)
		po.submit()

		rows = [row for row in self.run_report() if row.get("purchase_order") == po.name]
		self.assertCountEqual(
			[(row["item_code"], row["quantity"]) for row in rows],
			[(item.item_code, item.qty) for item in po.items],
		)

	def test_actual_cost_adds_up_every_invoice(self):
		po = create_purchase_order(qty=10, rate=90)
		for qty in (4, 3):
			invoice = make_purchase_invoice(po.name)
			invoice.items[0].qty = qty
			invoice.submit()

		row = next(row for row in self.run_report() if row.get("purchase_order") == po.name)
		self.assertEqual(row["actual_cost"], 630)

	def test_unordered_rows_of_a_partly_ordered_request_are_listed(self):
		mr = make_material_request_for_items(["_Test Item", "_Test Item Home Desktop 100"])
		po = make_purchase_order(mr.name)
		po.supplier = "_Test Supplier"
		po.items = po.items[:1]
		po.submit()

		rows = [row for row in self.run_report() if row.get("material_request_no") == mr.name]
		self.assertCountEqual(
			[(row["item_code"], row.get("purchase_order")) for row in rows],
			[("_Test Item", po.name), ("_Test Item Home Desktop 100", None)],
		)

	def test_billed_receipt_keeps_actual_delivery_date(self):
		po = create_purchase_order(qty=10)
		receipt = create_pr_against_po(po.name, received_qty=5)
		make_invoice_from_receipt(receipt.name).submit()

		row = next(row for row in self.run_report() if row.get("purchase_order") == po.name)
		self.assertEqual(row["actual_delivery_date"], getdate(receipt.posting_date))

	def make_project(self):
		return frappe.get_doc(
			{"doctype": "Project", "project_name": "_Test Procurement Tracker", "company": "_Test Company"}
		).insert()

	def test_cost_center_and_project_filters_both_apply(self):
		project = self.make_project()
		with_project = create_purchase_order(do_not_submit=True)
		with_project.items[0].project = project.name
		with_project.submit()
		without_project = create_purchase_order()

		rows = self.run_report(cost_center=with_project.items[0].cost_center, project=project.name)
		orders = {row.get("purchase_order") for row in rows}
		self.assertIn(with_project.name, orders)
		self.assertNotIn(without_project.name, orders)

	def test_filters_do_not_drop_the_estimate_of_a_linked_request(self):
		project = self.make_project()
		mr = self.make_priced_request()
		po = make_purchase_order(mr.name)
		po.supplier = "_Test Supplier"
		po.items[0].update({"cost_center": "_Test Cost Center 2 - _TC", "project": project.name})
		po.submit()

		rows = self.run_report(cost_center="_Test Cost Center 2 - _TC", project=project.name)
		row = next(row for row in rows if row.get("purchase_order") == po.name)
		self.assertEqual(row["estimated_cost"], 900)

	def test_transfer_request_is_not_listed(self):
		mr = make_material_request(
			material_request_type="Material Transfer", from_warehouse="_Test Warehouse 1 - _TC"
		)

		self.assertNotIn(mr.name, {row.get("material_request_no") for row in self.run_report()})

	def test_quantity_is_shown_in_its_order_unit(self):
		po = create_purchase_order(do_not_submit=True)
		po.items[0].update({"uom": "_Test UOM 1", "conversion_factor": 10})
		po.submit()

		row = next(row for row in self.run_report() if row.get("purchase_order") == po.name)
		self.assertEqual((row["quantity"], row["unit_of_measurement"]), (10, "_Test UOM 1"))

	def test_completed_and_closed_orders_are_shown_on_request(self):
		completed = create_purchase_order(qty=10)
		create_pr_against_po(completed.name, received_qty=10)
		make_purchase_invoice(completed.name).submit()
		closed = create_purchase_order()
		closed.update_status("Closed")

		orders = {row.get("purchase_order") for row in self.run_report()}
		self.assertNotIn(completed.name, orders)
		self.assertNotIn(closed.name, orders)

		rows = {row.get("purchase_order"): row for row in self.run_report(show_completed_orders=1)}
		self.assertEqual(rows[completed.name]["actual_cost"], 5000)
		self.assertEqual(rows[closed.name]["actual_cost"], 0)

	def test_uninvoiced_actual_cost_is_in_company_currency(self):
		po = create_purchase_order(supplier="_Test Supplier USD", currency="USD", rate=10, do_not_submit=1)
		po.conversion_rate = 80
		po.submit()

		row = next(row for row in self.run_report() if row.get("purchase_order") == po.name)
		self.assertEqual(row["actual_cost"], 8000)
