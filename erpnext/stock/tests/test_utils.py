import json

import frappe
from frappe.query_builder.functions import Timestamp
from frappe.tests import IntegrationTestCase

from erpnext.stock.utils import scan_barcode


class StockTestMixin:
	"""Mixin to simplfy stock ledger tests, useful for all stock transactions."""

	def make_item(self, item_code=None, properties=None, *args, **kwargs):
		from erpnext.stock.doctype.item.test_item import make_item

		return make_item(item_code, properties, *args, **kwargs)

	def assertSLEs(self, doc, expected_sles, sle_filters=None):
		"""Compare sorted SLEs, useful for vouchers that create multiple SLEs for same line"""

		filters = {"voucher_no": doc.name, "voucher_type": doc.doctype, "is_cancelled": 0}
		if sle_filters:
			filters.update(sle_filters)

		sle = frappe.qb.DocType("Stock Ledger Entry")
		query = (
			frappe.qb.from_(sle)
			.select("*")
			.where(sle.voucher_no == doc.name)
			.where(sle.voucher_type == doc.doctype)
			.where(sle.is_cancelled == 0)
		)
		if sle_filters:
			for key, value in sle_filters.items():
				query = query.where(sle[key] == value)

		sles = (
			query.orderby(Timestamp(sle.posting_date, sle.posting_time))
			.orderby(sle.creation)
			.run(as_dict=True)
		)
		self.assertGreaterEqual(len(sles), len(expected_sles))

		for exp_sle, act_sle in zip(expected_sles, sles, strict=False):
			for k, v in exp_sle.items():
				act_value = act_sle[k]
				if k == "stock_queue":
					act_value = json.loads(act_value)
					if act_value and act_value[0][0] == 0:
						# ignore empty fifo bins
						continue

				self.assertEqual(v, act_value, msg=f"{k} doesn't match \n{exp_sle}\n{act_sle}")

	def assertGLEs(self, doc, expected_gles, gle_filters=None, order_by=None):
		filters = {"voucher_no": doc.name, "voucher_type": doc.doctype, "is_cancelled": 0}

		if gle_filters:
			filters.update(gle_filters)
		actual_gles = frappe.get_all(
			"GL Entry",
			fields=["*"],
			filters=filters,
			order_by=order_by or "posting_date, creation",
		)
		self.assertGreaterEqual(len(actual_gles), len(expected_gles))
		for exp_gle, act_gle in zip(expected_gles, actual_gles, strict=False):
			for k, exp_value in exp_gle.items():
				act_value = act_gle[k]
				self.assertEqual(exp_value, act_value, msg=f"{k} doesn't match \n{exp_gle}\n{act_gle}")


class TestStockUtilities(IntegrationTestCase, StockTestMixin):
	def test_barcode_scanning(self):
		simple_item = self.make_item(properties={"barcodes": [{"barcode": "12399"}]})
		self.assertEqual(scan_barcode("12399")["item_code"], simple_item.name)

		batch_item = self.make_item(properties={"has_batch_no": 1, "create_new_batch": 1})
		batch = frappe.get_doc(doctype="Batch", item=batch_item.name).insert()

		batch_scan = scan_barcode(batch.name)
		self.assertEqual(batch_scan["item_code"], batch_item.name)
		self.assertEqual(batch_scan["batch_no"], batch.name)
		self.assertEqual(batch_scan["has_batch_no"], 1)
		self.assertEqual(batch_scan["has_serial_no"], 0)

		serial_item = self.make_item(properties={"has_serial_no": 1})
		serial = frappe.get_doc(
			doctype="Serial No", item_code=serial_item.name, serial_no=frappe.generate_hash()
		).insert()

		serial_scan = scan_barcode(serial.name)
		self.assertEqual(serial_scan["item_code"], serial_item.name)
		self.assertEqual(serial_scan["serial_no"], serial.name)
		self.assertEqual(serial_scan["has_batch_no"], 0)
		self.assertEqual(serial_scan["has_serial_no"], 1)

	def test_barcode_scanning_of_warehouse(self):
		warehouse = frappe.get_doc(
			{
				"doctype": "Warehouse",
				"warehouse_name": "Test Warehouse for Barcode",
				"company": "_Test Company",
			}
		).insert()

		warehouse_2 = frappe.get_doc(
			{
				"doctype": "Warehouse",
				"warehouse_name": "Test Warehouse for Barcode 2",
				"company": "_Test Company",
			}
		).insert()

		warehouse_scan = scan_barcode(warehouse.name)
		self.assertEqual(warehouse_scan["warehouse"], warehouse.name)

		item_with_warehouse = self.make_item(
			properties={
				"item_defaults": [{"company": "_Test Company", "default_warehouse": warehouse.name}],
				"barcodes": [{"barcode": "w12345"}],
			}
		)

		item_scan = scan_barcode("w12345")
		self.assertEqual(item_scan["item_code"], item_with_warehouse.name)
		self.assertEqual(item_scan.get("default_warehouse"), None)

		ctx = {"company": "_Test Company"}
		item_scan_with_ctx = scan_barcode("w12345", ctx=ctx)
		self.assertEqual(item_scan_with_ctx["item_code"], item_with_warehouse.name)
		self.assertEqual(item_scan_with_ctx["default_warehouse"], warehouse.name)

		ctx = {"company": "_Test Company", "set_warehouse": warehouse_2.name}
		item_scan_with_ctx = scan_barcode("w12345", ctx=ctx)
		self.assertEqual(item_scan_with_ctx["item_code"], item_with_warehouse.name)
		self.assertEqual(item_scan_with_ctx["default_warehouse"], warehouse_2.name)
