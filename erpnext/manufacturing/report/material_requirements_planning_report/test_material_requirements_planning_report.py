# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.classes.context_managers import freeze_time
from frappe.utils import add_days, flt, formatdate, getdate, today

from erpnext.accounts.doctype.tax_rule.test_tax_rule import make_tax_rule
from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
from erpnext.manufacturing.report.material_requirements_planning_report.material_requirements_planning_report import (
	MaterialRequirementsPlanningReport,
	execute,
	get_item_lead_time,
	make_order,
)
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.tests.utils import ERPNextTestSuite

COMPANY = "_Test Company"
WAREHOUSE = "_Test Warehouse - _TC"
SUPPLIER = "_Test Supplier"
TAX_TEMPLATE = "_Test Purchase Taxes and Charges Template - _TC"
WIP_WAREHOUSE = "_Test Warehouse 1 - _TC"


class TestMaterialRequirementsPlanningReport(ERPNextTestSuite):
	def test_detailed_chart_includes_full_date_range(self):
		with freeze_time("2026-08-12"):
			start_date = add_days(today(), 1)
			delivery_dates = [add_days(start_date, offset) for offset in range(12)]
			rows = [make_chart_row(delivery_date) for delivery_date in delivery_dates]
			rows.append(make_chart_row(delivery_dates[-1], planned_qty=2))

			chart = MaterialRequirementsPlanningReport(frappe._dict()).get_detailed_view_chart_data(rows)

			self.assertEqual(
				chart["data"]["labels"],
				[formatdate(delivery_date, "dd MMM") for delivery_date in delivery_dates],
			)
			self.assertEqual(chart["data"]["datasets"][0]["values"], [1] * 11 + [3])

	def test_forecast_is_counted_once_across_warehouse_rows(self):
		delivery_date = add_days(today(), 5)
		report = MaterialRequirementsPlanningReport(frappe._dict())
		report.mps_data = [
			frappe._dict(
				item_code="_Test Item", delivery_date=delivery_date, planned_qty=qty, warehouse=warehouse
			)
			for qty, warehouse in ((3, "Stores - _TC"), (4, "Finished Goods - _TC"))
		]
		forecast = [frappe._dict(item_code="_Test Item", delivery_date=delivery_date, qty=10)]

		with patch.object(
			MaterialRequirementsPlanningReport, "get_sales_forecast_data", return_value=forecast
		):
			report.update_sales_forecast_data()

		self.assertEqual(sum(max(row.planned_qty, row.sales_forecast_qty) for row in report.mps_data), 10)
		self.assertEqual([row.sales_forecast_qty for row in report.mps_data], [4, 6])

	def test_forecasts_of_one_date_are_added_before_splitting(self):
		delivery_date = add_days(today(), 5)
		report = MaterialRequirementsPlanningReport(frappe._dict())
		report.mps_data = [
			frappe._dict(
				item_code="_Test Item", delivery_date=delivery_date, planned_qty=1, warehouse=warehouse
			)
			for warehouse in ("Stores - _TC", "Finished Goods - _TC")
		]
		forecast = [
			frappe._dict(item_code="_Test Item", delivery_date=delivery_date, qty=1) for _row in range(2)
		]

		with patch.object(
			MaterialRequirementsPlanningReport, "get_sales_forecast_data", return_value=forecast
		):
			report.update_sales_forecast_data()

		self.assertEqual([row.sales_forecast_qty for row in report.mps_data], [1, 1])

	def test_daily_share_of_a_weekly_forecast_keeps_its_total(self):
		report = MaterialRequirementsPlanningReport(frappe._dict())
		dates = [add_days(today(), offset) for offset in range(7)]
		report.mps_data = [
			frappe._dict(item_code="_Test Item", delivery_date=date, planned_qty=1, warehouse="Stores - _TC")
			for date in dates
		]
		forecast = [frappe._dict(item_code="_Test Item", delivery_date=date, qty=10 / 7) for date in dates]

		with patch.object(
			MaterialRequirementsPlanningReport, "get_sales_forecast_data", return_value=forecast
		):
			report.update_sales_forecast_data()

		self.assertAlmostEqual(sum(row.sales_forecast_qty for row in report.mps_data), 10)

	def test_detailed_chart_distinguishes_delivery_dates_across_years(self):
		with freeze_time("2026-08-12"):
			delivery_dates = ["2026-08-15", "2027-08-15"]
			rows = [
				make_chart_row(delivery_dates[0]),
				make_chart_row(delivery_dates[1], planned_qty=2),
			]

			chart = MaterialRequirementsPlanningReport(frappe._dict()).get_detailed_view_chart_data(rows)

			self.assertEqual(
				chart["data"]["labels"],
				[formatdate(delivery_date, "dd MMM yyyy") for delivery_date in delivery_dates],
			)
			self.assertEqual(chart["data"]["datasets"][0]["values"], [1, 2])

	def test_detailed_chart_excludes_past_and_empty_delivery_dates(self):
		with freeze_time("2026-08-12"):
			delivery_dates = [today(), add_days(today(), 1)]
			rows = [
				make_chart_row(add_days(today(), -1)),
				make_chart_row(None),
				*[make_chart_row(delivery_date) for delivery_date in delivery_dates],
			]

			chart = MaterialRequirementsPlanningReport(frappe._dict()).get_detailed_view_chart_data(rows)

			self.assertEqual(
				chart["data"]["labels"],
				[formatdate(delivery_date, "dd MMM") for delivery_date in delivery_dates],
			)

	def test_manufacture_lead_time_preserves_fractional_days(self):
		"""Manufacturing duration must retain fractional days until the report rounds it."""
		item = make_item("_Test MRP Lead Time Item", {"is_stock_item": 1}).name
		frappe.get_doc(
			{
				"doctype": "Item Lead Time",
				"item_code": item,
				"manufacturing_time_in_mins": 7,
				"buffer_time": 2,
			}
		).insert()

		lead_time = get_item_lead_time(item, "Manufacture")
		self.assertAlmostEqual(lead_time, 7 / 1440 + 2, places=8)

	@freeze_time("2026-09-01 10:00:00.123456")
	def test_manufacturing_buffer_moves_release_date_earlier(self):
		plan = make_mrp_plan(self, planned_qty=49, rm_qty=1)
		mps = frappe.get_doc("Master Production Schedule", plan.mps)
		mps.items[0].delivery_date = "2026-09-30"
		mps.save()
		lead_time = frappe.get_doc(
			{"doctype": "Item Lead Time", "item_code": plan.fg_item, "manufacturing_time_in_mins": 30}
		).insert()
		frappe.get_doc(
			{"doctype": "Item Lead Time", "item_code": plan.rm_item, "purchase_time": 3, "buffer_time": 1}
		).insert()

		for buffer_days, expected_days in ((0, 2), (1, 3), (2, 4)):
			with self.subTest(buffer_days=buffer_days):
				lead_time.buffer_time = buffer_days
				lead_time.save()
				rows = get_mrp_rows(mps)
				fg_row, rm_row = rows[plan.fg_item], rows[plan.rm_item]
				self.assertEqual(fg_row.required_qty, 49)
				self.assertEqual(fg_row.lead_time, expected_days)
				self.assertEqual(
					getdate(fg_row.release_date), getdate(add_days("2026-09-30", -expected_days))
				)
				self.assertEqual(rm_row.lead_time, 4)
				self.assertEqual(rm_row.delivery_date, fg_row.release_date)

	def test_manufacturing_duration_boundaries_and_missing_operation_time(self):
		plan = make_mrp_plan(self, planned_qty=49, rm_qty=1)
		mps = frappe.get_doc("Master Production Schedule", plan.mps)
		lead_time = frappe.get_doc({"doctype": "Item Lead Time", "item_code": plan.fg_item}).insert()
		frappe.get_doc({"doctype": "Item Lead Time", "item_code": plan.rm_item, "purchase_time": 3}).insert()

		cases = (
			(30, 48, 0, 1),
			(30, 49, 0, 2),
			(30, 96, 0, 2),
			(31, 47, 0, 2),
			(3000, 1, 0, 3),
			(30, 0.5, 1, 2),
			(30, 0, 1, 0),
			(0, 49, 1, 1),
			(-30, 49, 1, 1),
		)
		for minutes, qty, buffer_days, expected_days in cases:
			with self.subTest(minutes=minutes, qty=qty, buffer_days=buffer_days):
				mps.items[0].planned_qty = qty
				mps.save()
				lead_time.update({"manufacturing_time_in_mins": minutes, "buffer_time": buffer_days})
				if minutes < 0:
					lead_time.db_update()
				else:
					lead_time.save()
				row = get_mrp_rows(mps)[plan.fg_item]
				self.assertEqual(row.lead_time, expected_days)
				self.assertEqual(row.release_date, add_days(row.delivery_date, -expected_days))

	def test_subassembly_buffer_uses_net_required_quantity(self):
		plan = make_mrp_plan(self, planned_qty=49, rm_qty=1)
		parent_item = make_item(properties={"is_stock_item": 1}).name
		parent_bom = make_bom(item=parent_item, raw_materials=[plan.fg_item], rm_qty=2, rate=100)
		self.assertEqual(parent_bom.items[0].bom_no, plan.bom)
		mps = frappe.get_doc("Master Production Schedule", plan.mps)
		mps.items[0].item_code = parent_item
		mps.save()
		for item in (parent_item, plan.fg_item):
			frappe.get_doc(
				{
					"doctype": "Item Lead Time",
					"item_code": item,
					"manufacturing_time_in_mins": 30,
					"buffer_time": 1,
				}
			).insert()
		frappe.get_doc({"doctype": "Item Lead Time", "item_code": plan.rm_item, "purchase_time": 3}).insert()

		rows = get_mrp_rows(mps)
		self.assertEqual(rows[parent_item].lead_time, 3)
		self.assertEqual(rows[plan.fg_item].required_qty, 98)
		self.assertEqual(rows[plan.fg_item].lead_time, 4)
		self.assertEqual(rows[plan.fg_item].delivery_date, rows[parent_item].release_date)
		self.assertEqual(rows[plan.rm_item].delivery_date, rows[plan.fg_item].release_date)

		make_stock_entry(item_code=plan.fg_item, target=WAREHOUSE, qty=50, rate=100)
		rows = get_mrp_rows(mps)
		self.assertEqual(rows[plan.fg_item].required_qty, 48)
		self.assertEqual(rows[plan.fg_item].lead_time, 2)
		self.assertEqual(rows[plan.rm_item].required_qty, 48)
		self.assertEqual(rows[plan.rm_item].lead_time, 3)

	def test_component_lead_time_is_not_added_to_the_parent(self):
		plan = make_mrp_plan(self, rm_qty=1)
		other_rm = make_item(properties={"is_stock_item": 1, "is_purchase_item": 1}).name
		make_bom(item=plan.fg_item, raw_materials=[plan.rm_item, other_rm], rate=100)
		for item in (plan.rm_item, other_rm):
			frappe.get_doc({"doctype": "Item Lead Time", "item_code": item, "purchase_time": 10}).insert()

		rows = get_mrp_rows(frappe.get_doc("Master Production Schedule", plan.mps))

		fg_row = rows[plan.fg_item]
		self.assertEqual(fg_row.lead_time, 0)
		self.assertEqual(fg_row.release_date, fg_row.delivery_date)
		for item in (plan.rm_item, other_rm):
			self.assertEqual(rows[item].delivery_date, fg_row.release_date)
			self.assertEqual(rows[item].release_date, add_days(fg_row.delivery_date, -10))

	def test_manufactured_component_without_bom_keeps_buffer_duration(self):
		plan = make_mrp_plan(self, planned_qty=49, rm_qty=1)
		item = frappe.get_doc("Item", plan.rm_item)
		item.is_purchase_item = 0
		item.save()
		frappe.get_doc(
			{
				"doctype": "Item Lead Time",
				"item_code": plan.rm_item,
				"manufacturing_time_in_mins": 30,
				"buffer_time": 1,
			}
		).insert()

		rows = get_mrp_rows(frappe.get_doc("Master Production Schedule", plan.mps))
		component = rows[plan.rm_item]
		self.assertEqual(component.type_of_material, "Manufacture")
		self.assertFalse(component.bom_no)
		self.assertEqual(component.lead_time, 3)
		self.assertEqual(rows[plan.fg_item].lead_time, 0)
		self.assertEqual(component.delivery_date, rows[plan.fg_item].release_date)

	def test_purchase_item_without_bom_is_purchased(self):
		plan = make_mps_item(
			self,
			{
				"is_stock_item": 1,
				"is_purchase_item": 1,
				"item_defaults": [
					{"company": COMPANY, "default_warehouse": WAREHOUSE, "default_supplier": SUPPLIER}
				],
			},
		)
		self.assertEqual(plan.row.type_of_material, "Purchase")

		make_order([plan.row], COMPANY, warehouse=WAREHOUSE, mps=plan.mps)

		purchase_order = get_created_order(plan.mps, "Purchase Order")
		self.assertEqual([d.item_code for d in purchase_order.items], [plan.item])
		self.assertFalse(frappe.get_all("Work Order", filters={"mps": plan.mps}, pluck="name"))

	def test_make_order_rejects_manufactured_item_without_bom(self):
		plan = make_mps_item(
			self,
			{
				"is_stock_item": 1,
				"is_purchase_item": 0,
				"item_defaults": [{"company": COMPANY, "default_warehouse": WAREHOUSE}],
			},
		)
		self.assertEqual(plan.row.type_of_material, "Manufacture")
		self.assertFalse(plan.row.bom_no)

		with self.assertRaises(frappe.ValidationError) as ctx:
			make_order([plan.row], COMPANY, warehouse=WAREHOUSE, mps=plan.mps)

		self.assertIn("Default BOM", str(ctx.exception))
		self.assertFalse(frappe.get_all("Work Order", filters={"mps": plan.mps}, pluck="name"))
		self.assertFalse(frappe.get_all("Purchase Order", filters={"mps": plan.mps}, pluck="name"))

	def test_make_order_rejects_purchase_item_without_supplier(self):
		plan = make_mps_item(
			self,
			{
				"is_stock_item": 1,
				"is_purchase_item": 1,
				"item_defaults": [{"company": COMPANY, "default_warehouse": WAREHOUSE}],
			},
		)
		self.assertEqual(plan.row.type_of_material, "Purchase")
		self.assertFalse(plan.row.default_supplier)

		with self.assertRaises(frappe.ValidationError) as ctx:
			make_order([plan.row], COMPANY, warehouse=WAREHOUSE, mps=plan.mps)

		self.assertIn("Default Supplier", str(ctx.exception))
		self.assertFalse(frappe.get_all("Purchase Order", filters={"mps": plan.mps}, pluck="name"))

	def test_make_order_falls_back_to_item_group_default_supplier(self):
		group = "_Test MRP Item Group With Supplier"
		if not frappe.db.exists("Item Group", group):
			frappe.get_doc(
				{
					"doctype": "Item Group",
					"item_group_name": group,
					"parent_item_group": "All Item Groups",
					"item_group_defaults": [
						{"company": COMPANY, "default_supplier": SUPPLIER, "default_warehouse": WAREHOUSE}
					],
				}
			).insert()

		plan = make_mps_item(
			self,
			{
				"is_stock_item": 1,
				"is_purchase_item": 1,
				"item_group": group,
				"item_defaults": [{"company": COMPANY, "default_warehouse": WAREHOUSE}],
			},
		)
		self.assertEqual(plan.row.type_of_material, "Purchase")
		self.assertEqual(plan.row.default_supplier, SUPPLIER)

		make_order([plan.row], COMPANY, warehouse=WAREHOUSE, mps=plan.mps)

		self.assertEqual(get_created_order(plan.mps, "Purchase Order").supplier, SUPPLIER)

	def test_make_order_uses_the_bom_passed_on_the_row(self):
		plan = make_mps_item(
			self,
			{
				"is_stock_item": 1,
				"is_purchase_item": 0,
				"item_defaults": [{"company": COMPANY, "default_warehouse": WAREHOUSE}],
			},
		)
		rm_item = make_item(
			properties={
				"is_stock_item": 1,
				"is_purchase_item": 1,
				"item_defaults": [{"company": COMPANY, "default_warehouse": WAREHOUSE}],
			}
		).name
		plan.row.bom_no = make_bom(item=plan.item, raw_materials=[rm_item], rm_qty=1, rate=100).name

		make_order([plan.row], COMPANY, warehouse=WAREHOUSE, mps=plan.mps)

		work_order = get_created_order(plan.mps, "Work Order")
		self.assertEqual(work_order.production_item, plan.item)
		self.assertEqual(work_order.bom_no, plan.row.bom_no)

	def test_make_order_creates_draft_purchase_and_work_orders(self):
		plan = make_mrp_plan(self)

		make_order(plan.rows, COMPANY, warehouse=WAREHOUSE, mps=plan.mps)

		purchase_order = get_created_order(plan.mps, "Purchase Order")
		self.assertEqual(purchase_order.docstatus, 0)
		self.assertEqual(purchase_order.supplier, SUPPLIER)
		self.assertEqual([d.item_code for d in purchase_order.items], [plan.rm_item])
		self.assertEqual(purchase_order.items[0].qty, plan.planned_qty * plan.rm_qty)

		work_order = get_created_order(plan.mps, "Work Order")
		self.assertEqual(work_order.docstatus, 0)
		self.assertEqual(work_order.production_item, plan.fg_item)
		self.assertEqual(work_order.bom_no, plan.bom)
		self.assertEqual(work_order.qty, plan.planned_qty)

	def test_order_outside_the_mps_is_kept_beside_its_planned_orders(self):
		delivery_date = add_days(today(), 5)
		report = MaterialRequirementsPlanningReport(frappe._dict())
		report.mps_data = [frappe._dict(item_code="_Test Item", delivery_date=delivery_date, planned_qty=10)]
		other_order = frappe._dict(item_code="_Test Item", delivery_date=delivery_date, adhoc_qty=5)
		planned_order = frappe._dict(item_code="_Test Item", delivery_date=delivery_date, adhoc_qty=10)

		rows = list(report.get_demand_beyond_mps([other_order], [planned_order]))

		self.assertEqual([row.adhoc_qty for row in rows], [5])

	def test_supply_after_an_earlier_sale_does_not_cover_it(self):
		report = MaterialRequirementsPlanningReport(frappe._dict())
		report._so_details = {("_Test Item", add_days(today(), 25)): frappe._dict(qty=7)}
		report._po_details = {("_Test Item", add_days(today(), 28)): frappe._dict(qty=7)}
		row = frappe._dict(item_code="_Test Item", delivery_date=add_days(today(), 30), planned_qty=0)

		report.add_non_planned_so(row)
		row.required_qty = flt(row.planned_qty)
		report.add_po_details(row)

		self.assertEqual(row.required_qty, 7)

	def test_supply_covers_the_later_demand_merged_into_a_row(self):
		report = MaterialRequirementsPlanningReport(frappe._dict())
		report._so_details = {("_Test Item", add_days(today(), 25)): frappe._dict(qty=7)}
		report._po_details = {("_Test Item", add_days(today(), 28)): frappe._dict(qty=10)}
		row = frappe._dict(item_code="_Test Item", delivery_date=add_days(today(), 30), planned_qty=10)

		report.add_non_planned_so(row)
		row.required_qty = flt(row.planned_qty)
		report.add_po_details(row)

		self.assertEqual(row.required_qty, 7)
		self.assertEqual(row.po_ordered_qty, 10)

	@ERPNextTestSuite.change_settings("Stock Settings", {"enable_stock_reservation": 1})
	def test_free_stock_counts_a_work_order_reservation_once(self):
		from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
		from erpnext.manufacturing.report.material_requirements_planning_report.material_requirements_planning_report import (
			get_free_stock,
		)

		material = make_item(properties={"is_stock_item": 1, "valuation_rate": 10}).name
		fg_item = make_item(properties={"is_stock_item": 1}).name
		bom = make_bom(item=fg_item, raw_materials=[material])
		make_stock_entry(item_code=material, target=WAREHOUSE, qty=20, basic_rate=10)
		make_wo_order_test_record(
			item=fg_item, bom_no=bom.name, qty=10, source_warehouse=WAREHOUSE, reserve_stock=1
		)
		report = MaterialRequirementsPlanningReport(frappe._dict(warehouse=WAREHOUSE))
		report.fg_items, report.rm_items = [], [material]

		bin_details = report.get_item_wise_bin_details()[material]

		self.assertEqual(get_free_stock(bin_details), 10)

	@ERPNextTestSuite.change_settings("Stock Settings", {"enable_stock_reservation": 1})
	def test_stock_reserved_in_wip_after_transfer_is_not_free(self):
		from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
		from erpnext.manufacturing.doctype.work_order.work_order import (
			make_stock_entry as make_wo_stock_entry,
		)
		from erpnext.manufacturing.report.material_requirements_planning_report.material_requirements_planning_report import (
			get_free_stock,
		)

		material = make_item(properties={"is_stock_item": 1, "valuation_rate": 10}).name
		fg_item = make_item(properties={"is_stock_item": 1}).name
		bom = make_bom(item=fg_item, raw_materials=[material])
		make_stock_entry(item_code=material, target=WAREHOUSE, qty=20, basic_rate=10)
		work_order = make_wo_order_test_record(
			item=fg_item,
			bom_no=bom.name,
			qty=10,
			source_warehouse=WAREHOUSE,
			wip_warehouse=WIP_WAREHOUSE,
			reserve_stock=1,
		)
		frappe.get_doc(make_wo_stock_entry(work_order.name, "Material Transfer for Manufacture", 10)).submit()
		report = MaterialRequirementsPlanningReport(frappe._dict())
		report.fg_items, report.rm_items = [], [material]

		bin_details = report.get_item_wise_bin_details()[material]

		self.assertEqual(get_free_stock(bin_details), 10)

	def test_make_order_skips_rows_that_are_already_covered(self):
		"""
		A row whose requirement is met by stock or by an order placed earlier has nothing left
		to order. It must be left out instead of failing, and the rows beside it must still be
		created.
		"""
		plan = make_mrp_plan(self)
		covered_row, remaining_rows = plan.rows[0], plan.rows[1:]
		self.assertTrue(remaining_rows, msg="the plan needs a second row to order")
		covered_row.required_qty = 0

		make_order(plan.rows, COMPANY, warehouse=WAREHOUSE, mps=plan.mps)

		ordered_items = [
			row.item_code
			for doctype in ("Purchase Order", "Work Order")
			for order in frappe.get_all(doctype, filters={"mps": plan.mps}, pluck="name")
			for row in get_ordered_items(doctype, order)
		]
		self.assertNotIn(covered_row.item_code, ordered_items)
		self.assertEqual(sorted(ordered_items), sorted([row.item_code for row in remaining_rows]))

	def test_make_order_creates_nothing_when_every_row_is_covered(self):
		plan = make_mrp_plan(self)
		for row in plan.rows:
			row.required_qty = 0

		make_order(plan.rows, COMPANY, warehouse=WAREHOUSE, mps=plan.mps)

		for doctype in ("Purchase Order", "Work Order"):
			self.assertFalse(frappe.get_all(doctype, filters={"mps": plan.mps}, pluck="name"))

	def test_make_order_ignores_a_requirement_left_over_by_rounding(self):
		"""What is left of a covered row after subtracting is not a quantity worth ordering."""
		plan = make_mrp_plan(self)
		for row in plan.rows:
			row.required_qty = 0.0000000001

		make_order(plan.rows, COMPANY, warehouse=WAREHOUSE, mps=plan.mps)

		for doctype in ("Purchase Order", "Work Order"):
			self.assertFalse(frappe.get_all(doctype, filters={"mps": plan.mps}, pluck="name"))

	def test_work_order_keeps_the_company_wip_warehouse(self):
		"""
		The item's own warehouse is where the finished goods go, the work in progress warehouse
		stays the one the company keeps for it.
		"""
		plan = make_mrp_plan(self)
		frappe.db.set_value("Company", COMPANY, "default_wip_warehouse", WIP_WAREHOUSE)

		make_order(plan.rows, COMPANY, warehouse=WAREHOUSE, mps=plan.mps)

		work_order = get_created_order(plan.mps, "Work Order")
		self.assertEqual(work_order.wip_warehouse, WIP_WAREHOUSE)

	def test_purchase_order_gets_defaults_from_set_missing_values(self):
		plan = make_mrp_plan(self)
		make_tax_rule(tax_type="Purchase", purchase_tax_template=TAX_TEMPLATE, priority=1, save=1)
		frappe.get_doc(
			{
				"doctype": "Item Price",
				"item_code": plan.rm_item,
				"price_list": "Standard Buying",
				"price_list_rate": 100,
			}
		).insert()

		make_order(plan.rows, COMPANY, warehouse=WAREHOUSE, mps=plan.mps)

		purchase_order = get_created_order(plan.mps, "Purchase Order")
		self.assertEqual(purchase_order.buying_price_list, "Standard Buying")
		self.assertEqual(purchase_order.items[0].rate, 100)
		template = frappe.get_doc("Purchase Taxes and Charges Template", TAX_TEMPLATE)
		self.assertEqual(purchase_order.taxes_and_charges, TAX_TEMPLATE)
		self.assertEqual([d.rate for d in purchase_order.taxes], [d.rate for d in template.taxes])

		net_total = flt(purchase_order.net_total)
		self.assertEqual(
			purchase_order.grand_total, net_total + net_total * flt(template.taxes[0].rate) / 100
		)

	def test_buckets_include_the_period_that_ends_on_a_bucket_boundary(self):
		"""A to_date landing on a bucket's first day must still get that bucket's column."""
		cases = [
			("Monthly", "2026-11-01", "2026-12-01", ["2026-11-01", "2026-12-01"]),
			("Monthly", "2026-12-01", "2026-12-01", ["2026-12-01"]),
			("Daily", "2026-11-30", "2026-12-01", ["2026-11-30", "2026-12-01"]),
			("Weekly", "2026-11-30", "2026-12-07", ["2026-11-30", "2026-12-07"]),
		]

		for bucket_size, from_date, to_date, bucket_starts in cases:
			with self.subTest(bucket_size=bucket_size, to_date=to_date):
				report = MaterialRequirementsPlanningReport(
					frappe._dict({"bucket_size": bucket_size, "from_date": from_date, "to_date": to_date})
				)

				dates = report.get_dates()
				self.assertEqual(
					[getdate(d["from_date"]) for d in dates],
					[getdate(start) for start in bucket_starts],
				)
				if bucket_size == "Monthly":
					self.assertEqual(
						[d["label"] for d in dates],
						[formatdate(start, "MMM YYYY") for start in bucket_starts],
					)

	def test_raw_material_qty_uses_the_bom_quantity(self):
		plan = make_mrp_plan(self)
		bom = make_bom(item=plan.fg_item, quantity=10, raw_materials=[plan.rm_item], rm_qty=20, rate=100)
		self.assertEqual(frappe.db.get_value("Item", plan.fg_item, "default_bom"), bom.name)

		rows = get_mrp_rows(frappe.get_doc("Master Production Schedule", plan.mps))

		self.assertEqual(rows[plan.rm_item].planned_qty, 20)
		self.assertEqual(rows[plan.rm_item].required_qty, 20)

	def test_sales_order_in_the_mps_is_not_added_again(self):
		plan = make_mrp_plan(self)
		make_mrp_sales_order(plan.fg_item, 10, add_days(today(), 30))

		rows = get_mrp_row_list(frappe.get_doc("Master Production Schedule", plan.mps))

		fg_rows = [row for row in rows if row.item_code == plan.fg_item]
		self.assertEqual([(row.planned_qty, row.required_qty) for row in fg_rows], [(10, 10)])
		self.assertEqual(sum(row.required_qty for row in rows if row.item_code == plan.rm_item), 20)

		make_mrp_sales_order(plan.fg_item, 5, add_days(today(), 30))
		rows = get_mrp_row_list(frappe.get_doc("Master Production Schedule", plan.mps))
		self.assertEqual(sum(row.required_qty for row in rows if row.item_code == plan.fg_item), 15)

	def test_purchase_order_qty_is_converted_to_the_purchase_uom(self):
		plan = make_mrp_plan(self, planned_qty=12)
		item = frappe.get_doc("Item", plan.rm_item)
		item.append("uoms", {"uom": "Box", "conversion_factor": 12})
		item.purchase_uom = "Box"
		item.save()
		mps = frappe.get_doc("Master Production Schedule", plan.mps)

		make_order(get_mrp_row_list(mps), COMPANY, warehouse=WAREHOUSE, mps=plan.mps)

		purchase_order = get_created_order(plan.mps, "Purchase Order")
		self.assertEqual(
			[(row.qty, row.uom, row.conversion_factor, row.stock_qty) for row in purchase_order.items],
			[(2, "Box", 12, 24)],
		)

	def test_safety_stock_is_ordered_once_and_only_when_stock_is_short(self):
		def make_plan_with_safety_stock():
			plan = make_mrp_plan(self)
			frappe.db.set_value("Item", plan.fg_item, "safety_stock", 4)
			frappe.db.set_value("Item", plan.rm_item, "safety_stock", 5)
			mps = frappe.get_doc("Master Production Schedule", plan.mps)
			for days in (40, 50):
				mps.append(
					"items",
					{
						"item_code": plan.fg_item,
						"warehouse": WAREHOUSE,
						"delivery_date": add_days(today(), days),
						"planned_qty": 10,
						"uom": mps.items[0].uom,
					},
				)
			mps.save()
			return plan, mps

		def required(rows, item_code):
			return [row.required_qty for row in rows if row.item_code == item_code]

		plan, mps = make_plan_with_safety_stock()
		rows = get_mrp_row_list(mps, add_safety_stock=1)
		self.assertEqual(required(rows, plan.fg_item), [14, 10, 10])
		self.assertEqual(sum(required(rows, plan.rm_item)), 73)

		make_stock_entry(item_code=plan.fg_item, target=WAREHOUSE, qty=50, rate=100)
		make_stock_entry(item_code=plan.rm_item, target=WAREHOUSE, qty=100, rate=100)
		rows = get_mrp_row_list(mps, add_safety_stock=1)
		self.assertEqual(required(rows, plan.fg_item), [0, 0, 0])
		self.assertEqual(sum(required(rows, plan.rm_item)), 0)

	def test_stock_committed_to_work_orders_is_not_on_hand(self):
		plan = make_mrp_plan(self, rm_qty=1)
		make_stock_entry(item_code=plan.rm_item, target=WAREHOUSE, qty=10, rate=100)
		other_fg = make_item(properties={"is_stock_item": 1}).name
		other_bom = make_bom(item=other_fg, raw_materials=[plan.rm_item], rm_qty=1, rate=100)
		make_wo_order_test_record(item=other_fg, bom_no=other_bom.name, qty=10, source_warehouse=WAREHOUSE)

		rows = get_mrp_rows(frappe.get_doc("Master Production Schedule", plan.mps))

		self.assertEqual(rows[plan.rm_item].in_hand_qty, 0)
		self.assertEqual(rows[plan.rm_item].required_qty, 10)

	def test_raw_material_sales_orders_raise_the_requirement(self):
		plan = make_mrp_plan(self, rm_qty=1)
		mps = frappe.get_doc("Master Production Schedule", plan.mps)
		make_mrp_sales_order(plan.rm_item, 7, add_days(today(), 25))

		rm_row = get_mrp_rows(mps)[plan.rm_item]
		self.assertEqual((rm_row.planned_qty, rm_row.adhoc_qty, rm_row.required_qty), (17, 7, 17))

		make_mrp_sales_order(plan.rm_item, 7, add_days(today(), 30))
		rm_row = get_mrp_rows(mps)[plan.rm_item]
		self.assertEqual((rm_row.planned_qty, rm_row.adhoc_qty, rm_row.required_qty), (24, 14, 24))

	def test_open_orders_booked_before_from_date_are_demand(self):
		plan = make_mrp_plan(self)
		make_mrp_sales_order(plan.fg_item, 6, add_days(today(), 20), transaction_date=add_days(today(), -10))
		make_mrp_sales_order(plan.fg_item, 4, add_days(today(), 20))

		rows = get_mrp_row_list(frappe.get_doc("Master Production Schedule", plan.mps))

		self.assertEqual(sum(flt(row.adhoc_qty) for row in rows if row.item_code == plan.fg_item), 10)

	def test_sub_assembly_work_order_uses_the_stock_uom(self):
		plan = make_mrp_plan(self)
		sub_assembly = frappe.get_doc("Item", plan.fg_item)
		sub_assembly.append("uoms", {"uom": "Box", "conversion_factor": 12})
		sub_assembly.purchase_uom = "Box"
		sub_assembly.save()
		parent_item = make_item(
			properties={
				"is_stock_item": 1,
				"item_defaults": [{"company": COMPANY, "default_warehouse": WAREHOUSE}],
			}
		).name
		make_bom(item=parent_item, raw_materials=[plan.fg_item], rate=100)
		mps = frappe.get_doc("Master Production Schedule", plan.mps)
		mps.items[0].item_code = parent_item
		mps.save()

		make_order(get_mrp_row_list(mps), COMPANY, warehouse=WAREHOUSE, mps=plan.mps)

		work_order = frappe.get_doc("Work Order", {"mps": plan.mps, "production_item": plan.fg_item})
		self.assertEqual(work_order.stock_uom, sub_assembly.stock_uom)

	def test_planned_purchase_order_shows_every_order_used(self):
		plan = make_mrp_plan(self, rm_qty=1)
		for days, qty in ((1, 5), (2, 3)):
			purchase_order = create_purchase_order(item_code=plan.rm_item, qty=qty, do_not_save=True)
			purchase_order.schedule_date = purchase_order.items[0].schedule_date = add_days(today(), days)
			purchase_order.insert()
			purchase_order.submit()

		rm_row = get_mrp_rows(frappe.get_doc("Master Production Schedule", plan.mps))[plan.rm_item]

		self.assertEqual((rm_row.po_ordered_qty, rm_row.required_qty), (8, 2))


