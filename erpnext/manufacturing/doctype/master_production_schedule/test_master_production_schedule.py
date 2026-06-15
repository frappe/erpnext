# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import math

import frappe
from frappe.utils import add_days, getdate, nowdate

from erpnext.manufacturing.doctype.master_production_schedule.master_production_schedule import (
	get_item_lead_time,
)
from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
from erpnext.stock.doctype.item.test_item import create_item
from erpnext.tests.utils import ERPNextTestSuite


def make_mps(**args):
	"""Build (but do not insert) a Master Production Schedule controller for unit-testing helpers."""
	args = frappe._dict(args)
	return frappe.get_doc(
		{
			"doctype": "Master Production Schedule",
			"company": args.company or "_Test Company",
			"posting_date": args.posting_date or nowdate(),
			"from_date": args.from_date or nowdate(),
			"to_date": args.to_date,
			"parent_warehouse": args.parent_warehouse,
		}
	)


def set_item_lead_time(item_code, manufacturing_time_in_mins=0, purchase_time=0, buffer_time=0):
	"""Create/replace an Item Lead Time record for the given item (autoname is field:item_code)."""
	if frappe.db.exists("Item Lead Time", item_code):
		frappe.delete_doc("Item Lead Time", item_code, force=True)

	doc = frappe.get_doc(
		{
			"doctype": "Item Lead Time",
			"item_code": item_code,
			"manufacturing_time_in_mins": manufacturing_time_in_mins,
			"purchase_time": purchase_time,
			"buffer_time": buffer_time,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc


class TestMasterProductionSchedule(ERPNextTestSuite):
	# ------------------------------------------------------------------
	# get_item_wise_mps_data: aggregation of demand by (item_code, delivery_date)
	# ------------------------------------------------------------------
	def test_item_wise_data_aggregates_same_item_and_date(self):
		mps = make_mps()
		delivery_date = getdate("2026-01-10")
		demand = [
			frappe._dict(
				{"item_code": "ITEM-A", "delivery_date": delivery_date, "stock_uom": "Nos", "qty": 4}
			),
			frappe._dict(
				{"item_code": "ITEM-A", "delivery_date": delivery_date, "stock_uom": "Nos", "qty": 6}
			),
		]

		result = mps.get_item_wise_mps_data(demand)

		# Two demand rows for the same (item, date) collapse into one aggregated key.
		self.assertEqual(len(result), 1)
		key = ("ITEM-A", delivery_date)
		self.assertIn(key, result)
		self.assertAlmostEqual(result[key].qty, 10.0, places=2)
		self.assertEqual(result[key].item_code, "ITEM-A")
		self.assertEqual(result[key].delivery_date, delivery_date)
		# order_release_date defaults to the delivery date before lead-time math runs.
		self.assertEqual(result[key].order_release_date, delivery_date)

	def test_item_wise_data_keeps_distinct_keys(self):
		mps = make_mps()
		date_one = getdate("2026-01-10")
		date_two = getdate("2026-01-12")
		demand = [
			frappe._dict({"item_code": "ITEM-A", "delivery_date": date_one, "stock_uom": "Nos", "qty": 5}),
			frappe._dict({"item_code": "ITEM-A", "delivery_date": date_two, "stock_uom": "Nos", "qty": 7}),
			frappe._dict({"item_code": "ITEM-B", "delivery_date": date_one, "stock_uom": "Nos", "qty": 3}),
		]

		result = mps.get_item_wise_mps_data(demand)

		# Different dates (or items) must remain separate buckets.
		self.assertEqual(len(result), 3)
		self.assertAlmostEqual(result[("ITEM-A", date_one)].qty, 5.0, places=2)
		self.assertAlmostEqual(result[("ITEM-A", date_two)].qty, 7.0, places=2)
		self.assertAlmostEqual(result[("ITEM-B", date_one)].qty, 3.0, places=2)

	def test_item_wise_data_empty_demand(self):
		mps = make_mps()
		# Empty demand window must not crash and must yield an empty schedule.
		self.assertEqual(mps.get_item_wise_mps_data([]), {})

	# ------------------------------------------------------------------
	# add_mps_data: order_release_date = delivery_date - ceil(cumulative_lead_time)
	# ------------------------------------------------------------------
	def test_add_mps_data_order_release_date(self):
		mps = make_mps()
		delivery_date = getdate("2026-02-20")
		data = frappe._dict(
			{
				("ITEM-A", delivery_date): frappe._dict(
					{
						"item_code": "ITEM-A",
						"delivery_date": delivery_date,
						"stock_uom": "Nos",
						"qty": 8.0,
						"cumulative_lead_time": 5.0,
						"order_release_date": delivery_date,
					}
				)
			}
		)

		mps.add_mps_data(data)

		self.assertEqual(len(mps.items), 1)
		row = mps.items[0]
		# Release the order 5 days before the required delivery date.
		self.assertEqual(getdate(row.order_release_date), add_days(delivery_date, -5))
		self.assertAlmostEqual(row.planned_qty, 8.0, places=2)
		self.assertEqual(row.uom, "Nos")
		self.assertEqual(row.cumulative_lead_time, 5)

	def test_add_mps_data_ceils_fractional_lead_time(self):
		mps = make_mps()
		delivery_date = getdate("2026-02-20")
		data = frappe._dict(
			{
				("ITEM-A", delivery_date): frappe._dict(
					{
						"item_code": "ITEM-A",
						"delivery_date": delivery_date,
						"stock_uom": "Nos",
						"qty": 2.0,
						# 3.2 days of lead time must round up to a whole 4 days.
						"cumulative_lead_time": 3.2,
						"order_release_date": delivery_date,
					}
				)
			}
		)

		mps.add_mps_data(data)

		row = mps.items[0]
		self.assertEqual(row.cumulative_lead_time, 4)
		self.assertEqual(getdate(row.order_release_date), add_days(delivery_date, -4))

	def test_add_mps_data_warehouse_falls_back_to_parent(self):
		mps = make_mps(parent_warehouse="_Test Warehouse - _TC")
		delivery_date = getdate("2026-03-01")
		data = frappe._dict(
			{
				("ITEM-A", delivery_date): frappe._dict(
					{
						"item_code": "ITEM-A",
						"delivery_date": delivery_date,
						"stock_uom": "Nos",
						"qty": 1.0,
						"cumulative_lead_time": 0.0,
						"order_release_date": delivery_date,
						# no warehouse set on the demand row
					}
				)
			}
		)

		mps.add_mps_data(data)

		row = mps.items[0]
		# Missing warehouse should fall back to the MPS parent warehouse.
		self.assertEqual(row.warehouse, "_Test Warehouse - _TC")
		# Zero lead time leaves the release date equal to the delivery date.
		self.assertEqual(getdate(row.order_release_date), delivery_date)

	def test_add_mps_data_sorted_by_delivery_date(self):
		mps = make_mps()
		later = getdate("2026-04-10")
		earlier = getdate("2026-04-01")
		data = frappe._dict(
			{
				("ITEM-A", later): frappe._dict(
					{
						"item_code": "ITEM-A",
						"delivery_date": later,
						"stock_uom": "Nos",
						"qty": 1.0,
						"cumulative_lead_time": 0.0,
						"order_release_date": later,
					}
				),
				("ITEM-B", earlier): frappe._dict(
					{
						"item_code": "ITEM-B",
						"delivery_date": earlier,
						"stock_uom": "Nos",
						"qty": 1.0,
						"cumulative_lead_time": 0.0,
						"order_release_date": earlier,
					}
				),
			}
		)

		mps.add_mps_data(data)

		# Rows are appended in ascending delivery-date order regardless of input order.
		self.assertEqual([getdate(r.delivery_date) for r in mps.items], [earlier, later])

	# ------------------------------------------------------------------
	# set_to_date: derives to_date from the latest item delivery date
	# ------------------------------------------------------------------
	def test_set_to_date_uses_latest_delivery_date(self):
		mps = make_mps()
		mps.append("items", {"item_code": "ITEM-A", "delivery_date": getdate("2026-05-05")})
		mps.append("items", {"item_code": "ITEM-B", "delivery_date": getdate("2026-05-20")})
		mps.append("items", {"item_code": "ITEM-C", "delivery_date": getdate("2026-05-12")})

		mps.set_to_date()

		self.assertEqual(getdate(mps.to_date), getdate("2026-05-20"))

	def test_set_to_date_no_items(self):
		mps = make_mps()
		# Without items or a forecast, to_date must reset to None (no crash).
		mps.set_to_date()
		self.assertIsNone(mps.to_date)

	# ------------------------------------------------------------------
	# get_distinct_items / get_items_for_mps: pure list helpers
	# ------------------------------------------------------------------
	def test_get_distinct_items(self):
		mps = make_mps()
		data = [
			frappe._dict({"item_code": "ITEM-A"}),
			frappe._dict({"item_code": "ITEM-B"}),
			frappe._dict({"item_code": "ITEM-A"}),
		]
		self.assertEqual(mps.get_distinct_items(data), ["ITEM-A", "ITEM-B"])

	def test_get_items_for_mps_without_selection(self):
		mps = make_mps()
		# No select_items configured -> nothing to constrain on.
		self.assertIsNone(mps.get_items_for_mps())

	# ------------------------------------------------------------------
	# get_item_lead_time: (manufacturing_time_in_mins / 1440) + purchase_time + buffer_time
	# ------------------------------------------------------------------
	def test_get_item_lead_time_computation(self):
		item = create_item("_Test MPS Lead Time Item", valuation_rate=100).item_code
		# 1440 mins == 1 day; + 3 purchase days + 2 buffer days == 6 days total.
		set_item_lead_time(item, manufacturing_time_in_mins=1440, purchase_time=3, buffer_time=2)

		self.assertAlmostEqual(get_item_lead_time(item), 6.0, places=2)

	def test_get_item_lead_time_missing_record(self):
		item = create_item("_Test MPS No Lead Time Item", valuation_rate=100).item_code
		# No Item Lead Time record exists for this item -> zero.
		self.assertEqual(get_item_lead_time(item), 0)

	# ------------------------------------------------------------------
	# get_cumulative_lead_time: recursive BOM lead-time walk
	# ------------------------------------------------------------------
	def test_cumulative_lead_time_item_without_bom(self):
		item = create_item("_Test MPS Standalone", valuation_rate=100).item_code
		set_item_lead_time(item, purchase_time=4)

		mps = make_mps()
		# With no BOM, the cumulative lead time is just the item's own lead time.
		self.assertAlmostEqual(mps.get_cumulative_lead_time(item, None), 4.0, places=2)

	def test_cumulative_lead_time_multi_level_bom(self):
		# Raw material -> sub-assembly -> finished good critical path.
		raw = create_item("_Test MPS Raw Material", valuation_rate=100).item_code
		sub_assembly = create_item("_Test MPS Sub Assembly", valuation_rate=200).item_code
		finished_good = create_item("_Test MPS Finished Good", valuation_rate=300).item_code

		set_item_lead_time(raw, purchase_time=2)
		set_item_lead_time(sub_assembly, manufacturing_time_in_mins=1440)  # 1 day
		set_item_lead_time(finished_good, manufacturing_time_in_mins=2880)  # 2 days

		# Sub-assembly BOM consumes the raw material; FG BOM consumes the sub-assembly.
		# is_default on the sub-assembly BOM wires up BOM Item.bom_no for the recursion.
		make_bom(item=sub_assembly, raw_materials=[raw])
		fg_bom = make_bom(item=finished_good, raw_materials=[sub_assembly])

		mps = make_mps()
		cumulative = mps.get_cumulative_lead_time(finished_good, fg_bom.name)

		# FG(2) + sub-assembly(1) + raw(2) = 5 days along the critical path.
		self.assertAlmostEqual(cumulative, 5.0, places=2)

	def test_add_mps_data_uses_recursive_lead_time(self):
		# End-to-end: cumulative lead time computed from a BOM feeds the release-date math.
		raw = create_item("_Test MPS E2E Raw", valuation_rate=100).item_code
		finished_good = create_item("_Test MPS E2E FG", valuation_rate=300).item_code

		set_item_lead_time(raw, purchase_time=3)
		set_item_lead_time(finished_good, manufacturing_time_in_mins=1440)  # 1 day

		fg_bom = make_bom(item=finished_good, raw_materials=[raw])

		mps = make_mps()
		lead_time = mps.get_cumulative_lead_time(finished_good, fg_bom.name)
		# FG(1) + raw(3) = 4 days.
		self.assertAlmostEqual(lead_time, 4.0, places=2)

		delivery_date = getdate("2026-06-30")
		data = frappe._dict(
			{
				(finished_good, delivery_date): frappe._dict(
					{
						"item_code": finished_good,
						"delivery_date": delivery_date,
						"stock_uom": "Nos",
						"qty": 10.0,
						"cumulative_lead_time": lead_time,
						"order_release_date": delivery_date,
					}
				)
			}
		)

		mps.add_mps_data(data)
		row = mps.items[0]
		self.assertEqual(row.cumulative_lead_time, math.ceil(lead_time))
		self.assertEqual(getdate(row.order_release_date), add_days(delivery_date, -math.ceil(lead_time)))
