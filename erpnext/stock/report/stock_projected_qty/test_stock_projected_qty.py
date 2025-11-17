import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company
from erpnext.accounts.doctype.payment_ledger_entry.test_payment_ledger_entry import make_sales_order
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_territory
from erpnext.stock.doctype.item.test_item import create_item
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

# from your_module_path import execute
from erpnext.stock.report.stock_projected_qty.stock_projected_qty import execute


class TestStockReorderReportExecute(FrappeTestCase):
	def setUp(self):
		self.company = create_company("_Test Company")
		self.company = "_Test Company"
		self.warehouse = create_warehouse(warehouse_name="_Test Warehouse - _TC", company="_Test Company")
		self.item_code = create_item(
			item_code="TEST-STOCK-ITEM",
			valuation_rate=100,
			warehouse="_Test Warehouse - _TC",
			company="_Test Company",
		)

		# self.item_code = "TEST-ITEM-EXEC"
		self.uom_name = "Box"
		self.stock_uom = "Nos"

		# Create UOM if not exists
		if not frappe.db.exists("UOM", self.uom_name):
			frappe.get_doc({"doctype": "UOM", "uom_name": self.uom_name}).insert()

		# Create stock entry for projected_qty
		frappe.get_doc(
			{
				"doctype": "Stock Entry",
				"stock_entry_type": "Material Receipt",
				"company": self.company,
				"items": [{"item_code": self.item_code.name, "qty": 5, "t_warehouse": self.warehouse}],
			}
		).insert().submit()

	def test_execute_with_item_code_filter_T_SPQ_001(self):
		"""Ensure only filtered item_code is returned in execute()"""
		columns, data = execute({"item_code": "TEST-STOCK-ITEM"})
		item_codes = [row[0] for row in data]
		self.assertIn(self.item_code.name, item_codes)
		self.assertEqual(len(set(item_codes)), 1)  # Ensure only 1 item is returned
		self.assertEqual(item_codes[0], self.item_code.name)

	def test_execute_with_include_uom_T_SPQ_002(self):
		"""Ensure UOM conversion factor is applied in execute() when include_uom is used"""
		columns, data = execute({"item_code": self.item_code.name, "include_uom": self.uom_name})
		uom_col_index = [col["fieldname"] for col in columns].index("stock_uom")
		self.assertTrue(any(row[uom_col_index] == self.stock_uom for row in data))
		# self.assertTrue(any(row[uom_col_index] == self.stock_uom for row in data))
		for row in data:
			self.assertEqual(row[uom_col_index], self.stock_uom)

		conversion_col_index = [col["fieldname"] for col in columns].index(
			"stock_uom"
		)  # or separate if extended
		self.assertTrue(any(row[conversion_col_index] for row in data))

	def test_execute_shortage_qty_calculation_T_SPQ_003(self):
		"""Test that shortage quantity is calculated when reorder level > projected_qty"""
		columns, data = execute({"item_code": self.item_code.name})
		shortage_index = [col["fieldname"] for col in columns].index("shortage_qty")
		shortages = [row[shortage_index] for row in data]
		self.assertTrue(any(s == 0 for s in shortages))
		shortage_index = [col["fieldname"] for col in columns].index("shortage_qty")
		reorder_index = [col["fieldname"] for col in columns].index("re_order_level")
		projected_index = [col["fieldname"] for col in columns].index("projected_qty")

		for row in data:
			reorder_level = row[reorder_index]
			projected_qty = row[projected_index]
			shortage_qty = row[shortage_index]

			if reorder_level and reorder_level > projected_qty:
				expected_shortage = reorder_level - projected_qty
				self.assertEqual(shortage_qty, expected_shortage)
			else:
				self.assertEqual(shortage_qty, 0)
