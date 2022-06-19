# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase, change_settings, timeout
from frappe.utils import add_days, add_months, cint, flt, now, today

from erpnext.manufacturing.doctype.job_card.job_card import JobCardCancelError
from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
from erpnext.manufacturing.doctype.work_order.work_order import (
	CapacityError,
	ItemHasVariantError,
	OverProductionError,
	StockOverProductionError,
	close_work_order,
	make_job_card,
	make_stock_entry,
	stop_unstop,
)
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.stock.doctype.item.test_item import create_item, make_item
from erpnext.stock.doctype.stock_entry import test_stock_entry
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse
from erpnext.stock.utils import get_bin


class TestWorkOrder(FrappeTestCase):
	def setUp(self):
		self.warehouse = "_Test Warehouse 2 - _TC"
		self.item = "_Test Item"

	def tearDown(self):
		frappe.db.rollback()

	def check_planned_qty(self):

		planned0 = (
			frappe.db.get_value(
				"Bin", {"item_code": "_Test FG Item", "warehouse": "_Test Warehouse 1 - _TC"}, "planned_qty"
			)
			or 0
		)

		wo_order = make_wo_order_test_record()

		planned1 = frappe.db.get_value(
			"Bin", {"item_code": "_Test FG Item", "warehouse": "_Test Warehouse 1 - _TC"}, "planned_qty"
		)

		self.assertEqual(planned1, planned0 + 10)

		# add raw materials to stores
		test_stock_entry.make_stock_entry(
			item_code="_Test Item", target="Stores - _TC", qty=100, basic_rate=100
		)
		test_stock_entry.make_stock_entry(
			item_code="_Test Item Home Desktop 100", target="Stores - _TC", qty=100, basic_rate=100
		)

		# from stores to wip
		s = frappe.get_doc(make_stock_entry(wo_order.name, "Material Transfer for Manufacture", 4))
		for d in s.get("items"):
			d.s_warehouse = "Stores - _TC"
		s.insert()
		s.submit()

		# from wip to fg
		s = frappe.get_doc(make_stock_entry(wo_order.name, "Manufacture", 4))
		s.insert()
		s.submit()

		self.assertEqual(frappe.db.get_value("Work Order", wo_order.name, "produced_qty"), 4)

		planned2 = frappe.db.get_value(
			"Bin", {"item_code": "_Test FG Item", "warehouse": "_Test Warehouse 1 - _TC"}, "planned_qty"
		)

		self.assertEqual(planned2, planned0 + 6)

		return wo_order

	def test_over_production(self):
		wo_doc = self.check_planned_qty()

		test_stock_entry.make_stock_entry(
			item_code="_Test Item", target="_Test Warehouse - _TC", qty=100, basic_rate=100
		)
		test_stock_entry.make_stock_entry(
			item_code="_Test Item Home Desktop 100", target="_Test Warehouse - _TC", qty=100, basic_rate=100
		)

		s = frappe.get_doc(make_stock_entry(wo_doc.name, "Manufacture", 7))
		s.insert()

		self.assertRaises(StockOverProductionError, s.submit)

	def test_planned_operating_cost(self):
		wo_order = make_wo_order_test_record(
			item="_Test FG Item 2", planned_start_date=now(), qty=1, do_not_save=True
		)
		wo_order.set_work_order_operations()
		cost = wo_order.planned_operating_cost
		wo_order.qty = 2
		wo_order.set_work_order_operations()
		self.assertEqual(wo_order.planned_operating_cost, cost * 2)

	def test_reserved_qty_for_partial_completion(self):
		item = "_Test Item"
		warehouse = "_Test Warehouse - _TC"

		bin1_at_start = get_bin(item, warehouse)

		# reset to correct value
		bin1_at_start.update_reserved_qty_for_production()

		wo_order = make_wo_order_test_record(
			item="_Test FG Item", qty=2, source_warehouse=warehouse, skip_transfer=1
		)

		reserved_qty_on_submission = cint(get_bin(item, warehouse).reserved_qty_for_production)

		# reserved qty for production is updated
		self.assertEqual(cint(bin1_at_start.reserved_qty_for_production) + 2, reserved_qty_on_submission)

		test_stock_entry.make_stock_entry(
			item_code="_Test Item", target=warehouse, qty=100, basic_rate=100
		)
		test_stock_entry.make_stock_entry(
			item_code="_Test Item Home Desktop 100", target=warehouse, qty=100, basic_rate=100
		)

		s = frappe.get_doc(make_stock_entry(wo_order.name, "Manufacture", 1))
		s.submit()

		bin1_at_completion = get_bin(item, warehouse)

		self.assertEqual(
			cint(bin1_at_completion.reserved_qty_for_production), reserved_qty_on_submission - 1
		)

	def test_production_item(self):
		wo_order = make_wo_order_test_record(item="_Test FG Item", qty=1, do_not_save=True)
		frappe.db.set_value("Item", "_Test FG Item", "end_of_life", "2000-1-1")

		self.assertRaises(frappe.ValidationError, wo_order.save)

		frappe.db.set_value("Item", "_Test FG Item", "end_of_life", None)
		frappe.db.set_value("Item", "_Test FG Item", "disabled", 1)

		self.assertRaises(frappe.ValidationError, wo_order.save)

		frappe.db.set_value("Item", "_Test FG Item", "disabled", 0)

		wo_order = make_wo_order_test_record(item="_Test Variant Item", qty=1, do_not_save=True)
		self.assertRaises(ItemHasVariantError, wo_order.save)

	def test_reserved_qty_for_production_submit(self):
		self.bin1_at_start = get_bin(self.item, self.warehouse)

		# reset to correct value
		self.bin1_at_start.update_reserved_qty_for_production()

		self.wo_order = make_wo_order_test_record(
			item="_Test FG Item", qty=2, source_warehouse=self.warehouse
		)

		self.bin1_on_submit = get_bin(self.item, self.warehouse)

		# reserved qty for production is updated
		self.assertEqual(
			cint(self.bin1_at_start.reserved_qty_for_production) + 2,
			cint(self.bin1_on_submit.reserved_qty_for_production),
		)
		self.assertEqual(
			cint(self.bin1_at_start.projected_qty), cint(self.bin1_on_submit.projected_qty) + 2
		)

	def test_reserved_qty_for_production_cancel(self):
		self.test_reserved_qty_for_production_submit()

		self.wo_order.cancel()

		bin1_on_cancel = get_bin(self.item, self.warehouse)

		# reserved_qty_for_producion updated
		self.assertEqual(
			cint(self.bin1_at_start.reserved_qty_for_production),
			cint(bin1_on_cancel.reserved_qty_for_production),
		)
		self.assertEqual(self.bin1_at_start.projected_qty, cint(bin1_on_cancel.projected_qty))

	def test_reserved_qty_for_production_on_stock_entry(self):
		test_stock_entry.make_stock_entry(
			item_code="_Test Item", target=self.warehouse, qty=100, basic_rate=100
		)
		test_stock_entry.make_stock_entry(
			item_code="_Test Item Home Desktop 100", target=self.warehouse, qty=100, basic_rate=100
		)

		self.test_reserved_qty_for_production_submit()

		s = frappe.get_doc(make_stock_entry(self.wo_order.name, "Material Transfer for Manufacture", 2))

		s.submit()

		bin1_on_start_production = get_bin(self.item, self.warehouse)

		# reserved_qty_for_producion updated
		self.assertEqual(
			cint(self.bin1_at_start.reserved_qty_for_production),
			cint(bin1_on_start_production.reserved_qty_for_production),
		)

		# projected qty will now be 2 less (becuase of item movement)
		self.assertEqual(
			cint(self.bin1_at_start.projected_qty), cint(bin1_on_start_production.projected_qty) + 2
		)

		s = frappe.get_doc(make_stock_entry(self.wo_order.name, "Manufacture", 2))

		bin1_on_end_production = get_bin(self.item, self.warehouse)

		# no change in reserved / projected
		self.assertEqual(
			cint(bin1_on_end_production.reserved_qty_for_production),
			cint(bin1_on_start_production.reserved_qty_for_production),
		)

	def test_reserved_qty_for_production_closed(self):

		wo1 = make_wo_order_test_record(item="_Test FG Item", qty=2, source_warehouse=self.warehouse)
		item = wo1.required_items[0].item_code
		bin_before = get_bin(item, self.warehouse)
		bin_before.update_reserved_qty_for_production()

		make_wo_order_test_record(item="_Test FG Item", qty=2, source_warehouse=self.warehouse)
		close_work_order(wo1.name, "Closed")

		bin_after = get_bin(item, self.warehouse)
		self.assertEqual(bin_before.reserved_qty_for_production, bin_after.reserved_qty_for_production)

	def test_backflush_qty_for_overpduction_manufacture(self):
		cancel_stock_entry = []
		allow_overproduction("overproduction_percentage_for_work_order", 30)
		wo_order = make_wo_order_test_record(planned_start_date=now(), qty=100)
		ste1 = test_stock_entry.make_stock_entry(
			item_code="_Test Item", target="_Test Warehouse - _TC", qty=120, basic_rate=5000.0
		)
		ste2 = test_stock_entry.make_stock_entry(
			item_code="_Test Item Home Desktop 100",
			target="_Test Warehouse - _TC",
			qty=240,
			basic_rate=1000.0,
		)

		cancel_stock_entry.extend([ste1.name, ste2.name])

		s = frappe.get_doc(make_stock_entry(wo_order.name, "Material Transfer for Manufacture", 60))
		s.submit()
		cancel_stock_entry.append(s.name)

		s = frappe.get_doc(make_stock_entry(wo_order.name, "Manufacture", 60))
		s.submit()
		cancel_stock_entry.append(s.name)

		s = frappe.get_doc(make_stock_entry(wo_order.name, "Material Transfer for Manufacture", 60))
		s.submit()
		cancel_stock_entry.append(s.name)

		s1 = frappe.get_doc(make_stock_entry(wo_order.name, "Manufacture", 50))
		s1.submit()
		cancel_stock_entry.append(s1.name)

		self.assertEqual(s1.items[0].qty, 50)
		self.assertEqual(s1.items[1].qty, 100)
		cancel_stock_entry.reverse()
		for ste in cancel_stock_entry:
			doc = frappe.get_doc("Stock Entry", ste)
			doc.cancel()

		allow_overproduction("overproduction_percentage_for_work_order", 0)

	def test_reserved_qty_for_stopped_production(self):
		test_stock_entry.make_stock_entry(
			item_code="_Test Item", target=self.warehouse, qty=100, basic_rate=100
		)
		test_stock_entry.make_stock_entry(
			item_code="_Test Item Home Desktop 100", target=self.warehouse, qty=100, basic_rate=100
		)

		# 	0 0 0

		self.test_reserved_qty_for_production_submit()

		# 2 0 -2

		s = frappe.get_doc(make_stock_entry(self.wo_order.name, "Material Transfer for Manufacture", 1))

		s.submit()

		# 1 -1 0

		bin1_on_start_production = get_bin(self.item, self.warehouse)

		# reserved_qty_for_producion updated
		self.assertEqual(
			cint(self.bin1_at_start.reserved_qty_for_production) + 1,
			cint(bin1_on_start_production.reserved_qty_for_production),
		)

		# projected qty will now be 2 less (becuase of item movement)
		self.assertEqual(
			cint(self.bin1_at_start.projected_qty), cint(bin1_on_start_production.projected_qty) + 2
		)

		# STOP
		stop_unstop(self.wo_order.name, "Stopped")

		bin1_on_stop_production = get_bin(self.item, self.warehouse)

		# no change in reserved / projected
		self.assertEqual(
			cint(bin1_on_stop_production.reserved_qty_for_production),
			cint(self.bin1_at_start.reserved_qty_for_production),
		)
		self.assertEqual(
			cint(bin1_on_stop_production.projected_qty) + 1, cint(self.bin1_at_start.projected_qty)
		)

	def test_scrap_material_qty(self):
		wo_order = make_wo_order_test_record(planned_start_date=now(), qty=2)

		# add raw materials to stores
		test_stock_entry.make_stock_entry(
			item_code="_Test Item", target="Stores - _TC", qty=10, basic_rate=5000.0
		)
		test_stock_entry.make_stock_entry(
			item_code="_Test Item Home Desktop 100", target="Stores - _TC", qty=10, basic_rate=1000.0
		)

		s = frappe.get_doc(make_stock_entry(wo_order.name, "Material Transfer for Manufacture", 2))
		for d in s.get("items"):
			d.s_warehouse = "Stores - _TC"
		s.insert()
		s.submit()

		s = frappe.get_doc(make_stock_entry(wo_order.name, "Manufacture", 2))
		s.insert()
		s.submit()

		wo_order_details = frappe.db.get_value(
			"Work Order", wo_order.name, ["scrap_warehouse", "qty", "produced_qty", "bom_no"], as_dict=1
		)

		scrap_item_details = get_scrap_item_details(wo_order_details.bom_no)

		self.assertEqual(wo_order_details.produced_qty, 2)

		for item in s.items:
			if item.bom_no and item.item_code in scrap_item_details:
				self.assertEqual(wo_order_details.scrap_warehouse, item.t_warehouse)
				self.assertEqual(flt(wo_order_details.qty) * flt(scrap_item_details[item.item_code]), item.qty)

	def test_allow_overproduction(self):
		allow_overproduction("overproduction_percentage_for_work_order", 0)
		wo_order = make_wo_order_test_record(planned_start_date=now(), qty=2)
		test_stock_entry.make_stock_entry(
			item_code="_Test Item", target="_Test Warehouse - _TC", qty=10, basic_rate=5000.0
		)
		test_stock_entry.make_stock_entry(
			item_code="_Test Item Home Desktop 100",
			target="_Test Warehouse - _TC",
			qty=10,
			basic_rate=1000.0,
		)

		s = frappe.get_doc(make_stock_entry(wo_order.name, "Material Transfer for Manufacture", 3))
		s.insert()
		self.assertRaises(StockOverProductionError, s.submit)

		allow_overproduction("overproduction_percentage_for_work_order", 50)
		s.load_from_db()
		s.submit()
		self.assertEqual(s.docstatus, 1)

		allow_overproduction("overproduction_percentage_for_work_order", 0)

	def test_over_production_for_sales_order(self):
		so = make_sales_order(item_code="_Test FG Item", qty=2)

		allow_overproduction("overproduction_percentage_for_sales_order", 0)
		wo_order = make_wo_order_test_record(
			planned_start_date=now(), sales_order=so.name, qty=3, do_not_save=True
		)

		self.assertRaises(OverProductionError, wo_order.save)

		allow_overproduction("overproduction_percentage_for_sales_order", 50)
		wo_order = make_wo_order_test_record(planned_start_date=now(), sales_order=so.name, qty=3)

		self.assertEqual(wo_order.docstatus, 1)

		allow_overproduction("overproduction_percentage_for_sales_order", 0)

	def test_work_order_with_non_stock_item(self):
		items = {
			"Finished Good Test Item For non stock": 1,
			"_Test FG Item": 1,
			"_Test FG Non Stock Item": 0,
		}
		for item, is_stock_item in items.items():
			make_item(item, {"is_stock_item": is_stock_item})

		if not frappe.db.get_value("Item Price", {"item_code": "_Test FG Non Stock Item"}):
			frappe.get_doc(
				{
					"doctype": "Item Price",
					"item_code": "_Test FG Non Stock Item",
					"price_list_rate": 1000,
					"price_list": "_Test Price List India",
				}
			).insert(ignore_permissions=True)

		fg_item = "Finished Good Test Item For non stock"
		test_stock_entry.make_stock_entry(
			item_code="_Test FG Item", target="_Test Warehouse - _TC", qty=1, basic_rate=100
		)

		if not frappe.db.get_value("BOM", {"item": fg_item, "docstatus": 1}):
			bom = make_bom(
				item=fg_item,
				rate=1000,
				raw_materials=["_Test FG Item", "_Test FG Non Stock Item"],
				do_not_save=True,
			)
			bom.rm_cost_as_per = "Price List"  # non stock item won't have valuation rate
			bom.buying_price_list = "_Test Price List India"
			bom.currency = "INR"
			bom.save()

		wo = make_wo_order_test_record(production_item=fg_item)

		se = frappe.get_doc(make_stock_entry(wo.name, "Material Transfer for Manufacture", 1))
		se.insert()
		se.submit()

		ste = frappe.get_doc(make_stock_entry(wo.name, "Manufacture", 1))
		ste.insert()
		self.assertEqual(len(ste.additional_costs), 1)
		self.assertEqual(ste.total_additional_costs, 1000)

	@timeout(seconds=60)
	def test_job_card(self):
		stock_entries = []
		bom = frappe.get_doc("BOM", {"docstatus": 1, "with_operations": 1, "company": "_Test Company"})

		work_order = make_wo_order_test_record(
			item=bom.item, qty=1, bom_no=bom.name, source_warehouse="_Test Warehouse - _TC"
		)

		for row in work_order.required_items:
			stock_entry_doc = test_stock_entry.make_stock_entry(
				item_code=row.item_code, target="_Test Warehouse - _TC", qty=row.required_qty, basic_rate=100
			)
			stock_entries.append(stock_entry_doc)

		ste = frappe.get_doc(make_stock_entry(work_order.name, "Material Transfer for Manufacture", 1))
		ste.submit()
		stock_entries.append(ste)

		job_cards = frappe.get_all(
			"Job Card", filters={"work_order": work_order.name}, order_by="creation asc"
		)
		self.assertEqual(len(job_cards), len(bom.operations))

		for i, job_card in enumerate(job_cards):
			doc = frappe.get_doc("Job Card", job_card)
			doc.time_logs[0].completed_qty = 1
			doc.submit()

		ste1 = frappe.get_doc(make_stock_entry(work_order.name, "Manufacture", 1))
		ste1.submit()
		stock_entries.append(ste1)

		for job_card in job_cards:
			doc = frappe.get_doc("Job Card", job_card)
			self.assertRaises(JobCardCancelError, doc.cancel)

		stock_entries.reverse()
		for stock_entry in stock_entries:
			stock_entry.cancel()

	def test_capcity_planning(self):
		frappe.db.set_value(
			"Manufacturing Settings",
			None,
			{"disable_capacity_planning": 0, "capacity_planning_for_days": 1},
		)

		data = frappe.get_cached_value(
			"BOM",
			{"docstatus": 1, "item": "_Test FG Item 2", "with_operations": 1, "company": "_Test Company"},
			["name", "item"],
		)

		if data:
			bom, bom_item = data

			planned_start_date = add_months(today(), months=-1)
			work_order = make_wo_order_test_record(
				item=bom_item, qty=10, bom_no=bom, planned_start_date=planned_start_date
			)

			work_order1 = make_wo_order_test_record(
				item=bom_item, qty=30, bom_no=bom, planned_start_date=planned_start_date, do_not_submit=1
			)

			self.assertRaises(CapacityError, work_order1.submit)

			frappe.db.set_value("Manufacturing Settings", None, {"capacity_planning_for_days": 30})

			work_order1.reload()
			work_order1.submit()
			self.assertTrue(work_order1.docstatus, 1)

			work_order1.cancel()
			work_order.cancel()

	def test_work_order_with_non_transfer_item(self):
		items = {"Finished Good Transfer Item": 1, "_Test FG Item": 1, "_Test FG Item 1": 0}
		for item, allow_transfer in items.items():
			make_item(item, {"include_item_in_manufacturing": allow_transfer})

		fg_item = "Finished Good Transfer Item"
		test_stock_entry.make_stock_entry(
			item_code="_Test FG Item", target="_Test Warehouse - _TC", qty=1, basic_rate=100
		)
		test_stock_entry.make_stock_entry(
			item_code="_Test FG Item 1", target="_Test Warehouse - _TC", qty=1, basic_rate=100
		)

		if not frappe.db.get_value("BOM", {"item": fg_item}):
			make_bom(item=fg_item, raw_materials=["_Test FG Item", "_Test FG Item 1"])

		wo = make_wo_order_test_record(production_item=fg_item)
		ste = frappe.get_doc(make_stock_entry(wo.name, "Material Transfer for Manufacture", 1))
		ste.insert()
		ste.submit()
		self.assertEqual(len(ste.items), 1)
		ste1 = frappe.get_doc(make_stock_entry(wo.name, "Manufacture", 1))
		self.assertEqual(len(ste1.items), 3)

	def test_cost_center_for_manufacture(self):
		wo_order = make_wo_order_test_record()
		ste = make_stock_entry(wo_order.name, "Material Transfer for Manufacture", wo_order.qty)
		self.assertEqual(ste.get("items")[0].get("cost_center"), "_Test Cost Center - _TC")

	def test_operation_time_with_batch_size(self):
		fg_item = "Test Batch Size Item For BOM"
		rm1 = "Test Batch Size Item RM 1 For BOM"

		for item in ["Test Batch Size Item For BOM", "Test Batch Size Item RM 1 For BOM"]:
			make_item(item, {"include_item_in_manufacturing": 1, "is_stock_item": 1})

		bom_name = frappe.db.get_value(
			"BOM", {"item": fg_item, "is_active": 1, "with_operations": 1}, "name"
		)

		if not bom_name:
			bom = make_bom(item=fg_item, rate=1000, raw_materials=[rm1], do_not_save=True)
			bom.with_operations = 1
			bom.append(
				"operations",
				{
					"operation": "_Test Operation 1",
					"workstation": "_Test Workstation 1",
					"description": "Test Data",
					"operating_cost": 100,
					"time_in_mins": 40,
					"batch_size": 5,
				},
			)

			bom.save()
			bom.submit()
			bom_name = bom.name

		work_order = make_wo_order_test_record(
			item=fg_item, planned_start_date=now(), qty=1, do_not_save=True
		)

		work_order.set_work_order_operations()
		work_order.save()
		self.assertEqual(work_order.operations[0].time_in_mins, 8.0)

		work_order1 = make_wo_order_test_record(
			item=fg_item, planned_start_date=now(), qty=5, do_not_save=True
		)

		work_order1.set_work_order_operations()
		work_order1.save()
		self.assertEqual(work_order1.operations[0].time_in_mins, 40.0)

	def test_batch_size_for_fg_item(self):
		fg_item = "Test Batch Size Item For BOM 3"
		rm1 = "Test Batch Size Item RM 1 For BOM 3"

		frappe.db.set_value("Manufacturing Settings", None, "make_serial_no_batch_from_work_order", 0)
		for item in ["Test Batch Size Item For BOM 3", "Test Batch Size Item RM 1 For BOM 3"]:
			item_args = {"include_item_in_manufacturing": 1, "is_stock_item": 1}

			if item == fg_item:
				item_args["has_batch_no"] = 1
				item_args["create_new_batch"] = 1
				item_args["batch_number_series"] = "TBSI3.#####"

			make_item(item, item_args)

		bom_name = frappe.db.get_value(
			"BOM", {"item": fg_item, "is_active": 1, "with_operations": 1}, "name"
		)

		if not bom_name:
			bom = make_bom(item=fg_item, rate=1000, raw_materials=[rm1], do_not_save=True)
			bom.save()
			bom.submit()
			bom_name = bom.name

		work_order = make_wo_order_test_record(
			item=fg_item, skip_transfer=True, planned_start_date=now(), qty=1
		)
		ste1 = frappe.get_doc(make_stock_entry(work_order.name, "Manufacture", 1))
		for row in ste1.get("items"):
			if row.is_finished_item:
				self.assertEqual(row.item_code, fg_item)

		work_order = make_wo_order_test_record(
			item=fg_item, skip_transfer=True, planned_start_date=now(), qty=1
		)
		frappe.db.set_value("Manufacturing Settings", None, "make_serial_no_batch_from_work_order", 1)
		ste1 = frappe.get_doc(make_stock_entry(work_order.name, "Manufacture", 1))
		for row in ste1.get("items"):
			if row.is_finished_item:
				self.assertEqual(row.item_code, fg_item)

		work_order = make_wo_order_test_record(
			item=fg_item, skip_transfer=True, planned_start_date=now(), qty=30, do_not_save=True
		)
		work_order.batch_size = 10
		work_order.insert()
		work_order.submit()
		self.assertEqual(work_order.has_batch_no, 1)
		ste1 = frappe.get_doc(make_stock_entry(work_order.name, "Manufacture", 30))
		for row in ste1.get("items"):
			if row.is_finished_item:
				self.assertEqual(row.item_code, fg_item)
				self.assertEqual(row.qty, 10)

		frappe.db.set_value("Manufacturing Settings", None, "make_serial_no_batch_from_work_order", 0)

	def test_partial_material_consumption(self):
		frappe.db.set_value("Manufacturing Settings", None, "material_consumption", 1)
		wo_order = make_wo_order_test_record(planned_start_date=now(), qty=4)

		ste_cancel_list = []
		ste1 = test_stock_entry.make_stock_entry(
			item_code="_Test Item", target="_Test Warehouse - _TC", qty=20, basic_rate=5000.0
		)
		ste2 = test_stock_entry.make_stock_entry(
			item_code="_Test Item Home Desktop 100",
			target="_Test Warehouse - _TC",
			qty=20,
			basic_rate=1000.0,
		)

		ste_cancel_list.extend([ste1, ste2])

		s = frappe.get_doc(make_stock_entry(wo_order.name, "Material Transfer for Manufacture", 4))
		s.submit()
		ste_cancel_list.append(s)

		ste1 = frappe.get_doc(make_stock_entry(wo_order.name, "Manufacture", 2))
		ste1.submit()
		ste_cancel_list.append(ste1)

		ste3 = frappe.get_doc(make_stock_entry(wo_order.name, "Material Consumption for Manufacture", 2))
		self.assertEqual(ste3.fg_completed_qty, 2)

		expected_qty = {"_Test Item": 2, "_Test Item Home Desktop 100": 4}
		for row in ste3.items:
			self.assertEqual(row.qty, expected_qty.get(row.item_code))
		ste_cancel_list.reverse()
		for ste_doc in ste_cancel_list:
			ste_doc.cancel()

		frappe.db.set_value("Manufacturing Settings", None, "material_consumption", 0)

	def test_extra_material_transfer(self):
		frappe.db.set_value("Manufacturing Settings", None, "material_consumption", 0)
		frappe.db.set_value(
			"Manufacturing Settings",
			None,
			"backflush_raw_materials_based_on",
			"Material Transferred for Manufacture",
		)

		wo_order = make_wo_order_test_record(planned_start_date=now(), qty=4)

		ste_cancel_list = []
		ste1 = test_stock_entry.make_stock_entry(
			item_code="_Test Item", target="_Test Warehouse - _TC", qty=20, basic_rate=5000.0
		)
		ste2 = test_stock_entry.make_stock_entry(
			item_code="_Test Item Home Desktop 100",
			target="_Test Warehouse - _TC",
			qty=20,
			basic_rate=1000.0,
		)

		ste_cancel_list.extend([ste1, ste2])

		itemwise_qty = {}
		s = frappe.get_doc(make_stock_entry(wo_order.name, "Material Transfer for Manufacture", 4))
		for row in s.items:
			row.qty = row.qty + 2
			itemwise_qty.setdefault(row.item_code, row.qty)

		s.submit()
		ste_cancel_list.append(s)

		ste3 = frappe.get_doc(make_stock_entry(wo_order.name, "Manufacture", 2))
		for ste_row in ste3.items:
			if itemwise_qty.get(ste_row.item_code) and ste_row.s_warehouse:
				self.assertEqual(ste_row.qty, itemwise_qty.get(ste_row.item_code) / 2)

		ste3.submit()
		ste_cancel_list.append(ste3)

		ste2 = frappe.get_doc(make_stock_entry(wo_order.name, "Manufacture", 2))
		for ste_row in ste2.items:
			if itemwise_qty.get(ste_row.item_code) and ste_row.s_warehouse:
				self.assertEqual(ste_row.qty, itemwise_qty.get(ste_row.item_code) / 2)
		ste_cancel_list.reverse()
		for ste_doc in ste_cancel_list:
			ste_doc.cancel()

		frappe.db.set_value("Manufacturing Settings", None, "backflush_raw_materials_based_on", "BOM")

	def test_make_stock_entry_for_customer_provided_item(self):
		finished_item = "Test Item for Make Stock Entry 1"
		make_item(finished_item, {"include_item_in_manufacturing": 1, "is_stock_item": 1})

		customer_provided_item = "CUST-0987"
		make_item(
			customer_provided_item,
			{
				"is_purchase_item": 0,
				"is_customer_provided_item": 1,
				"is_stock_item": 1,
				"include_item_in_manufacturing": 1,
				"customer": "_Test Customer",
			},
		)

		if not frappe.db.exists("BOM", {"item": finished_item}):
			make_bom(item=finished_item, raw_materials=[customer_provided_item], rm_qty=1)

		company = "_Test Company with perpetual inventory"
		customer_warehouse = create_warehouse("Test Customer Provided Warehouse", company=company)
		wo = make_wo_order_test_record(
			item=finished_item, qty=1, source_warehouse=customer_warehouse, company=company
		)

		ste = frappe.get_doc(make_stock_entry(wo.name, purpose="Material Transfer for Manufacture"))
		ste.insert()

		self.assertEqual(len(ste.items), 1)
		for item in ste.items:
			self.assertEqual(item.allow_zero_valuation_rate, 1)
			self.assertEqual(item.valuation_rate, 0)

	def test_valuation_rate_missing_on_make_stock_entry(self):
		item_name = "Test Valuation Rate Missing"
		rm_item = "_Test raw material item"
		make_item(
			item_name,
			{
				"is_stock_item": 1,
				"include_item_in_manufacturing": 1,
			},
		)
		make_item(
			"_Test raw material item",
			{
				"is_stock_item": 1,
				"include_item_in_manufacturing": 1,
			},
		)

		if not frappe.db.get_value("BOM", {"item": item_name}):
			make_bom(item=item_name, raw_materials=[rm_item], rm_qty=1)

		company = "_Test Company with perpetual inventory"
		source_warehouse = create_warehouse("Test Valuation Rate Missing Warehouse", company=company)
		wo = make_wo_order_test_record(
			item=item_name, qty=1, source_warehouse=source_warehouse, company=company
		)

		stock_entry = frappe.get_doc(make_stock_entry(wo.name, "Material Transfer for Manufacture"))
		self.assertRaises(frappe.ValidationError, stock_entry.save)

	def test_wo_completion_with_pl_bom(self):
		from erpnext.manufacturing.doctype.bom.test_bom import (
			create_bom_with_process_loss_item,
			create_process_loss_bom_items,
		)

		qty = 4
		scrap_qty = 0.25  # bom item qty = 1, consider as 25% of FG
		source_warehouse = "Stores - _TC"
		wip_warehouse = "_Test Warehouse - _TC"
		fg_item_non_whole, _, bom_item = create_process_loss_bom_items()

		test_stock_entry.make_stock_entry(
			item_code=bom_item.item_code, target=source_warehouse, qty=4, basic_rate=100
		)

		bom_no = f"BOM-{fg_item_non_whole.item_code}-001"
		if not frappe.db.exists("BOM", bom_no):
			bom_doc = create_bom_with_process_loss_item(
				fg_item_non_whole, bom_item, scrap_qty=scrap_qty, scrap_rate=0, fg_qty=1, is_process_loss=1
			)
			bom_doc.submit()

		wo = make_wo_order_test_record(
			production_item=fg_item_non_whole.item_code,
			bom_no=bom_no,
			wip_warehouse=wip_warehouse,
			qty=qty,
			skip_transfer=1,
			stock_uom=fg_item_non_whole.stock_uom,
		)

		se = frappe.get_doc(make_stock_entry(wo.name, "Material Transfer for Manufacture", qty))
		se.get("items")[0].s_warehouse = "Stores - _TC"
		se.insert()
		se.submit()

		se = frappe.get_doc(make_stock_entry(wo.name, "Manufacture", qty))
		se.insert()
		se.submit()

		# Testing stock entry values
		items = se.get("items")
		self.assertEqual(len(items), 3, "There should be 3 items including process loss.")

		source_item, fg_item, pl_item = items

		total_pl_qty = qty * scrap_qty
		actual_fg_qty = qty - total_pl_qty

		self.assertEqual(pl_item.qty, total_pl_qty)
		self.assertEqual(fg_item.qty, actual_fg_qty)

		# Testing Work Order values
		self.assertEqual(frappe.db.get_value("Work Order", wo.name, "produced_qty"), qty)
		self.assertEqual(frappe.db.get_value("Work Order", wo.name, "process_loss_qty"), total_pl_qty)

	@timeout(seconds=60)
	def test_job_card_scrap_item(self):
		items = [
			"Test FG Item for Scrap Item Test",
			"Test RM Item 1 for Scrap Item Test",
			"Test RM Item 2 for Scrap Item Test",
		]

		company = "_Test Company with perpetual inventory"
		for item_code in items:
			create_item(
				item_code=item_code,
				is_stock_item=1,
				is_purchase_item=1,
				opening_stock=100,
				valuation_rate=10,
				company=company,
				warehouse="Stores - TCP1",
			)

		item = "Test FG Item for Scrap Item Test"
		raw_materials = ["Test RM Item 1 for Scrap Item Test", "Test RM Item 2 for Scrap Item Test"]
		if not frappe.db.get_value("BOM", {"item": item}):
			bom = make_bom(
				item=item, source_warehouse="Stores - TCP1", raw_materials=raw_materials, do_not_save=True
			)
			bom.with_operations = 1
			bom.append(
				"operations",
				{
					"operation": "_Test Operation 1",
					"workstation": "_Test Workstation 1",
					"hour_rate": 20,
					"time_in_mins": 60,
				},
			)

			bom.submit()

		wo_order = make_wo_order_test_record(
			item=item, company=company, planned_start_date=now(), qty=20, skip_transfer=1
		)
		job_card = frappe.db.get_value("Job Card", {"work_order": wo_order.name}, "name")
		update_job_card(job_card)

		stock_entry = frappe.get_doc(make_stock_entry(wo_order.name, "Manufacture", 10))
		for row in stock_entry.items:
			if row.is_scrap_item:
				self.assertEqual(row.qty, 1)

		# Partial Job Card 1 with qty 10
		wo_order = make_wo_order_test_record(
			item=item, company=company, planned_start_date=add_days(now(), 60), qty=20, skip_transfer=1
		)
		job_card = frappe.db.get_value("Job Card", {"work_order": wo_order.name}, "name")
		update_job_card(job_card, 10)

		stock_entry = frappe.get_doc(make_stock_entry(wo_order.name, "Manufacture", 10))
		for row in stock_entry.items:
			if row.is_scrap_item:
				self.assertEqual(row.qty, 2)

		# Partial Job Card 2 with qty 10
		operations = []
		wo_order.load_from_db()
		for row in wo_order.operations:
			n_dict = row.as_dict()
			n_dict["qty"] = 10
			n_dict["pending_qty"] = 10
			operations.append(n_dict)

		make_job_card(wo_order.name, operations)
		job_card = frappe.db.get_value("Job Card", {"work_order": wo_order.name, "docstatus": 0}, "name")
		update_job_card(job_card, 10)

		stock_entry = frappe.get_doc(make_stock_entry(wo_order.name, "Manufacture", 10))
		for row in stock_entry.items:
			if row.is_scrap_item:
				self.assertEqual(row.qty, 2)

	def test_close_work_order(self):
		items = [
			"Test FG Item for Closed WO",
			"Test RM Item 1 for Closed WO",
			"Test RM Item 2 for Closed WO",
		]

		company = "_Test Company with perpetual inventory"
		for item_code in items:
			create_item(
				item_code=item_code,
				is_stock_item=1,
				is_purchase_item=1,
				opening_stock=100,
				valuation_rate=10,
				company=company,
				warehouse="Stores - TCP1",
			)

		item = "Test FG Item for Closed WO"
		raw_materials = ["Test RM Item 1 for Closed WO", "Test RM Item 2 for Closed WO"]
		if not frappe.db.get_value("BOM", {"item": item}):
			bom = make_bom(
				item=item, source_warehouse="Stores - TCP1", raw_materials=raw_materials, do_not_save=True
			)
			bom.with_operations = 1
			bom.append(
				"operations",
				{
					"operation": "_Test Operation 1",
					"workstation": "_Test Workstation 1",
					"hour_rate": 20,
					"time_in_mins": 60,
				},
			)

			bom.submit()

		wo_order = make_wo_order_test_record(
			item=item, company=company, planned_start_date=now(), qty=20, skip_transfer=1
		)
		job_cards = frappe.db.get_value("Job Card", {"work_order": wo_order.name}, "name")

		if len(job_cards) == len(bom.operations):
			for jc in job_cards:
				job_card_doc = frappe.get_doc("Job Card", jc)
				job_card_doc.append(
					"time_logs",
					{"from_time": now(), "time_in_mins": 60, "completed_qty": job_card_doc.for_quantity},
				)

				job_card_doc.submit()

			close_work_order(wo_order, "Closed")
			self.assertEqual(wo_order.get("status"), "Closed")

	def test_fix_time_operations(self):
		bom = frappe.get_doc(
			{
				"doctype": "BOM",
				"item": "_Test FG Item 2",
				"is_active": 1,
				"is_default": 1,
				"quantity": 1.0,
				"with_operations": 1,
				"operations": [
					{
						"operation": "_Test Operation 1",
						"description": "_Test",
						"workstation": "_Test Workstation 1",
						"time_in_mins": 60,
						"operating_cost": 140,
						"fixed_time": 1,
					}
				],
				"items": [
					{
						"amount": 5000.0,
						"doctype": "BOM Item",
						"item_code": "_Test Item",
						"parentfield": "items",
						"qty": 1.0,
						"rate": 5000.0,
					},
				],
			}
		)
		bom.save()
		bom.submit()

		wo1 = make_wo_order_test_record(
			item=bom.item, bom_no=bom.name, qty=1, skip_transfer=1, do_not_submit=1
		)
		wo2 = make_wo_order_test_record(
			item=bom.item, bom_no=bom.name, qty=2, skip_transfer=1, do_not_submit=1
		)

		self.assertEqual(wo1.operations[0].time_in_mins, wo2.operations[0].time_in_mins)

	def test_partial_manufacture_entries(self):
		cancel_stock_entry = []

		frappe.db.set_value(
			"Manufacturing Settings",
			None,
			"backflush_raw_materials_based_on",
			"Material Transferred for Manufacture",
		)

		wo_order = make_wo_order_test_record(planned_start_date=now(), qty=100)
		ste1 = test_stock_entry.make_stock_entry(
			item_code="_Test Item", target="_Test Warehouse - _TC", qty=120, basic_rate=5000.0
		)
		ste2 = test_stock_entry.make_stock_entry(
			item_code="_Test Item Home Desktop 100",
			target="_Test Warehouse - _TC",
			qty=240,
			basic_rate=1000.0,
		)

		cancel_stock_entry.extend([ste1.name, ste2.name])

		sm = frappe.get_doc(make_stock_entry(wo_order.name, "Material Transfer for Manufacture", 100))
		for row in sm.get("items"):
			if row.get("item_code") == "_Test Item":
				row.qty = 110

		sm.submit()
		cancel_stock_entry.append(sm.name)

		s = frappe.get_doc(make_stock_entry(wo_order.name, "Manufacture", 90))
		for row in s.get("items"):
			if row.get("item_code") == "_Test Item":
				self.assertEqual(row.get("qty"), 100)
		s.submit()
		cancel_stock_entry.append(s.name)

		s1 = frappe.get_doc(make_stock_entry(wo_order.name, "Manufacture", 5))
		for row in s1.get("items"):
			if row.get("item_code") == "_Test Item":
				self.assertEqual(row.get("qty"), 5)
		s1.submit()
		cancel_stock_entry.append(s1.name)

		s2 = frappe.get_doc(make_stock_entry(wo_order.name, "Manufacture", 5))
		for row in s2.get("items"):
			if row.get("item_code") == "_Test Item":
				self.assertEqual(row.get("qty"), 5)

		cancel_stock_entry.reverse()
		for ste in cancel_stock_entry:
			doc = frappe.get_doc("Stock Entry", ste)
			doc.cancel()

		frappe.db.set_value("Manufacturing Settings", None, "backflush_raw_materials_based_on", "BOM")

	@change_settings("Manufacturing Settings", {"make_serial_no_batch_from_work_order": 1})
	def test_auto_batch_creation(self):
		from erpnext.manufacturing.doctype.bom.test_bom import create_nested_bom

		fg_item = frappe.generate_hash(length=20)
		child_item = frappe.generate_hash(length=20)

		bom_tree = {fg_item: {child_item: {}}}

		create_nested_bom(bom_tree, prefix="")

		item = frappe.get_doc("Item", fg_item)
		item.has_batch_no = 1
		item.create_new_batch = 0
		item.save()

		try:
			make_wo_order_test_record(item=fg_item)
		except frappe.MandatoryError:
			self.fail("Batch generation causing failing in Work Order")

	@change_settings(
		"Manufacturing Settings",
		{"backflush_raw_materials_based_on": "Material Transferred for Manufacture"},
	)
	def test_manufacture_entry_mapped_idx_with_exploded_bom(self):
		"""Test if WO containing BOM with partial exploded items and scrap items, maps idx correctly."""
		test_stock_entry.make_stock_entry(
			item_code="_Test Item",
			target="_Test Warehouse - _TC",
			basic_rate=5000.0,
			qty=2,
		)
		test_stock_entry.make_stock_entry(
			item_code="_Test Item Home Desktop 100",
			target="_Test Warehouse - _TC",
			basic_rate=1000.0,
			qty=2,
		)

		wo_order = make_wo_order_test_record(
			qty=1,
			use_multi_level_bom=1,
			skip_transfer=1,
		)

		ste_manu = frappe.get_doc(make_stock_entry(wo_order.name, "Manufacture", 1))

		for index, row in enumerate(ste_manu.get("items"), start=1):
			self.assertEqual(index, row.idx)

	@change_settings(
		"Manufacturing Settings",
		{"backflush_raw_materials_based_on": "Material Transferred for Manufacture"},
	)
	def test_work_order_multiple_material_transfer(self):
		"""
		Test transferring multiple RMs in separate Stock Entries.
		"""
		work_order = make_wo_order_test_record(planned_start_date=now(), qty=1)
		test_stock_entry.make_stock_entry(  # stock up RM
			item_code="_Test Item",
			target="_Test Warehouse - _TC",
			qty=1,
			basic_rate=5000.0,
		)
		test_stock_entry.make_stock_entry(  # stock up RM
			item_code="_Test Item Home Desktop 100",
			target="_Test Warehouse - _TC",
			qty=2,
			basic_rate=1000.0,
		)

		transfer_entry = frappe.get_doc(
			make_stock_entry(work_order.name, "Material Transfer for Manufacture", 1)
		)
		del transfer_entry.get("items")[0]  # transfer only one RM
		transfer_entry.submit()

		# WO's "Material Transferred for Mfg" shows all is transferred, one RM is pending
		work_order.reload()
		self.assertEqual(work_order.material_transferred_for_manufacturing, 1)
		self.assertEqual(work_order.required_items[0].transferred_qty, 0)
		self.assertEqual(work_order.required_items[1].transferred_qty, 2)

		final_transfer_entry = frappe.get_doc(  # transfer last RM with For Quantity = 0
			make_stock_entry(work_order.name, "Material Transfer for Manufacture", 0)
		)
		final_transfer_entry.save()

		self.assertEqual(final_transfer_entry.fg_completed_qty, 0.0)
		self.assertEqual(final_transfer_entry.items[0].qty, 1)

		final_transfer_entry.submit()
		work_order.reload()

		# WO's "Material Transferred for Mfg" shows all is transferred, no RM is pending
		self.assertEqual(work_order.material_transferred_for_manufacturing, 1)
		self.assertEqual(work_order.required_items[0].transferred_qty, 1)
		self.assertEqual(work_order.required_items[1].transferred_qty, 2)


