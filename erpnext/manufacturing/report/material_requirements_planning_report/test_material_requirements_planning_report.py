# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.classes.context_managers import freeze_time
from frappe.utils import add_days, flt, formatdate, today

from erpnext.accounts.doctype.tax_rule.test_tax_rule import make_tax_rule
from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
from erpnext.manufacturing.report.material_requirements_planning_report.material_requirements_planning_report import (
	MaterialRequirementsPlanningReport,
	execute,
	get_item_lead_time,
	make_order,
)
from erpnext.stock.doctype.item.test_item import make_item
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

	def test_manufacture_lead_time_is_not_int_truncated(self):
		"""lead_time = 1440 / manufacturing_time_in_mins + buffer_time. Both columns are Int;
		integer/integer division truncates on Postgres (1440/7 -> 205) while MariaDB yields a
		decimal, so the computed lead time (and the derived release date) diverged by engine."""
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
		# 1440 / 7 + 2 = 207.714...; a truncating integer division on Postgres would give 207.
		self.assertAlmostEqual(float(lead_time), 1440 / 7 + 2, places=2)

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
