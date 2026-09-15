from copy import deepcopy

import frappe
from frappe.desk.query_report import build_xlsx_data, get_linked_doctypes

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.report.available_serial_no.available_serial_no import process_stock_ledger_entries
from erpnext.stock.report.utils import prepare_serial_batch_report
from erpnext.stock.serial_batch_identity import SerialBatchIdentity
from erpnext.tests.utils import ERPNextTestSuite


class TestSerialBatchReportUtils(ERPNextTestSuite):
	def setUp(self):
		self.item = make_item(properties={"has_serial_no": 1, "has_batch_no": 1})
		self.other_item = make_item(properties={"has_serial_no": 1, "has_batch_no": 1})
		self.serial = self.make_number("Serial No", "Report-001")
		self.batch = self.make_number("Batch", "Report-001")
		self.other_serial = self.make_number("Serial No", "Report-001", self.other_item.name)
		self.other_batch = self.make_number("Batch", "Report-001", self.other_item.name)

	def test_shared_numbers_keep_distinct_references_and_source_rows(self):
		columns = [
			{
				"label": "Serial",
				"fieldname": "received_serial",
				"fieldtype": "Link",
				"options": "Serial No",
				"width": 160,
			},
			{
				"label": "Batch",
				"fieldname": "received_batch",
				"fieldtype": "Link",
				"options": "Batch",
				"width": 120,
			},
		]
		data = [
			{"received_serial": self.serial.name, "received_batch": self.batch.name},
			{"received_serial": self.other_serial.name, "received_batch": self.other_batch.name},
		]
		original_columns, original_data = deepcopy(columns), deepcopy(data)
		result_columns, result = prepare_serial_batch_report(columns, data)
		self.assertEqual(columns, original_columns)
		self.assertEqual(data, original_data)
		for row, original in zip(result, original_data, strict=True):
			self.assertEqual(row.received_serial, original["received_serial"])
			self.assertEqual(row.received_batch, original["received_batch"])
			self.assertEqual(row.received_serial_number, "Report-001")
			self.assertEqual(row.received_batch_number, "Report-001")
		self.assertEqual(
			[column["fieldname"] for column in result_columns],
			["received_serial_number", "received_serial", "received_batch_number", "received_batch"],
		)
		widths = {column["fieldname"]: column["width"] for column in result_columns}
		self.assertEqual([widths["received_serial_number"], widths["received_batch_number"]], [160, 120])
		self.assertEqual(
			get_linked_doctypes(result_columns, result),
			{"Serial No": "received_serial", "Batch": "received_batch"},
		)
		self.assertEqual(
			{column["fieldname"] for column in result_columns if column.get("hidden")},
			{"received_serial", "received_batch"},
		)

	def test_only_explicit_serial_text_is_resolved(self):
		second_serial = self.make_number("Serial No", "Report-002")
		ids = f"{second_serial.name}\n{self.serial.name}\n{second_serial.name}"
		columns = [
			{"label": "Serial No", "fieldname": "serial_no", "fieldtype": "Small Text"},
			{"label": "Balance", "fieldname": "balance", "fieldtype": "Small Text"},
		]
		data = [{"serial_no": self.serial.name, "balance": ids}]
		_, result = prepare_serial_batch_report(columns, data, serial_fields=("balance",))
		self.assertEqual(result[0].serial_no, self.serial.name)
		self.assertNotIn("serial_no_number", result[0])
		self.assertEqual(result[0].balance, ids)
		self.assertEqual(result[0].balance_number, "Report-002\nReport-001\nReport-002")

	def test_link_ids_are_not_matched_as_physical_numbers(self):
		self.make_number("Serial No", self.serial.name)
		_, result = prepare_serial_batch_report(["Serial:Link/Serial No:120"], [[self.serial.name]])
		self.assertEqual(result[0].serial, self.serial.name)
		self.assertEqual(result[0].serial_number, "Report-001")

	def test_array_results_export_numbers_without_hidden_ids(self):
		columns = ["Serial:Link/Serial No:120", "Batch:Link/Batch:120", "Qty:Float:80"]
		data = [[self.serial.name, self.batch.name, 2]]
		result_columns, result = prepare_serial_batch_report(columns, data)
		export_rows, _, _ = build_xlsx_data(frappe._dict(columns=result_columns, result=result))
		self.assertEqual(export_rows, [["Serial", "Batch", "Qty"], ["Report-001", "Report-001", 2]])
		self.assertEqual(data, [[self.serial.name, self.batch.name, 2]])
		self.assertEqual(result[0].serial, self.serial.name)
		self.assertEqual(result[0].batch, self.batch.name)

	def test_empty_results_keep_column_visibility(self):
		columns, data = prepare_serial_batch_report(
			[{"label": "Batch", "fieldname": "batch", "fieldtype": "Link", "options": "Batch", "hidden": 1}],
			[],
		)
		self.assertEqual(data, [])
		self.assertEqual(columns[0].fieldname, "batch_number")
		self.assertTrue(all(column["hidden"] for column in columns))

	def test_available_serials_include_legacy_ledger_text(self):
		entries = [
			frappe._dict(
				item_code=self.item.name,
				warehouse="Stores - _TC",
				serial_no=self.serial.name,
				actual_qty=qty,
				stock_value_difference=qty * 10,
			)
			for qty in (1, -1)
		]
		rows = process_stock_ledger_entries(entries, {self.item.name: {}}, None, 2)
		columns = [{"label": "Balance", "fieldname": "balance_serial_no", "fieldtype": "Small Text"}]
		_, result = prepare_serial_batch_report(columns, rows, serial_fields=("balance_serial_no",))
		self.assertEqual([row.balance_serial_no for row in result], [self.serial.name, ""])
		self.assertEqual([row.balance_serial_no_number for row in result], ["Report-001", ""])

	def make_number(self, doctype, number, item_code=None):
		identity = SerialBatchIdentity(doctype)
		return frappe.get_doc(
			{
				"doctype": doctype,
				identity.item_field: item_code or self.item.name,
				identity.number_field: number,
				"company": "_Test Company",
			}
		).insert()