def update_job_card(job_card, jc_qty=None):
	employee = frappe.db.get_value("Employee", {"status": "Active"}, "name")
	job_card_doc = frappe.get_doc("Job Card", job_card)
	job_card_doc.set(
		"scrap_items",
		[
			{"item_code": "Test RM Item 1 for Scrap Item Test", "stock_qty": 2},
			{"item_code": "Test RM Item 2 for Scrap Item Test", "stock_qty": 2},
		],
	)

	if jc_qty:
		job_card_doc.for_quantity = jc_qty

	job_card_doc.append(
		"time_logs",
		{
			"from_time": now(),
			"employee": employee,
			"time_in_mins": 60,
			"completed_qty": job_card_doc.for_quantity,
		},
	)

	job_card_doc.submit()


def get_scrap_item_details(bom_no):
	scrap_items = {}
	for item in frappe.db.sql(
		"""select item_code, stock_qty from `tabBOM Scrap Item`
		where parent = %s""",
		bom_no,
		as_dict=1,
	):
		scrap_items[item.item_code] = item.stock_qty

	return scrap_items


def allow_overproduction(fieldname, percentage):
	doc = frappe.get_doc("Manufacturing Settings")
	doc.update({fieldname: percentage})
	doc.save()


def make_wo_order_test_record(**args):
	args = frappe._dict(args)
	if args.company and args.company != "_Test Company":
		warehouse_map = {"fg_warehouse": "_Test FG Warehouse", "wip_warehouse": "_Test WIP Warehouse"}

		for attr, wh_name in warehouse_map.items():
			if not args.get(attr):
				args[attr] = create_warehouse(wh_name, company=args.company)

	wo_order = frappe.new_doc("Work Order")
	wo_order.production_item = args.production_item or args.item or args.item_code or "_Test FG Item"
	wo_order.bom_no = args.bom_no or frappe.db.get_value(
		"BOM", {"item": wo_order.production_item, "is_active": 1, "is_default": 1}
	)
	wo_order.qty = args.qty or 10
	wo_order.wip_warehouse = args.wip_warehouse or "_Test Warehouse - _TC"
	wo_order.fg_warehouse = args.fg_warehouse or "_Test Warehouse 1 - _TC"
	wo_order.scrap_warehouse = args.fg_warehouse or "_Test Scrap Warehouse - _TC"
	wo_order.company = args.company or "_Test Company"
	wo_order.stock_uom = args.stock_uom or "_Test UOM"
	wo_order.use_multi_level_bom = args.use_multi_level_bom or 0
	wo_order.skip_transfer = args.skip_transfer or 0
	wo_order.get_items_and_operations_from_bom()
	wo_order.sales_order = args.sales_order or None
	wo_order.planned_start_date = args.planned_start_date or now()
	wo_order.transfer_material_against = args.transfer_material_against or "Work Order"

	if args.source_warehouse:
		for item in wo_order.get("required_items"):
			item.source_warehouse = args.source_warehouse

	if not args.do_not_save:
		wo_order.insert()

		if not args.do_not_submit:
			wo_order.submit()
	return wo_order


test_records = frappe.get_test_records("Work Order")