def make_chart_row(delivery_date, planned_qty=1):
	return frappe._dict(
		{
			"delivery_date": delivery_date,
			"planned_qty": planned_qty,
			"in_hand_qty": 0,
			"po_ordered_qty": 0,
			"wo_ordered_qty": 0,
		}
	)


def make_mps_item(test_case, item_properties, planned_qty=10):
	item = make_item(properties=item_properties).name
	mps = frappe.get_doc(
		{
			"doctype": "Master Production Schedule",
			"company": COMPANY,
			"posting_date": today(),
			"from_date": today(),
			"parent_warehouse": WAREHOUSE,
			"items": [
				{
					"item_code": item,
					"warehouse": WAREHOUSE,
					"delivery_date": add_days(today(), 30),
					"planned_qty": planned_qty,
					"uom": frappe.get_cached_value("Item", item, "stock_uom"),
				}
			],
		}
	)
	mps.insert()

	_, data, _, _ = execute(
		frappe._dict(
			{
				"company": COMPANY,
				"from_date": today(),
				"to_date": add_days(today(), 90),
				"warehouse": WAREHOUSE,
				"mps": mps.name,
				"type_of_material": "All",
				"add_safety_stock": 0,
			}
		)
	)
	rows = [row for row in data if row.get("item_code")]
	test_case.assertTrue(rows, msg="the report returned no rows to create orders from")

	return frappe._dict(item=item, mps=mps.name, row=rows[0], rows=rows)


