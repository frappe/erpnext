from unittest.mock import patch

import frappe
from bs4 import BeautifulSoup
from frappe.utils import escape_html
from frappe.utils.print_format_generator import PrintFormatGenerator
from frappe.www.printview import set_link_titles

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.stock.serial_batch_identity import SerialBatchIdentity
from erpnext.tests.utils import ERPNextTestSuite


class TestSerialBatchPrint(ERPNextTestSuite):
	def make_print(self, number="PRINT-SERIAL"):
		item = make_item(properties={"has_serial_no": 1, "has_batch_no": 1})
		serial = SerialBatchIdentity("Serial No").resolve(item.name, [number], create=True)[0]
		batch = SerialBatchIdentity("Batch").resolve(item.name, ["PRINT-BATCH"], create=True)[0]
		doc = make_purchase_receipt(
			item_code=item.name,
			qty=1,
			rate=100,
			use_serial_batch_fields=1,
			serial_no=serial,
			batch_no=batch,
			do_not_submit=True,
		)
		table = {
			"fieldtype": "Table",
			"fieldname": "items",
			"table_columns": [
				{"fieldname": "serial_no", "fieldtype": "Small Text", "label": "Serial No", "width": 50},
				{
					"fieldname": "batch_no",
					"fieldtype": "Link",
					"options": "Batch",
					"label": "Batch No",
					"width": 50,
				},
			],
		}
		print_format = frappe.new_doc("Print Format")
		print_format.update(
			{
				"doc_type": "Purchase Receipt",
				"print_format_builder_beta": 1,
				"pdf_generator": "chrome",
				"format_data": frappe.as_json({"sections": [{"columns": [{"fields": [table]}]}]}),
			}
		)
		set_link_titles(doc)
		return doc, print_format

	def test_builder_preview_displays_physical_numbers(self):
		doc, print_format = self.make_print()
		serial, batch = doc.items[0].serial_no, doc.items[0].batch_no
		for _ in range(2):
			html = PrintFormatGenerator(print_format, doc).get_html_preview()
			self.assertIn("PRINT-SERIAL", html)
			self.assertIn("PRINT-BATCH", html)
			self.assertNotIn(serial, html)
			self.assertNotIn(batch, html)
			self.assertEqual(doc.items[0].serial_no, serial)
			self.assertEqual(doc.items[0].batch_no, batch)
			self.assertEqual(doc.as_dict()["items"][0]["serial_no"], serial)

	def test_builder_pdf_receives_physical_numbers(self):
		doc, print_format = self.make_print()
		serial = doc.items[0].serial_no
		with patch("frappe.utils.pdf.get_chrome_pdf", return_value=b"pdf") as render_pdf:
			self.assertEqual(PrintFormatGenerator(print_format, doc).render_pdf(), b"pdf")
		html = render_pdf.call_args.kwargs["html"]
		self.assertIn("PRINT-SERIAL", html)
		self.assertNotIn(serial, html)
		self.assertEqual(doc.items[0].serial_no, serial)

	def test_builder_canvas_displays_physical_numbers(self):
		from frappe.utils.print_format_generator import get_formatted_field_values

		doc, _ = self.make_print()
		values = get_formatted_field_values(doc.doctype, doc.name)
		self.assertEqual(values["child"]["items"][0]["serial_no"], "PRINT-SERIAL")
		self.assertEqual(values["child"]["items"][0]["batch_no"], "PRINT-BATCH")
		self.assertEqual(frappe.get_doc(doc.doctype, doc.name).items[0].serial_no, doc.items[0].serial_no)

	def test_print_escapes_physical_serial_numbers(self):
		number = "PRINT-<img src=x onerror=alert(1)>"
		doc, print_format = self.make_print(number)
		serial = doc.items[0].serial_no
		html = PrintFormatGenerator(print_format, doc).get_html_preview()
		self.assertIn(escape_html(number), html)
		self.assertNotIn(number, html)
		self.assertEqual(doc.items[0].serial_no, serial)

	def test_print_preserves_pending_physical_input(self):
		doc, print_format = self.make_print()
		row = doc.items[0]
		serial = row.serial_no
		row.__dict__["__serial_batch_input"] = ["serial_no"]
		html = PrintFormatGenerator(print_format, doc).get_html_preview()
		self.assertIn(serial, html)
		self.assertNotIn("PRINT-SERIAL", html)
		self.assertEqual(row.serial_no, serial)
		self.assertEqual(row.get("__serial_batch_input"), ["serial_no"])

	def test_formatting_fetches_serial_labels_for_all_rows_together(self):
		doc, _ = self.make_print()
		serial = doc.items[0].serial_no
		other_serial = SerialBatchIdentity("Serial No").resolve(
			doc.items[0].item_code, ["OTHER-PRINT-SERIAL"], create=True
		)[0]
		doc.append("items", {"item_code": doc.items[0].item_code, "serial_no": other_serial})
		with patch.object(
			SerialBatchIdentity, "labels", autospec=True, side_effect=SerialBatchIdentity.labels
		) as labels:
			self.assertEqual(doc.items[0].get_formatted("serial_no"), "PRINT-SERIAL")
			self.assertEqual(doc.items[1].get_formatted("serial_no"), "OTHER-PRINT-SERIAL")
			self.assertEqual(doc.items[0].get_formatted("serial_no"), "PRINT-SERIAL")
		self.assertEqual(labels.call_count, 1)
		self.assertEqual(set(labels.call_args.args[1]), {serial, other_serial})
		self.assertNotIn("__serial_number_labels", doc.as_dict()["items"][0])

	def test_custom_print_can_still_look_up_serial_by_id(self):
		doc, _ = self.make_print()
		template = (
			"{{ frappe.db.get_value('Serial No', doc.items[0].serial_no, 'serial_no') }} / "
			"{{ doc.items[0].get_formatted('serial_no') }}"
		)
		self.assertEqual(frappe.render_template(template, {"doc": doc}), "PRINT-SERIAL / PRINT-SERIAL")

	def test_merged_builder_columns_preserve_special_characters(self):
		for number in ("SERIAL-&<001>", "SERIAL-\"quote\"-'single'", "SERIAL-&amp;-&lt;"):
			for primary in (True, False):
				with self.subTest(number=number, primary=primary):
					doc, print_format = self.make_print(number)
					serial = doc.items[0].serial_no
					layout = frappe.parse_json(print_format.format_data)
					table = layout["sections"][0]["columns"][0]["fields"][0]
					serial_column, batch_column = table["table_columns"]
					column, merged = (
						(serial_column, batch_column) if primary else (batch_column, serial_column)
					)
					column["merged_fields"] = [{**merged, "style": "secondary"}]
					table["table_columns"] = [column]
					print_format.format_data = frappe.as_json(layout)
					generator = PrintFormatGenerator(print_format, doc)
					preview = generator.get_html_preview()
					with patch("frappe.utils.pdf.get_chrome_pdf", return_value=b"pdf") as render_pdf:
						generator.render_pdf()
					for html in (preview, render_pdf.call_args.kwargs["html"]):
						cells = BeautifulSoup(html, "html.parser").select(".cell-line")
						self.assertIn(number, [cell.get_text() for cell in cells])
						self.assertTrue(all(cell.find() is None for cell in cells))
						self.assertNotIn(serial, html)
					self.assertEqual(doc.items[0].serial_no, serial)
