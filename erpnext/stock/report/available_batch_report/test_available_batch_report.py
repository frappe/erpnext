from types import SimpleNamespace

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today

from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse
from erpnext.stock.report.available_batch_report import available_batch_report
from erpnext.stock.utils import get_or_create_fiscal_year


class TestAvailableBatchReport(FrappeTestCase):
	def setUp(self):
		self.company = create_company("_Test Company")
		get_or_create_fiscal_year("_Test Company")

		self.warehouse = create_warehouse("Stores - _TC")

		self.item = create_item("TEST-ITEM-100")
		self.batch = create_batch("BATCH-001", self.item, self.warehouse)
		self.stock_entry_doc = (
			frappe.get_doc(
				{
					"doctype": "Stock Entry",
					"stock_entry_type": "Material Receipt",
					"company": "_Test Company",
					"items": [
						{
							"item_code": self.item,
							"qty": 5,
							"t_warehouse": self.warehouse,
							"batch_no": self.batch,
						}
					],
				}
			)
			.insert()
			.submit()
		)

	def make_filters(self, **overrides):
		default_filters = dict(
			warehouse=None,
			item_code=None,
			from_date=None,
			to_date=None,
			include_expired_batches=None,
			show_item_name=None,
			batch_no=None,
			warehouse_type=None,
		)
		default_filters.update(overrides)
		return SimpleNamespace(**default_filters)

	def test_get_batchwise_data_to_date_TC_SCK_498(self):
		filters = self.make_filters(to_date="2025-12-31")
		columns, data = available_batch_report.execute(filters)

		# Validate column structure
		expected_fields = {"item_code", "warehouse", "batch_no", "expiry_date", "balance_qty"}
		actual_fields = {col["fieldname"] for col in columns}
		self.assertTrue(expected_fields.issubset(actual_fields))

		# Check a known entry
		test_row = next((d for d in data if d["item_code"] == "TEST-ITEM-100"), None)
		self.assertIsNotNone(test_row)
		self.assertEqual(test_row["batch_no"], "BATCH-001")
		self.assertEqual(test_row["warehouse"], "Stores - _TC")
		self.assertEqual(test_row["balance_qty"], 5)
		self.assertIsNone(test_row["expiry_date"])

		# Check data types
		for row in data:
			self.assertIsInstance(row["balance_qty"], float)
			self.assertIn(row["item_code"], [d["item_code"] for d in data])

	def test_get_batchwise_data_multiple_filters_TC_SCK_499(self):
		filters = self.make_filters(
			item_code=self.item.name,
			warehouse=self.warehouse,
			batch_no=self.batch.name,
			expiry_date="2025-12-31",
			show_item_name=True,
			include_expired_batches=True,
			to_date="2025-12-31",
		)
		columns, data = available_batch_report.execute(filters)
		self.assertEqual(len(data), 1)

		# Validate contents of the returned row
		row = data[0]
		self.assertEqual(row["item_code"], "TEST-ITEM-100")
		self.assertEqual(row["item_name"], "Test Item TEST-ITEM-100")
		self.assertEqual(row["batch_no"], "BATCH-001")
		self.assertEqual(row["warehouse"], "Stores - _TC")
		self.assertEqual(row["balance_qty"], 5)
		self.assertIsNone(row["expiry_date"])

		# Optional: assert column headers include expected fieldnames
		expected_fieldnames = {
			"item_code",
			"item_name",
			"warehouse",
			"batch_no",
			"expiry_date",
			"balance_qty",
		}
		returned_fieldnames = {col["fieldname"] for col in columns}
		self.assertTrue(expected_fieldnames.issubset(returned_fieldnames))

	# Added: test for execute()
	def test_execute_function_TC_SCK_500(self):
		filters = self.make_filters(
			item_code=self.item.name,
			warehouse=self.warehouse,
			batch_no=self.batch.name,
			show_item_name=True,
			to_date="2025-12-31",
		)
		columns, data = available_batch_report.execute(filters)
		row = data[0]
		self.assertEqual(row["item_code"], "TEST-ITEM-100")
		self.assertEqual(row["batch_no"], "BATCH-001")
		self.assertEqual(row["warehouse"], "Stores - _TC")
		self.assertEqual(row["balance_qty"], 5.0)
		self.assertEqual(row["item_name"], "Test Item TEST-ITEM-100")

		# Validate expected columns exist
		expected_column_fields = {
			"item_code",
			"item_name",
			"warehouse",
			"batch_no",
			"expiry_date",
			"balance_qty",
		}
		actual_column_fields = {col["fieldname"] for col in columns}
		self.assertTrue(expected_column_fields.issubset(actual_column_fields))

	def test_to_date_today_with_expiry_check_TC_SCK_501(self):
		self.batch.expiry_date = today()
		self.batch.reload()
		self.batch.save()

		filters = self.make_filters(to_date=today(), item_code=self.item.name)
		columns, data = available_batch_report.execute(filters)
		self.assertEqual(len(data), 1)

		# Validate content
		row = data[0]
		self.assertEqual(row["item_code"], "TEST-ITEM-100")
		self.assertEqual(row["batch_no"], "BATCH-001")
		self.assertEqual(row["warehouse"], "Stores - _TC")
		self.assertEqual(row["balance_qty"], 30.0)

	def test_to_date_today_with_expired_batches_included_TC_SCK_502(self):
		# Expired batch with include_expired_batches=True
		self.batch.expiry_date = "2000-01-01"
		self.batch.reload()
		self.batch.save()

		filters = self.make_filters(to_date=today(), item_code=self.item.name, include_expired_batches=True)
		data = available_batch_report.get_data(filters)
		row = data[0]
		self.assertEqual(row["item_code"], "TEST-ITEM-100")
		self.assertEqual(row["batch_no"], "BATCH-001")
		self.assertEqual(row["warehouse"], "Stores - _TC")
		self.assertEqual(row["balance_qty"], 5)

	def test_get_batchwise_data_from_serial_batch_bundle_TC_SCK_503(self):
		from frappe import generate_hash
		from frappe.utils import now_datetime

		filters = self.make_filters(item_code=self.item.name, to_date=today())
		data = available_batch_report.get_data(filters)
		matching_rows = [
			row for row in data if row["item_code"] == self.item.name and row["warehouse"] == self.warehouse
		]

		self.assertTrue(matching_rows, "No matching entry found for the serial and batch bundle item")

		# Validate values in the first matching row
		row = matching_rows[0]
		self.assertEqual(row["item_code"], self.item.name)
		self.assertEqual(row["warehouse"], self.warehouse)
		self.assertGreaterEqual(row["balance_qty"], 1.0)  # At least 1 due to the Inward transaction


