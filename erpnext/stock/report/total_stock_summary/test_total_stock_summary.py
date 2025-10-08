import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.accounts.doctype.account.test_account import create_account
from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company
from erpnext.stock.doctype.item.test_item import create_item
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse
from erpnext.stock.utils import get_or_create_fiscal_year


class TestTotalStockSummary(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.original_get_value = frappe.db.get_value  # Save original method

	@classmethod
	def tearDownClass(cls):
		frappe.db.get_value = cls.original_get_value  # Restore original after tests
		super().tearDownClass()

	def setUp(self):
		# Restore frappe.db.get_value to prevent leaked lambda
		frappe.db.get_value = self.original_get_value

		self.company = create_company("_Test Company")
		self.company = "_Test Company"
		self.warehouse = create_warehouse(warehouse_name="_Test Warehouse - _TC", company="_Test Company")
		self.item = create_item(
			item_code="TEST-STOCK-ITEM",
			valuation_rate=100,
			warehouse="_Test Warehouse - _TC",
			company="_Test Company",
		)

		get_or_create_fiscal_year("_Test Company")

		self.stock_entry_name = create_stock_entry(
			item_code=self.item, warehouse="_Test Warehouse - _TC", qty=15, company="_Test Company"
		)

		self.filters = {"group_by": "Warehouse", "company": "_Test Company"}

	def test_execute_without_filters_TC_SCK_517(self):
		from erpnext.stock.report.total_stock_summary.total_stock_summary import execute

		# Test with filters - group by Warehouse
		columns, data = execute(self.filters)
		assert columns, "Expected columns to be returned"
		assert data, "Expected data to be returned"
		assert columns[0].startswith(
			"Warehouse"
		), f"Expected first column to be 'Warehouse', got '{columns[0]}'"
		assert any(
			row[0] == self.warehouse and row[1] == self.item.item_code for row in data
		), f"Expected data row for warehouse '{self.warehouse}' and item '{self.item.item_code}', got {data}"
		# Test with no filters (default group_by should be Company)
		columns_default, data_default = execute()
		assert columns_default, "Expected columns with default filters"
		assert data_default, "Expected data with default filters"
		assert columns_default[0].startswith(
			"Company"
		), f"Expected first column to be 'Company', got '{columns_default[0]}'"
		assert any(
			row[0] == self.company and row[1] == self.item.name for row in data_default
		), f"Expected row for company '{self.company}', got {data_default}"

		# Simulate empty stock scenario
		frappe.db.sql("DELETE FROM `tabBin` WHERE item_code = %s", self.item.name)
		columns_empty, data_empty = execute(self.filters)
		assert columns_empty, "Expected columns even if no data"


def create_stock_entry(item_code, warehouse, qty, company):
	se = frappe.get_doc(
		{
			"doctype": "Stock Entry",
			"stock_entry_type": "Material Receipt",
			"company": company,
			"items": [
				{"item_code": item_code, "qty": qty, "uom": "Nos", "t_warehouse": warehouse, "rate": 100}
			],
		}
	)
	se.insert(ignore_permissions=True)
	se.submit()
	return se.name
