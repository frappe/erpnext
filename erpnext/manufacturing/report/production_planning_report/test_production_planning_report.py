# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe.utils import add_days, flt, nowdate

from erpnext.manufacturing.doctype.production_plan.test_production_plan import make_bom
from erpnext.manufacturing.doctype.work_order.test_work_order import make_wo_order_test_record
from erpnext.manufacturing.report.production_planning_report.production_planning_report import execute
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.stock.doctype.item.test_item import create_item
from erpnext.stock.doctype.material_request.test_material_request import make_material_request
from erpnext.tests.utils import ERPNextTestSuite

COMPANY = "_Test Company"
WAREHOUSE = "_Test Warehouse - _TC"
FG_WAREHOUSE = "_Test Warehouse 1 - _TC"


class TestProductionPlanningReport(ERPNextTestSuite):
	"""Coverage for manufacturing Production Planning Report.

	Each test builds a self-contained Item + BOM + order chain so the
	assertions do not depend on shared global fixtures. The base class
	rolls back the DB after every test, so nothing here needs cleanup.
	"""

	def setUp(self):
		self.fg_item = "_Test PPR FG Item"
		self.rm_item_1 = "_Test PPR RM 1"
		self.rm_item_2 = "_Test PPR RM 2"

		# Raw materials carry a default_warehouse so the report's
		# warehouse-resolution branch has something to pick from.
		for rm in (self.rm_item_1, self.rm_item_2):
			create_item(
				rm,
				is_stock_item=1,
				valuation_rate=100,
				warehouse=WAREHOUSE,
				company=COMPANY,
			)

		create_item(
			self.fg_item,
			is_stock_item=1,
			valuation_rate=0,
			warehouse=WAREHOUSE,
			company=COMPANY,
		)

		# Default BOM for the FG item; Sales Order / Material Request rows
		# fall back to Item.default_bom to gather raw materials.
		self.bom = make_bom(
			item=self.fg_item,
			raw_materials=[self.rm_item_1, self.rm_item_2],
			rm_qty=2,
			source_warehouse=WAREHOUSE,
			company=COMPANY,
			set_as_default_bom=True,
		)

	# ------------------------------------------------------------------ helpers
	def _row_names(self, data):
		"""Sorted, de-duplicated list of order ids in the report data.

		PostgreSQL has no implicit ordering, so always sort before asserting.
		"""
		return sorted({row.get("name") for row in data if row.get("name")})

	def _raw_material_codes(self, data):
		return sorted({row.get("item_code") for row in data if row.get("item_code")})

	def _ordered_names(self, data):
		"""Distinct order ids in their order of first appearance.

		Unlike _row_names this deliberately does NOT sort: it captures the
		sequence the report's ORDER BY produced, so order_by behaviour can be
		asserted. The report orders by a single distinct-valued column, so the
		sequence is deterministic on both MariaDB and PostgreSQL.
		"""
		ordered = []
		for row in data:
			name = row.get("name")
			if name and name not in ordered:
				ordered.append(name)
		return ordered

	# -------------------------------------------------------------- work order
	def test_execute_based_on_work_order(self):
		wo = make_wo_order_test_record(
			production_item=self.fg_item,
			bom_no=self.bom.name,
			qty=5,
			source_warehouse=WAREHOUSE,
			fg_warehouse=FG_WAREHOUSE,
			company=COMPANY,
			stock_uom="Nos",
		)

		filters = {
			"company": COMPANY,
			"based_on": "Work Order",
			"order_by": "Planned Start Date",
			"docnames": [wo.name],
		}
		columns, data = execute(filters)

		self.assertTrue(columns, "columns must not be empty")
		self.assertTrue(data, "expected at least one row for the Work Order")
		self.assertIn(wo.name, self._row_names(data))

		# The order qty should be reflected on the rows belonging to this WO.
		wo_rows = [row for row in data if row.get("name") == wo.name]
		self.assertTrue(wo_rows)
		for row in wo_rows:
			self.assertAlmostEqual(flt(row.get("qty_to_manufacture")), 5.0, places=2)
			self.assertEqual(row.get("production_item"), self.fg_item)

	def test_work_order_raw_materials_gathered(self):
		wo = make_wo_order_test_record(
			production_item=self.fg_item,
			bom_no=self.bom.name,
			qty=3,
			source_warehouse=WAREHOUSE,
			fg_warehouse=FG_WAREHOUSE,
			company=COMPANY,
			stock_uom="Nos",
		)

		filters = {
			"company": COMPANY,
			"based_on": "Work Order",
			"order_by": "Planned Start Date",
			"docnames": [wo.name],
		}
		_columns, data = execute(filters)

		rm_codes = self._raw_material_codes(data)
		# Both BOM raw materials should surface against the work order row.
		self.assertIn(self.rm_item_1, rm_codes)
		self.assertIn(self.rm_item_2, rm_codes)

	# ------------------------------------------------------------- sales order
	def test_execute_based_on_sales_order(self):
		so = make_sales_order(
			item_code=self.fg_item,
			qty=4,
			warehouse=WAREHOUSE,
			company=COMPANY,
			currency="INR",
		)

		filters = {
			"company": COMPANY,
			"based_on": "Sales Order",
			"order_by": "Delivery Date",
			"docnames": [so.name],
		}
		columns, data = execute(filters)

		self.assertTrue(columns)
		self.assertTrue(data, "expected rows for the Sales Order")
		self.assertIn(so.name, self._row_names(data))

		# Raw materials come from the FG item's default BOM.
		rm_codes = self._raw_material_codes(data)
		self.assertIn(self.rm_item_1, rm_codes)
		self.assertIn(self.rm_item_2, rm_codes)

		# required_qty == per-unit qty (2) * order qty (4) == 8 for each RM.
		so_rows = [row for row in data if row.get("name") == so.name]
		self.assertTrue(so_rows)
		for row in so_rows:
			if row.get("item_code") in (self.rm_item_1, self.rm_item_2):
				self.assertAlmostEqual(flt(row.get("required_qty")), 8.0, places=2)

	def test_sales_order_order_by_actually_orders_rows(self):
		"""order_by must order the rows, not just return the same set.

		The report sorts Sales Orders by delivery_date ASC for "Delivery Date"
		and by base_grand_total DESC for "Total Amount". Two orders whose
		date-order is the opposite of their amount-order must come back in
		opposite sequences.
		"""
		# SO A: earlier delivery (today), lower amount (2 * 100 = 200).
		so_early_cheap = make_sales_order(
			item_code=self.fg_item,
			qty=2,
			rate=100,
			transaction_date=add_days(nowdate(), -10),
			warehouse=WAREHOUSE,
			company=COMPANY,
			currency="INR",
		)
		# SO B: later delivery (today + 10), higher amount (10 * 100 = 1000).
		so_late_pricey = make_sales_order(
			item_code=self.fg_item,
			qty=10,
			rate=100,
			transaction_date=nowdate(),
			warehouse=WAREHOUSE,
			company=COMPANY,
			currency="INR",
		)

		base_filters = {
			"company": COMPANY,
			"based_on": "Sales Order",
			"docnames": [so_early_cheap.name, so_late_pricey.name],
		}

		_c1, data_by_date = execute({**base_filters, "order_by": "Delivery Date"})
		_c2, data_by_amount = execute({**base_filters, "order_by": "Total Amount"})

		# Delivery Date ascending -> the earlier-delivery order comes first.
		self.assertEqual(
			self._ordered_names(data_by_date),
			[so_early_cheap.name, so_late_pricey.name],
		)
		# Total Amount descending -> the higher-amount order comes first: the
		# exact opposite sequence, proving the ORDER BY is really applied.
		self.assertEqual(
			self._ordered_names(data_by_amount),
			[so_late_pricey.name, so_early_cheap.name],
		)

	def test_total_amount_column_for_sales_order(self):
		so = make_sales_order(
			item_code=self.fg_item,
			qty=2,
			warehouse=WAREHOUSE,
			company=COMPANY,
			currency="INR",
		)

		columns, _data = execute(
			{
				"company": COMPANY,
				"based_on": "Sales Order",
				"order_by": "Total Amount",
				"docnames": [so.name],
			}
		)

		# The dynamic order_by column should switch to a currency field.
		fieldnames = [col["fieldname"] for col in columns]
		self.assertIn("base_grand_total", fieldnames)

	# -------------------------------------------------------- material request
	def test_execute_based_on_material_request(self):
		mr = make_material_request(
			item_code=self.fg_item,
			material_request_type="Manufacture",
			qty=6,
			uom="Nos",
			warehouse=WAREHOUSE,
			company=COMPANY,
		)

		filters = {
			"company": COMPANY,
			"based_on": "Material Request",
			"order_by": "Required Date",
			"docnames": [mr.name],
		}
		columns, data = execute(filters)

		self.assertTrue(columns)
		self.assertTrue(data, "expected rows for the Manufacture Material Request")
		self.assertIn(mr.name, self._row_names(data))

		# schedule_date column is wired up for Material Request.
		fieldnames = [col["fieldname"] for col in columns]
		self.assertIn("schedule_date", fieldnames)

		# Raw materials resolved from the default BOM (per-unit 2 * qty 6 == 12).
		rm_codes = self._raw_material_codes(data)
		self.assertIn(self.rm_item_1, rm_codes)
		self.assertIn(self.rm_item_2, rm_codes)

		mr_rows = [row for row in data if row.get("name") == mr.name]
		self.assertTrue(mr_rows)
		for row in mr_rows:
			if row.get("item_code") in (self.rm_item_1, self.rm_item_2):
				self.assertAlmostEqual(flt(row.get("required_qty")), 12.0, places=2)

	# -------------------------------------------------------------- edge cases
	def test_no_open_orders_returns_empty_data(self):
		# A docname that does not exist -> no orders, no crash, empty data.
		columns, data = execute(
			{
				"company": COMPANY,
				"based_on": "Work Order",
				"order_by": "Planned Start Date",
				"docnames": ["NON-EXISTENT-WO-XYZ"],
			}
		)

		self.assertTrue(columns, "columns are built even when there is no data")
		self.assertEqual(data, [])

	def test_company_with_no_orders_returns_empty_data(self):
		# Use a valid-but-unused docname filter under a company that has no
		# matching open orders for the given window.
		so = make_sales_order(
			item_code=self.fg_item,
			qty=1,
			warehouse=WAREHOUSE,
			company=COMPANY,
			currency="INR",
		)

		# Restrict to a different (non-existent for this SO) docname so the
		# query returns nothing without raising.
		_columns, data = execute(
			{
				"company": COMPANY,
				"based_on": "Sales Order",
				"order_by": "Delivery Date",
				"docnames": ["NON-EXISTENT-SO-" + so.name],
			}
		)

		self.assertEqual(data, [])
