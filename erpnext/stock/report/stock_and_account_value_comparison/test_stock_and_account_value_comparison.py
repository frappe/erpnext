import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company
from erpnext.stock.doctype.item.test_item import create_item
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse
from erpnext.stock.report.stock_and_account_value_comparison.stock_and_account_value_comparison import execute
from erpnext.stock.utils import get_or_create_fiscal_year


class TestStockAndAccountValueComparison(FrappeTestCase):
	def setUp(self):
		if not frappe.db.exists("Company", "_Test Company"):
			create_company("_Test Company")
		self.company = "_Test Company"
		self.account = "Stock In Hand - _TC"
		self.posting_date = frappe.utils.nowdate()
		self.warehouse = create_warehouse(warehouse_name="_Test Warehouse - _TC", company=self.company)
		self.item = create_item(item_code="_Test Item", valuation_rate=100)
		get_or_create_fiscal_year(self.company)
		self.stock_entry = self.create_stock_entry()
		self.create_stock_ledger_entry()
		self.create_gl_entry()

	def test_report_execute_and_columns_and_data_TC_SCK_511(self):
		filters = frappe._dict({"company": self.company, "as_on_date": self.posting_date})
		columns, data = execute(filters)
		# Columns structure
		self.assertTrue(columns)
		self.assertIn("fieldname", columns[0])
		expected_fields = [
			"name",
			"posting_date",
			"posting_time",
			"voucher_type",
			"voucher_no",
			"stock_value",
			"account_value",
			"difference_value",
		]
		self.assertEqual([col["fieldname"] for col in columns], expected_fields)
		# Data is returned and has required fields
		self.assertTrue(data)
		for row in data:
			for key in ["stock_value", "account_value", "difference_value", "voucher_type", "voucher_no"]:
				self.assertIn(key, row)
		# Difference logic
		for row in data:
			self.assertAlmostEqual(
				row["difference_value"], row["stock_value"] - row["account_value"], places=2
			)

	def test_report_execute_with_account_filter_TC_SCK_512(self):
		filters = frappe._dict(
			{"company": self.company, "as_on_date": self.posting_date, "account": self.account}
		)
		columns, data = execute(filters)
		self.assertTrue(data)
		for row in data:
			self.assertIn("account_value", row)
			self.assertIn("stock_value", row)

	def test_report_perpetual_inventory_disabled_TC_SCK_513(self):
		import erpnext

		filters = frappe._dict({"company": self.company, "as_on_date": self.posting_date})
		original = erpnext.is_perpetual_inventory_enabled
		erpnext.is_perpetual_inventory_enabled = lambda company: False
		with self.assertRaises(frappe.ValidationError):
			execute(filters)
		erpnext.is_perpetual_inventory_enabled = original

	def test_data_difference_filtering_TC_SCK_514(self):
		# Manipulate GL Entry to force a difference > 0.1
		frappe.db.set_value(
			"GL Entry",
			{"voucher_no": self.stock_entry},
			"debit_in_account_currency",
			800,  # stock_value is 1000, so difference will be 200
		)
		filters = frappe._dict({"company": self.company, "as_on_date": self.posting_date})
		_, data = execute(filters)
		self.assertTrue(any(abs(row["difference_value"]) > 0.1 for row in data))

	def test_posting_time_conversion_TC_SCK_515(self):
		filters = frappe._dict({"company": self.company, "as_on_date": self.posting_date})
		_, data = execute(filters)
		for row in data:
			if "posting_time" in row and row["posting_time"] is not None:
				from datetime import timedelta

				self.assertIsInstance(row["posting_time"], timedelta)

	def test_create_reposting_entries_TC_SCK_516(self):
		from unittest.mock import patch

		from erpnext.stock.report.stock_and_account_value_comparison.stock_and_account_value_comparison import (
			create_reposting_entries,
		)

		test_row = {
			"voucher_type": "Stock Entry",
			"voucher_no": self.stock_entry,
			"posting_date": self.posting_date,
		}

		# Cleanup any pre-existing reposting entries
		existing = frappe.get_all(
			"Repost Item Valuation",
			{
				"voucher_type": test_row["voucher_type"],
				"voucher_no": test_row["voucher_no"],
				"company": self.company,
			},
		)
		for r in existing:
			doc = frappe.get_doc("Repost Item Valuation", r.name)
			if doc.docstatus == 1:
				doc.cancel()
			doc.delete()

		# Now mock msgprint and call create_reposting_entries
		with patch("frappe.msgprint") as mock_msgprint:
			create_reposting_entries([test_row], self.company)
			mock_msgprint.assert_called_once()
			args = mock_msgprint.call_args[0][0]
			self.assertIn("Reposting entries created", args)

	def create_stock_entry(self):
		se = frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": "Material Receipt",
				"company": self.company,
				"posting_date": self.posting_date,
				"items": [
					{
						"item_code": self.item.name,
						"qty": 10,
						"uom": "Nos",
						"t_warehouse": self.warehouse,
						"rate": 100,
					}
				],
			}
		)
		se.insert(ignore_permissions=True)
		se.submit()
		return se.name

	def create_stock_ledger_entry(self):
		if not frappe.db.exists("Stock Ledger Entry", {"voucher_no": self.stock_entry}):
			frappe.get_doc(
				{
					"doctype": "Stock Ledger Entry",
					"item_code": self.item.name,
					"warehouse": self.warehouse,
					"posting_date": self.posting_date,
					"posting_time": frappe.utils.now_datetime().time(),
					"voucher_type": "Stock Entry",
					"voucher_no": self.stock_entry,
					"voucher_detail_no": self.stock_entry + "-ROW1",
					"actual_qty": 10,
					"stock_value": 1000,
					"stock_value_difference": 1000,
					"company": self.company,
					"incoming_rate": 100,
					"is_cancelled": 0,
				}
			).insert(ignore_permissions=True)

	def create_gl_entry(self):
		if not frappe.db.exists("GL Entry", {"voucher_no": self.stock_entry}):
			frappe.get_doc(
				{
					"doctype": "GL Entry",
					"posting_date": self.posting_date,
					"account": self.account,
					"debit_in_account_currency": 1000,
					"credit_in_account_currency": 0,
					"voucher_type": "Stock Entry",
					"voucher_no": self.stock_entry,
					"company": self.company,
					"fiscal_year": frappe.defaults.get_user_default("fiscal_year"),
				}
			).insert(ignore_permissions=True)
