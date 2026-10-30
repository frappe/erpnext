# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.permissions import add_user_permission

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.batch_item_expiry_status.batch_item_expiry_status import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestBatchItemExpiryStatus(ERPNextTestSuite):
	def run_report(self, **extra):
		filters = frappe._dict(
			{
				"from_date": "2026-01-01",
				"to_date": "2026-12-31",
				"company": "_Test Company",
			}
		)
		filters.update(extra)
		return execute(filters)[1]

	def test_batch_listed_with_balance(self):
		item = make_item(
			properties={
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "BIE-.#####",
				"has_expiry_date": 1,
				"shelf_life_in_days": 30,
			}
		).name

		make_stock_entry(
			item_code=item,
			to_warehouse="_Test Warehouse - _TC",
			qty=10,
			rate=100,
			posting_date="2026-06-01",
		)

		batch_no = frappe.db.get_value("Batch", {"item": item}, "name")
		self.assertTrue(batch_no, "Stock entry did not auto-create a batch")

		data = self.run_report(item=item)

		row = next((r for r in data if r[2] == batch_no), None)
		self.assertIsNotNone(row, f"Batch {batch_no} not found in report for item {item}")

		self.assertEqual(row[0], item)
		self.assertEqual(row[2], batch_no)
		self.assertEqual(row[4], 10)
		# expiry = batch manufacturing_date + 30 day shelf life; matches the Batch record
		batch_expiry = frappe.db.get_value("Batch", batch_no, "expiry_date")
		self.assertIsNotNone(row[5], "Expiry date should be set for a batch with shelf life")
		self.assertEqual(frappe.utils.getdate(row[5]), frappe.utils.getdate(batch_expiry))
		# Expiry (In Days) column = days until expiry
		expected_days = frappe.utils.date_diff(batch_expiry, frappe.utils.today())
		self.assertEqual(row[6], expected_days)

	def test_batches_are_filtered_by_expiry_date(self):
		item = make_item(properties={"is_stock_item": 1, "has_batch_no": 1}).name
		batches = {}
		for label, days in (("old", 2), ("later", 60)):
			batches[label] = frappe.get_doc(
				{
					"doctype": "Batch",
					"item": item,
					"batch_id": frappe.generate_hash(length=10),
					"expiry_date": frappe.utils.add_days(frappe.utils.today(), days),
				}
			).insert()
			make_stock_entry(
				item_code=item,
				to_warehouse="_Test Warehouse - _TC",
				qty=5,
				rate=100,
				batch_no=batches[label].name,
				use_serial_batch_fields=1,
			)
		frappe.db.set_value(
			"Batch", batches["old"].name, "creation", frappe.utils.add_days(frappe.utils.now(), -400)
		)

		data = self.run_report(
			item=item, from_date=frappe.utils.today(), to_date=frappe.utils.add_days(frappe.utils.today(), 30)
		)

		self.assertEqual([row[2] for row in data], [batches["old"].name])

	def make_batch_in_two_warehouses(self):
		item = make_item(properties={"is_stock_item": 1, "has_batch_no": 1}).name
		batch = frappe.get_doc(
			{
				"doctype": "Batch",
				"item": item,
				"batch_id": frappe.generate_hash(length=10),
				"expiry_date": frappe.utils.add_days(frappe.utils.today(), 10),
			}
		).insert()
		for warehouse, qty in (("Stores - _TC", 7), ("Finished Goods - _TC", 3)):
			make_stock_entry(
				item_code=item,
				to_warehouse=warehouse,
				qty=qty,
				rate=100,
				batch_no=batch.name,
				use_serial_batch_fields=1,
			)

		return item, batch.name

	def run_report_as_restricted_user(self, item, applicable_for=None):
		user = "batch-expiry-warehouse@example.com"
		if not frappe.db.exists("User", user):
			frappe.get_doc(
				{"doctype": "User", "email": user, "first_name": "Batch Expiry", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		frappe.get_doc("User", user).add_roles("Stock Manager")
		add_user_permission("Warehouse", "Finished Goods - _TC", user, applicable_for=applicable_for)

		frappe.set_user(user)
		try:
			return self.run_report(
				item=item,
				from_date=frappe.utils.today(),
				to_date=frappe.utils.add_days(frappe.utils.today(), 30),
			)
		finally:
			frappe.set_user("Administrator")

	def test_quantity_counts_only_permitted_warehouses(self):
		item, batch = self.make_batch_in_two_warehouses()

		data = self.run_report_as_restricted_user(item)

		self.assertEqual([(row[2], row[4]) for row in data], [(batch, 3)])

	def test_permission_for_another_doctype_does_not_limit_the_quantity(self):
		item, batch = self.make_batch_in_two_warehouses()

		data = self.run_report_as_restricted_user(item, applicable_for="Purchase Order")

		self.assertEqual([(row[2], row[4]) for row in data], [(batch, 10)])