def make_mrp_plan(test_case, planned_qty=10, rm_qty=2):
	"""Build a finished good with a submitted BOM and an MPS demanding it, then return the
	report's own output rows -- the same payload the report's client sends to `make_order`."""
	rm_item = make_item(
		properties={
			"is_stock_item": 1,
			"is_purchase_item": 1,
			"item_defaults": [
				{"company": COMPANY, "default_warehouse": WAREHOUSE, "default_supplier": SUPPLIER}
			],
		}
	).name
	fg_item = make_item(
		properties={
			"is_stock_item": 1,
			"item_defaults": [{"company": COMPANY, "default_warehouse": WAREHOUSE}],
		}
	).name

	# on_submit sets Item.default_bom, which is how the report finds the raw materials
	bom = make_bom(item=fg_item, raw_materials=[rm_item], rm_qty=rm_qty, rate=100).name

	mps = frappe.get_doc(
		{
			"doctype": "Master Production Schedule",
			"company": COMPANY,
			"posting_date": today(),
			"from_date": today(),
			"parent_warehouse": WAREHOUSE,
			"items": [
				{
					"item_code": fg_item,
					"warehouse": WAREHOUSE,
					"delivery_date": add_days(today(), 30),
					"planned_qty": planned_qty,
					"uom": frappe.get_cached_value("Item", fg_item, "stock_uom"),
				}
			],
		}
	)
	# left in draft: on_submit enqueues MRP Log creation in a background job
	mps.insert()

	_, data, _, _ = execute(
		frappe._dict(
			{
				"company": COMPANY,
				"from_date": today(),
				"to_date": add_days(today(), 90),
				"warehouse": WAREHOUSE,
				"mps": mps.name,
				"type_of_material": "All",
				"add_safety_stock": 0,
			}
		)
	)

	# the report separates each finished good with a blank row
	rows = [row for row in data if row.get("item_code")]
	test_case.assertTrue(rows, msg="the report returned no rows to create orders from")

	return frappe._dict(
		rm_item=rm_item,
		fg_item=fg_item,
		bom=bom,
		mps=mps.name,
		planned_qty=planned_qty,
		rm_qty=rm_qty,
		rows=rows,
	)