def create_company(company_name):
	if not frappe.db.exists("Company", company_name):
		company = frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": company_name,
				"company_type": "Company",
				"default_currency": "INR",
				"country": "India",
				"company_email": "test@example.com",
				"abbr": "_TC",
			}
		).insert()
		return company
	return frappe.get_doc("Company", company_name)


def create_item(item_code):
	brand = "TestBrand"
	hsn_code = "10010010"

	if not frappe.db.exists("GST HSN Code", hsn_code):
		frappe.get_doc(
			{"doctype": "GST HSN Code", "hsn_code": hsn_code, "description": "Test HSN Code for automation"}
		).insert()

	if not frappe.db.exists("Brand", brand):
		frappe.get_doc({"doctype": "Brand", "brand": brand}).insert()

	if not frappe.db.exists("Item", item_code):
		item = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": item_code,
				"item_name": f"Test Item {item_code}",
				"is_stock_item": 1,
				"item_group": "All Item Groups",
				"stock_uom": "Nos",
				"gst_hsn_code": hsn_code,
				"has_batch_no": 1,
			}
		).insert()
		return item
	return frappe.get_doc("Item", item_code)


def create_batch(batch_name, item, warehouse):
	if not frappe.db.exists("Batch", batch_name):
		batch = frappe.get_doc(
			{"doctype": "Batch", "batch_id": batch_name, "item": item.name, "warehouse": warehouse}
		).insert()
		return batch
	return frappe.get_doc("Batch", batch_name)


def create_stock_entry(item, warehouse, batch, qty):
	from frappe.utils import nowdate

	stock_entry = frappe.get_doc(
		{
			"doctype": "Stock Entry",
			"stock_entry_type": "Material Receipt",
			"company": "_Test Company",
			"posting_date": nowdate(),
			"items": [{"item_code": item.name, "qty": qty, "t_warehouse": warehouse, "batch_no": batch.name}],
		}
	)
	stock_entry.insert()
	stock_entry.submit()
