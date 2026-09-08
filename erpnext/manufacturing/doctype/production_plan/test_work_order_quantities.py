# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from contextlib import contextmanager
from unittest.mock import patch

import frappe

from erpnext.manufacturing.doctype.operation.test_operation import make_operation
from erpnext.manufacturing.doctype.production_plan.services.work_order_quantities import (
	ProductionPlanWorkOrderQuantities,
)
from erpnext.manufacturing.doctype.production_plan.test_production_plan import (
	create_production_plan,
	make_bom,
)
from erpnext.manufacturing.doctype.work_order.mapper import make_stock_entry as make_se_from_wo
from erpnext.manufacturing.doctype.work_order.work_order import (
	OverProductionError,
	StockOverProductionError,
	close_work_order,
	stop_unstop,
)
from erpnext.manufacturing.doctype.workstation.test_workstation import make_workstation
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

				self.assert_loss_reversal_blocked(manufacture)
				first.reload()
				self.assertEqual(first.process_loss_qty, 10)
				self.assertEqual(first.produced_qty, 90)
				self.assert_pending_qty(plan, field, 0)
				replacement.cancel()
				manufacture.cancel()
				self.assertEqual(first.reload().process_loss_qty, 0)
				first.reload().cancel()
				self.assert_pending_qty(plan, field, 100)

	def test_cumulative_manufacture_loss_exceeds_work_order(self):
		plan = self.make_plan()
		for field in (None, *REFERENCE_FIELDS):
			with self.subTest(field=field):
				first = self.create_work_order(plan, field or "production_plan_item")
				if field is None:
					first.production_plan = None
					first.production_plan_item = None
				first.qty = 100
				first.submit()
				self.manufacture_with_loss(first, loss_qty=99)
				second_entry = self.manufacture_with_loss(first, loss_qty=99, submit=False)
				self.assert_manufacture_rejected(second_entry, StockOverProductionError)
				self.assertEqual(first.reload().produced_qty, 1)
				self.assertEqual(first.process_loss_qty, 99)
				if field:
					self.assert_pending_qty(plan, field, 99)
					replacement = self.create_work_order(plan, field)
					replacement.submit()
					self.assert_pending_qty(plan, field, 0)

	def test_cumulative_manufacture_loss_respects_allowance(self):
		frappe.db.set_single_value("Manufacturing Settings", "overproduction_percentage_for_work_order", 10)
		plan = self.make_plan()
		for field in REFERENCE_FIELDS:
			with self.subTest(field=field):
				first = self.create_work_order(plan, field)
				first.submit()
				self.manufacture_with_loss(first, qty=50)
				self.manufacture_with_loss(first, qty=50)
				last_entry = self.manufacture_with_loss(first, qty=10)
				self.assertEqual(first.reload().produced_qty, 99)
				self.assertEqual(first.process_loss_qty, 11)
				self.assert_pending_qty(plan, field, 1)
				excess = self.manufacture_with_loss(first, qty=1, submit=False)
				self.assert_manufacture_rejected(excess, StockOverProductionError)
				excess.delete()
				last_entry.cancel()
				self.assertEqual(first.reload().produced_qty, 90)
				self.assertEqual(first.process_loss_qty, 10)
				self.manufacture_with_loss(first, qty=10)

	@ERPNextTestSuite.change_settings("System Settings", {"float_precision": 6})
	def test_cumulative_fractional_manufacture_loss(self):
		plan = self.make_plan(qty=0.3)
		for field in REFERENCE_FIELDS:
			with self.subTest(field=field):
				first = self.create_work_order(plan, field)
				first.submit()
				self.manufacture_with_loss(first, qty=0.1, loss_qty=0.025)
				self.manufacture_with_loss(first, qty=0.2, loss_qty=0.05)
				self.assertAlmostEqual(first.reload().produced_qty, 0.225)
				self.assertAlmostEqual(first.process_loss_qty, 0.075)
				excess = self.manufacture_with_loss(first, qty=0.001, submit=False)
				self.assert_manufacture_rejected(excess, StockOverProductionError)

	def test_existing_excess_loss_preserves_produced_quantity(self):
		for field in REFERENCE_FIELDS:
			for loss_qty, produced_qty in ((198, 2), (100, 2), (20, 90), (198, 0)):
				with self.subTest(field=field, loss_qty=loss_qty, produced_qty=produced_qty):
					plan = self.make_plan()
					first = self.create_work_order(plan, field)
					first.submit()
					# Reproduce records saved before cumulative manufacture validation existed.
					first.db_set({"process_loss_qty": loss_qty, "produced_qty": produced_qty})
					pending_qty = 100 - produced_qty
					self.assert_pending_qty(plan, field, pending_qty)
					replacement = self.create_work_order(plan, field)
					self.assertEqual(replacement.qty, pending_qty)
					self.assert_overproduction(replacement, pending_qty + 1)
					replacement.qty = pending_qty
					replacement.submit()
					self.assert_pending_qty(plan, field, 0)
					quantities = ProductionPlanWorkOrderQuantities(plan.name)
					quantities.validate_work_order(first, process_loss_qty=loss_qty)
					with self.assertRaises(OverProductionError):
						quantities.validate_work_order(first, process_loss_qty=0)

	def test_more_production_cannot_consume_replacement_allowance(self):
		frappe.db.set_single_value("Manufacturing Settings", "overproduction_percentage_for_work_order", 10)
		plan = self.make_plan()
		for field in REFERENCE_FIELDS:
			with self.subTest(field=field):
				first = self.create_work_order(plan, field)
				first.submit()
				self.manufacture_with_loss(first, loss_qty=99)
				replacement = self.create_work_order(plan, field)
				replacement.qty = 109
				replacement.submit()
				# This fits the first Work Order's allowance, but exceeds the plan's 110 units.
				excess = self.manufacture_with_loss(first, qty=10, loss_qty=9, submit=False)
				self.assert_manufacture_rejected(excess, OverProductionError)
				self.assertEqual(first.reload().produced_qty, 1)
				self.assertEqual(first.process_loss_qty, 99)

	def test_loss_reversal_with_draft_replacement(self):
		plan = self.make_plan()
		for field in REFERENCE_FIELDS:
			with self.subTest(field=field):
				first = self.create_work_order(plan, field)
				first.submit()
				manufacture = self.manufacture_with_loss(first)
				replacement = self.create_work_order(plan, field)
				manufacture.cancel()
				self.assertEqual(first.reload().process_loss_qty, 0)
				self.assert_pending_qty(plan, field, 0)
				self.assert_overproduction(replacement, 10)

	def test_partial_loss_reversal_with_overproduction_allowance(self):
		frappe.db.set_single_value("Manufacturing Settings", "overproduction_percentage_for_work_order", 5)
		plan = self.make_plan()
		for field in REFERENCE_FIELDS:
			with self.subTest(field=field):
				first = self.create_work_order(plan, field)
				first.submit()
				manufactures = [self.manufacture_with_loss(first, qty=50) for _ in range(2)]
				self.assertEqual(first.reload().process_loss_qty, 10)
				replacement = self.create_work_order(plan, field)
				replacement.submit()

				# Retaining five units of loss keeps the net quantity at the allowed 105.
				manufactures[1].cancel()
				self.assertEqual(first.reload().process_loss_qty, 5)
				self.assert_loss_reversal_blocked(manufactures[0])
				self.assertEqual(first.reload().process_loss_qty, 5)
				replacement.cancel()
				manufactures[0].cancel()
				self.assertEqual(first.reload().process_loss_qty, 0)

	def test_job_card_loss_reversal_with_replacement(self):
		self.make_bom_with_operation(self.finished_good, self.raw_material)
		plan = self.make_plan()
		first = self.create_work_order(plan, "production_plan_item")
		first.submit()
		job_card = frappe.get_last_doc("Job Card", {"work_order": first.name})
		job_card.append("time_logs", {"from_time": "2024-05-01 08:00:00"})
		job_card.save()
		job_card.complete_job_card(
			qty=90,
			for_quantity=100,
			pending_qty=0,
			process_loss_qty=10,
			end_time="2024-05-01 09:00:00",
		)
		job_card.reload().submit()
		self.assertEqual(first.reload().process_loss_qty, 10)
		make_stock_entry(item_code=self.raw_material, target=self.warehouse, qty=100, basic_rate=10)
		manufacture = frappe.get_doc(job_card.make_stock_entry_for_semi_fg_item()).submit()
		replacement = self.create_work_order(plan, "production_plan_item")
		replacement.submit()
		with self.assert_plan_locked_before_work_order_update(first):
			manufacture.cancel()
		job_card.reload()
		self.assert_loss_reversal_blocked(job_card)
		self.assertEqual(first.reload().process_loss_qty, 10)
		self.assertEqual(first.operations[0].process_loss_qty, 10)
		replacement.cancel()
		job_card.cancel()
		self.assertEqual(first.reload().process_loss_qty, 0)

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

	def make_bom_with_operation(self, item, material):
		bom = make_bom(item=item, raw_materials=[material], with_operations=1, do_not_save=True)
		bom.track_semi_finished_goods = 1
		bom.items[0].operation_row_id = 1
		operation = {
			"operation": f"_Test Loss Reversal {item}",
			"workstation": "_Test Workstation A",
			"finished_good": item,
			"finished_good_qty": 1,
			"is_final_finished_good": 1,
			"sequence_id": 1,
			"time_in_mins": 60,
			"source_warehouse": self.warehouse,
			"fg_warehouse": self.warehouse,
			"skip_material_transfer": 1,
		}
		make_workstation(operation)
		make_operation(operation)
		bom.append("operations", operation)
		bom.insert().submit()

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

	def manufacture_with_loss(self, work_order, qty=None, *, loss_qty=None, submit=True):
		for item in work_order.required_items:
			make_stock_entry(
				item_code=item.item_code, target=self.warehouse, qty=item.required_qty, basic_rate=10
			)
		entry = frappe.get_doc(make_se_from_wo(work_order.name, "Manufacture", qty or work_order.qty))
		if loss_qty is not None:
			entry.process_loss_qty = loss_qty
			entry.process_loss_percentage = loss_qty / entry.fg_completed_qty * 100
			for item in entry.items:
				if item.is_finished_item:
					item.qty = entry.fg_completed_qty - loss_qty
		if submit:
			entry.submit()
		else:
			entry.save()
		return entry

	def assert_manufacture_rejected(self, entry, exception):
		frappe.db.savepoint("excess_manufacture")
		try:
			with self.assertRaises(exception):
				entry.submit()
		finally:
			frappe.db.rollback(save_point="excess_manufacture")
		self.assertEqual(entry.reload().docstatus, 0)

	def assert_loss_reversal_blocked(self, document):
		work_order = frappe.get_doc("Work Order", document.work_order)
		frappe.db.savepoint("loss_reversal")
		try:
			with (
				self.assert_plan_locked_before_work_order_update(work_order),
				self.assertRaises(OverProductionError),
			):
				document.cancel()
		finally:
			# Match the request rollback after an on_cancel validation fails.
			frappe.db.rollback(save_point="loss_reversal")
		self.assertEqual(document.reload().docstatus, 1)

	@contextmanager
	def assert_plan_locked_before_work_order_update(self, work_order):
		get_value, set_value = frappe.db.get_value, frappe.db.set_value
		plan_row_locked = False
		row_doctype = (
			"Production Plan Sub Assembly Item"
			if work_order.production_plan_sub_assembly_item
			else "Production Plan Item"
		)
		row_name = work_order.production_plan_sub_assembly_item or work_order.production_plan_item

		def get_value_with_lock_check(doctype, filters=None, *args, **kwargs):
			nonlocal plan_row_locked
			if doctype == "Work Order" and filters == work_order.name and kwargs.get("for_update"):
				self.assertTrue(plan_row_locked, "Work Order locked before its Production Plan row")
			result = get_value(doctype, filters, *args, **kwargs)
			if (
				doctype == row_doctype
				and filters == {"name": row_name, "parent": work_order.production_plan}
				and kwargs.get("for_update")
			):
				plan_row_locked = True
			return result

		def set_value_with_lock_check(doctype, name, *args, **kwargs):
			if doctype == "Work Order" and name == work_order.name:
				self.assertTrue(plan_row_locked, "Work Order updated before locking its Production Plan row")
			return set_value(doctype, name, *args, **kwargs)

		with (
			patch.object(frappe.db, "get_value", get_value_with_lock_check),
			patch.object(frappe.db, "set_value", set_value_with_lock_check),
		):
			yield

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