def get_mrp_rows(mps):
	return {row.item_code: row for row in get_mrp_row_list(mps)}


def get_mrp_row_list(mps, **filters):
	# Changing settings and refreshing the report happens in separate requests in Desk.
	frappe.local.request_cache.clear()
	_, rows, _, _ = execute(
		frappe._dict(
			{
				"company": mps.company,
				"warehouse": mps.parent_warehouse,
				"mps": mps.name,
				"from_date": mps.from_date,
				"to_date": mps.to_date,
				"type_of_material": "All",
				"bucket_size": "Daily",
				"add_safety_stock": 0,
				**filters,
			}
		)
	)
	return [row for row in rows if row.get("item_code")]


def make_mrp_sales_order(item_code, qty, delivery_date, transaction_date=None):
	sales_order = make_sales_order(
		item_code=item_code,
		qty=qty,
		warehouse=WAREHOUSE,
		transaction_date=transaction_date or today(),
		do_not_save=True,
	)
	sales_order.delivery_date = delivery_date
	sales_order.items[0].delivery_date = delivery_date
	sales_order.insert()
	sales_order.submit()
	return sales_order


def get_ordered_items(doctype, order):
	child_doctype = "Purchase Order Item" if doctype == "Purchase Order" else None
	if not child_doctype:
		return frappe.get_all(doctype, filters={"name": order}, fields=["production_item as item_code"])

	return frappe.get_all(child_doctype, filters={"parent": order}, fields=["item_code"])


def get_created_order(mps, doctype):
	names = frappe.get_all(doctype, filters={"mps": mps}, pluck="name")
	if len(names) != 1:
		frappe.throw(f"Expected exactly one {doctype} for {mps}, got {names}")

	return frappe.get_doc(doctype, names[0])
