import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate

from erpnext.selling.doctype.product_bundle.test_product_bundle import make_product_bundle
from erpnext.stock.doctype.item.test_item import create_item
from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse
from erpnext.stock.report.product_bundle_balance.product_bundle_balance import execute


class TestProductBundleBalance(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self.company = "_Test Company"
		self.warehouse = "_Test Warehouse - _TC"

		# Child items
		self.child_item_1 = create_item(
			item_code="BUNDLE-CHILD-1", is_stock_item=1, company=self.company, valuation_rate=100
		)
		self.child_item_2 = create_item(
			item_code="BUNDLE-CHILD-2", is_stock_item=1, company=self.company, valuation_rate=100
		)

		# Parent (bundle) item
		self.parent_item = create_item(
			item_code="_Test Product Bundle Item New -Test", is_stock_item=0, company=self.company
		)

		make_product_bundle("_Test Product Bundle Item New -Test", ["BUNDLE-CHILD-1", "BUNDLE-CHILD-2"], 2)

		# Add stock for child items: 5 units of child 1, 9 units of child 2
		make_stock_entry(
			item_code=self.child_item_1.name,
			to_warehouse=self.warehouse,
			qty=5,
			company=self.company,
			posting_date=nowdate(),
		)
		make_stock_entry(
			item_code=self.child_item_2.name,
			to_warehouse=self.warehouse,
			qty=9,
			company=self.company,
			posting_date=nowdate(),
		)

	def test_bundle_balance_report_TC_SCK_508(self):
		filters = {
			"company": self.company,
			"warehouse": self.warehouse,
			"date": nowdate(),
		}
		columns, data = execute(filters)

		# Parent row check
		parent_rows = [
			row for row in data if row.get("indent") == 0 and row.get("item_code") == self.parent_item.name
		]
		self.assertTrue(parent_rows, "Parent row for bundle item not found.")
		parent_row = parent_rows[0]
		self.assertEqual(parent_row["company"], self.company)
		self.assertEqual(parent_row["warehouse"], self.warehouse)

		# The bundle quantity is min(5//2, 9//3) = min(2, 3) = 2
		self.assertEqual(parent_row["bundle_qty"], 2)

		# Child rows check
		child_rows = [
			row for row in data if row.get("indent") == 1 and row.get("parent_item") == self.parent_item.name
		]
		self.assertEqual(len(child_rows), 2)
		for row in child_rows:
			if row["item_code"] == self.child_item_1.name:
				self.assertEqual(row["actual_qty"], 5)
				self.assertEqual(row["minimum_qty"], 2)
				self.assertEqual(row["bundle_qty"], 2)
			elif row["item_code"] == self.child_item_2.name:
				self.assertEqual(row["actual_qty"], 9)
				self.assertEqual(row["minimum_qty"], 2)
				self.assertEqual(row["bundle_qty"], 4)
			else:
				self.fail("Unexpected child item in bundle.")

		# The parent row should be followed by its two children
		parent_idx = data.index(parent_row)
		self.assertEqual(data[parent_idx + 1]["indent"], 1)
		self.assertEqual(data[parent_idx + 2]["indent"], 1)
