# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.classes.context_managers import freeze_time
from frappe.utils import add_days, flt, formatdate, getdate, today

from erpnext.accounts.doctype.tax_rule.test_tax_rule import make_tax_rule
from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
from erpnext.manufacturing.report.material_requirements_planning_report.material_requirements_planning_report import (
	MaterialRequirementsPlanningReport,
	execute,
	get_item_lead_time,
	make_order,
)
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
			(0, 49, 1, 4),
			(-30, 49, 1, 4),
		)
		for minutes, qty, buffer_days, expected_days in cases:
			with self.subTest(minutes=minutes, qty=qty, buffer_days=buffer_days):
				mps.items[0].planned_qty = qty
				mps.save()
				lead_time.update({"manufacturing_time_in_mins": minutes, "buffer_time": buffer_days})
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

	def test_raw_material_fallback_reuses_subtrees_by_required_quantity(self):
		plan = make_mrp_plan(self, planned_qty=49, rm_qty=1)
		frappe.get_doc(
			{
				"doctype": "Item Lead Time",
				"item_code": plan.fg_item,
				"manufacturing_time_in_mins": 30,
				"buffer_time": 1,
			}
		).insert()
		frappe.get_doc({"doctype": "Item Lead Time", "item_code": plan.rm_item, "purchase_time": 3}).insert()

		parents = []
		child_item = plan.fg_item
		for _ in range(6):
			parent_item = make_item(properties={"is_stock_item": 1}).name
			make_bom(item=parent_item, raw_materials=[child_item], rm_qty=1, rate=100)
			frappe.get_doc({"doctype": "Item Lead Time", "item_code": parent_item, "buffer_time": 1}).insert()
			parents.append(parent_item)
			child_item = parent_item

		mps = frappe.get_doc("Master Production Schedule", plan.mps)
		mps.items[0].item_code = parents[-1]
		mps.save()
		with patch(f"{execute.__module__}.get_item_lead_time", wraps=get_item_lead_time) as lead_time:
			rows = get_mrp_rows(mps)
			# Descendant calculations should grow with the row count, not the square of BOM depth.
			self.assertLessEqual(lead_time.call_count, 2 * len(rows))

		for level, parent_item in enumerate(parents):
			self.assertEqual(rows[parent_item].required_qty, 49)
			self.assertEqual(rows[parent_item].lead_time, level + 7)
		self.assertEqual(rows[plan.fg_item].lead_time, 3)
		self.assertEqual(rows[plan.rm_item].lead_time, 3)

		# Stock changes the quantity below this assembly after the ancestor fallback was calculated.
		make_stock_entry(item_code=parents[2], target=WAREHOUSE, qty=1, rate=100)
		rows = get_mrp_rows(mps)
		self.assertEqual(rows[parents[-1]].lead_time, 12)
		self.assertEqual(rows[parents[2]].required_qty, 48)
		self.assertEqual(rows[parents[2]].lead_time, 8)
		self.assertEqual(rows[plan.fg_item].required_qty, 48)
		self.assertEqual(rows[plan.fg_item].lead_time, 2)

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
			}
		)
	)
	return {row.item_code: row for row in rows if row.get("item_code")}


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
