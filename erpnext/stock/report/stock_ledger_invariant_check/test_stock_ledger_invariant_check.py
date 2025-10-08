import unittest
from datetime import date, datetime, time

import frappe
from frappe.utils import nowdate, nowtime

from erpnext.stock.doctype.item.test_item import create_item
from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse
from erpnext.stock.report.stock_ledger_invariant_check import stock_ledger_invariant_check as report


class TestStockLedgerInvariantCheck(unittest.TestCase):
	def setUp(self):
		frappe.set_user("Administrator")

		self.item = create_item(item_code="_Test Item", is_stock_item=1, valuation_rate=100)
		self.warehouse = create_warehouse("_Test Warehouse")

		make_stock_entry(
			item=self.item.name,
			qty=10,
			rate=100,
			to_warehouse=self.warehouse,
			posting_date=nowdate(),
			posting_time=nowtime(),
		)

	def test_report_execution_T_SLIC_001(self):
		filters = frappe._dict({"item_code": self.item.name, "warehouse": self.warehouse})
		columns, data = report.execute(filters)

		self.assertIsInstance(columns, list)
		self.assertGreater(len(columns), 0)
		self.assertIsInstance(data, list)
		self.assertGreater(len(data), 0)

		for row in data:
			self.assertIn("fifo_valuation_rate", row)

	def test_empty_fifo_queue_T_SLIC_002(self):
		make_stock_entry(
			item=self.item.name,
			qty=10,
			from_warehouse=self.warehouse,
			posting_date=nowdate(),
			posting_time=nowtime(),
		)

		filters = frappe._dict({"item_code": self.item.name, "warehouse": self.warehouse})
		_, data = report.execute(filters)

		consumption_found = any("consumption_rate" in row and row.consumption_rate for row in data)
		self.assertTrue(consumption_found)

	def test_create_reposting_entries_T_SLIC_003(self):
		se = make_stock_entry(
			item=self.item.name,
			qty=5,
			rate=100,
			to_warehouse=self.warehouse,
			posting_date=nowdate(),
			posting_time=nowtime(),
		)
		se_doc = frappe.get_doc("Stock Entry", se.name)
		rows = [
			{
				"item_code": self.item.name,
				"warehouse": self.warehouse,
				"posting_date": se_doc.posting_date,
				"posting_time": se_doc.posting_time,
				"voucher_type": se_doc.doctype,
				"voucher_no": se_doc.name,
				"company": se_doc.company,
				"qty": se_doc.items[0].qty,
				"valuation_rate": se_doc.items[0].basic_rate,
			}
		]
		frappe.db.delete(
			"Repost Item Valuation",
			{
				"item_code": self.item.name,
				"warehouse": self.warehouse,
				"posting_date": se_doc.posting_date,
				"posting_time": se_doc.posting_time,
			},
		)
		report.create_reposting_entries(rows)
		repost = frappe.get_all(
			"Repost Item Valuation",
			filters={
				"item_code": self.item.name,
				"warehouse": self.warehouse,
				"posting_date": se_doc.posting_date,
				"posting_time": se_doc.posting_time,
				"docstatus": 1,
			},
			fields=["name"],
		)
		self.assertTrue(repost, "Repost Item Valuation entry was not created.")

	def test_create_reposting_entries_with_string_input_T_SLIC_004(self):
		import json

		se_doc = make_stock_entry(
			item_code=self.item.name,
			qty=10,
			rate=100,
			to_warehouse=self.warehouse,
		)
		rows = [
			{
				"item_code": se_doc.items[0].item_code,
				"warehouse": se_doc.items[0].t_warehouse,
				"posting_date": se_doc.posting_date.isoformat(),
				"posting_time": se_doc.posting_time.isoformat(),
				"voucher_type": se_doc.doctype,
				"voucher_no": se_doc.name,
				"company": se_doc.company,
				"qty": float(se_doc.items[0].qty),
				"valuation_rate": float(se_doc.items[0].basic_rate),
			}
		]
		frappe.db.delete(
			"Repost Item Valuation",
			{
				"item_code": self.item.name,
				"warehouse": self.warehouse,
				"posting_date": se_doc.posting_date,
				"posting_time": se_doc.posting_time,
			},
		)
		report.create_reposting_entries(json.dumps(rows))
		reposts = frappe.get_all(
			"Repost Item Valuation",
			filters={
				"item_code": self.item.name,
				"warehouse": self.warehouse,
				"posting_date": se_doc.posting_date,
				"posting_time": se_doc.posting_time,
				"docstatus": 1,
			},
			fields=["name"],
		)
		self.assertTrue(reposts, "Repost Item Valuation not created from JSON string input.")

	def test_report_columns_T_SLIC_005(self):
		columns = report.get_columns()
		self.assertIsInstance(columns, list)
		self.assertTrue(any(col["fieldname"] == "valuation_diff" for col in columns))
