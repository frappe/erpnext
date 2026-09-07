# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from erpnext.manufacturing.doctype.production_plan.test_production_plan import (
	create_production_plan,
	make_bom,
)
from erpnext.manufacturing.doctype.work_order.mapper import make_stock_entry as make_se_from_wo
from erpnext.manufacturing.doctype.work_order.work_order import (
	OverProductionError,
	close_work_order,
	stop_unstop,
)
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
from erpnext.tests.utils import ERPNextTestSuite

REFERENCE_FIELDS = ("production_plan_item", "production_plan_sub_assembly_item")


class TestProductionPlanWorkOrderQuantities(ERPNextTestSuite):
	def setUp(self):
		self.warehouse = "_Test Warehouse - _TC"
		self.raw_material, self.sub_assembly, self.finished_good = (
			make_item(properties={"is_stock_item": 1, "stock_uom": "Kg", "valuation_rate": 10}).name
			for _ in range(3)
		)
		for item, material in (
			(self.sub_assembly, self.raw_material),
			(self.finished_good, self.sub_assembly),
		):
			make_bom(item=item, raw_materials=[material], process_loss_percentage=10)
		frappe.db.set_single_value("Manufacturing Settings", "overproduction_percentage_for_work_order", 0)

	def test_quantity_limit_on_submit(self):
		plan = self.make_plan()
		for field in REFERENCE_FIELDS:
			with self.subTest(field=field):
				first = self.create_work_order(plan, field)
				first.qty = 50
				first.submit()
				second = self.create_work_order(plan, field)
				self.assertEqual(second.qty, 50)
				self.assert_overproduction(second, 60)
				second.qty = 50
				second.submit()
				self.assert_pending_qty(plan, field, 0)

	def test_recorded_loss_creates_replacement(self):
		plan = self.make_plan()
		for field in REFERENCE_FIELDS:
			with self.subTest(field=field):
				first = self.create_work_order(plan, field)
				first.submit()
				self.assert_pending_qty(plan, field, 0)
				manufacture = self.manufacture_with_loss(first)
				first.reload()
				self.assertEqual(first.process_loss_qty, 10)
				self.assertEqual(first.produced_qty, 90)
				self.assert_pending_qty(plan, field, 10)

				replacement = self.create_work_order(plan, field)
				self.assertEqual(replacement.qty, 10)
				self.assert_overproduction(replacement, 11)
				replacement.qty = 10
				replacement.submit()
				self.assert_pending_qty(plan, field, 0)
				row = self.plan_row(plan, field)
				self.assertEqual(row.ordered_qty, 110)

				manufacture.cancel()
				self.assert_pending_qty(plan, field, 0)
				extra = self.copy_work_order(replacement)
				self.assert_overproduction(extra, 1)
				replacement.cancel()
				first.reload().cancel()
				self.assert_pending_qty(plan, field, 100)

	def test_expected_loss_does_not_allow_extra_quantity(self):
		plan = self.make_plan()
		for field in REFERENCE_FIELDS:
			with self.subTest(field=field):
				work_order = self.create_work_order(plan, field)
				self.assert_overproduction(work_order, 110)

	def test_overproduction_allowance(self):
		frappe.db.set_single_value("Manufacturing Settings", "overproduction_percentage_for_work_order", 10)
		plan = self.make_plan()
		for field in REFERENCE_FIELDS:
			with self.subTest(field=field):
				first = self.create_work_order(plan, field)
				self.assertEqual(first.qty, 100)
				first.submit()
				self.assert_pending_qty(plan, field, 0)
				second = self.copy_work_order(first)
				self.assert_overproduction(second, 11)
				second.qty = 10
				second.submit()

	def test_drafts_and_cancelled_orders_do_not_consume_quantity(self):
		plan = self.make_plan()
		for field in REFERENCE_FIELDS:
			with self.subTest(field=field):
				first = self.create_work_order(plan, field)
				second = self.create_work_order(plan, field)
				self.assertEqual(first.qty, second.qty)
				first.submit()
				self.assert_overproduction(second, 100)
				first.cancel()
				second.submit()
				self.assert_pending_qty(plan, field, 0)

	def test_process_loss_and_overproduction_allowance(self):
		frappe.db.set_single_value("Manufacturing Settings", "overproduction_percentage_for_work_order", 10)
		plan = self.make_plan()
		for field in REFERENCE_FIELDS:
			with self.subTest(field=field):
				first = self.create_work_order(plan, field)
				first.qty = 50
				first.submit()
				self.manufacture_with_loss(first)
				second = self.create_work_order(plan, field)
				self.assertEqual(second.qty, 55)
				self.assert_overproduction(second, 66)
				second.qty = 65
				second.submit()
				self.assert_pending_qty(plan, field, 0)

	def test_stopped_and_closed_orders_consume_quantity(self):
		plan = self.make_plan()
		for field in REFERENCE_FIELDS:
			with self.subTest(field=field):
				first = self.create_work_order(plan, field)
				first.submit()
				stop_unstop(first.name, "Stopped")
				self.assert_pending_qty(plan, field, 0)
				stop_unstop(first.name, "Not Started")
				close_work_order(first.name, "Closed")
				self.assert_pending_qty(plan, field, 0)

	def test_fractional_quantities(self):
		plan = self.make_plan(qty=0.3)
		for field in REFERENCE_FIELDS:
			with self.subTest(field=field):
				first = self.create_work_order(plan, field)
				first.qty = 0.1
				first.submit()
				second = self.create_work_order(plan, field)
				self.assertEqual(second.qty, 0.2)
				second.submit()
				self.assert_pending_qty(plan, field, 0)

	def test_rows_with_same_item_are_independent(self):
		plan = self.make_plan(submit=False)
		sales_order = make_sales_order(item_code=self.finished_good, qty=200, warehouse=self.warehouse)
		plan.po_items[0].sales_order = sales_order.name
		plan.po_items[0].sales_order_item = sales_order.items[0].name
		row = plan.po_items[0].as_dict()
		row.pop("name")
		row["planned_qty"] = 50
		plan.append("po_items", row)
		plan.submit()
		first = self.create_work_order(plan, "production_plan_item")
		first.submit()
		plan.onload()
		pending = plan.get_onload()["pending_work_order_qty"]["production_plan_item"]
		self.assertEqual(pending[plan.po_items[0].name], 0)
		self.assertEqual(pending[plan.po_items[1].name], 50)
		second_name = frappe.db.get_value(
			"Work Order", {"production_plan_item": plan.po_items[1].name, "docstatus": 0}, "name"
		)
		second = frappe.get_doc("Work Order", second_name)
		self.assertEqual(second.qty, 50)
		self.assert_overproduction(second, 51)

	def test_material_request_plan_uses_remaining_quantity(self):
		plan = self.make_plan(submit=False)
		plan.get_items_from = "Material Request"
		plan.submit()
		first = self.create_work_order(plan, "production_plan_item")
		first.qty = 50
		first.submit()
		second = self.create_work_order(plan, "production_plan_item")
		self.assertEqual(second.qty, 50)

	def test_reference_must_belong_to_plan(self):
		plan = self.make_plan()
		other_plan = self.make_plan()
		work_order = self.create_work_order(plan, "production_plan_item")
		work_order.production_plan = other_plan.name
		with self.assertRaisesRegex(frappe.ValidationError, "must reference a row"):
			work_order.submit()

	def test_missing_or_ambiguous_plan_reference(self):
		plan = self.make_plan()
		work_order = self.create_work_order(plan, "production_plan_item")
		work_order.production_plan_sub_assembly_item = plan.sub_assembly_items[0].name
		with self.assertRaisesRegex(frappe.ValidationError, "only one Production Plan row"):
			work_order.submit()
		work_order.reload()
		work_order.production_plan_item = None
		with self.assertRaisesRegex(frappe.ValidationError, "must reference a row"):
			work_order.submit()

	def make_plan(self, qty=100, submit=True):
		plan = create_production_plan(
			item_code=self.finished_good,
			planned_qty=qty,
			stock_uom="Kg",
			warehouse=self.warehouse,
			sub_assembly_warehouse=self.warehouse,
			skip_getting_mr_items=True,
			do_not_submit=True,
		)
		plan.get_sub_assembly_items()
		if submit:
			plan.submit()
		return plan

	def create_work_order(self, plan, field):
		plan.make_work_order()
		name = frappe.db.get_value(
			"Work Order",
			{"production_plan": plan.name, field: self.plan_row(plan, field).name, "docstatus": 0},
			"name",
			order_by="creation desc",
		)
		work_order = frappe.get_doc("Work Order", name)
		work_order.update(
			{"skip_transfer": 1, "source_warehouse": self.warehouse, "fg_warehouse": self.warehouse}
		)
		return work_order

	def copy_work_order(self, work_order):
		copy = frappe.copy_doc(work_order)
		copy.docstatus = 0
		copy.production_plan = work_order.production_plan
		for field in REFERENCE_FIELDS:
			copy.set(field, work_order.get(field))
		copy.insert()
		return copy

	def manufacture_with_loss(self, work_order):
		for item in work_order.required_items:
			make_stock_entry(
				item_code=item.item_code, target=self.warehouse, qty=item.required_qty, basic_rate=10
			)
		entry = frappe.get_doc(make_se_from_wo(work_order.name, "Manufacture", work_order.qty))
		entry.submit()
		return entry

	def assert_overproduction(self, work_order, qty):
		work_order.qty = qty
		work_order.save()
		with self.assertRaises(OverProductionError):
			work_order.submit()
		work_order.reload()

	def assert_pending_qty(self, plan, field, expected):
		plan.reload()
		plan.onload()
		self.assertEqual(
			plan.get_onload()["pending_work_order_qty"][field][self.plan_row(plan, field).name], expected
		)

	def plan_row(self, plan, field):
		return plan.po_items[0] if field == "production_plan_item" else plan.sub_assembly_items[0]
