import frappe
from frappe.utils import now_datetime

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.serial_batch_bundle import get_serial_or_batch_nos
from erpnext.tests.utils import ERPNextTestSuite


class TestSerialBatchPrinting(ERPNextTestSuite):
	def test_serial_print_preserves_spelling_order_and_references(self):
		bundles = [self.make_bundle(serial_numbers=["Z<001>", "A&002"]) for _ in range(2)]
		for bundle in bundles:
			self.assert_print(bundle, "Z&lt;001&gt;, A&amp;002")
		self.assertNotEqual(bundles[0].entries[0].serial_no, bundles[1].entries[0].serial_no)

	def test_batch_print_shows_number_and_quantity(self):
		bundle = self.make_bundle(batch_number="LOT<001>")
		self.assert_print(bundle, "<tr><td>LOT&lt;001&gt;</td><td>3.0</td></tr>")

	def test_combined_print_shows_both_numbers(self):
		bundle = self.make_bundle(serial_numbers=["SER&001"], batch_number="LOT<001>")
		self.assert_print(bundle, "<tr><td>LOT&lt;001&gt;</td><td>SER&amp;001</td><td>1.0</td></tr>")

	def assert_print(self, bundle, expected):
		before = bundle.reload().as_dict()
		row = frappe._dict(serial_and_batch_bundle=bundle.name)
		for _ in range(2):
			html = get_serial_or_batch_nos(bundle.name)
			self.assertIn(expected, html)
			for entry in bundle.entries:
				for name in (entry.serial_no, entry.batch_no):
					if name:
						self.assertNotIn(name, html)
			self.assertEqual(
				frappe.render_template(
					"templates/print_formats/includes/serial_and_batch_bundle.html", {"doc": row}
				).strip(),
				html,
			)
		self.assertEqual(row.serial_and_batch_bundle, bundle.name)
		self.assertEqual(bundle.as_dict(), before)
		self.assertEqual(bundle.reload().as_dict(), before)

	def make_bundle(self, serial_numbers=None, batch_number=None):
		item = make_item(
			properties={"has_serial_no": bool(serial_numbers), "has_batch_no": bool(batch_number)}
		)
		batch = None
		if batch_number:
			batch = frappe.get_doc(doctype="Batch", item=item.name, batch_id=batch_number).insert().name
		entries = []
		for number in serial_numbers or []:
			serial = frappe.get_doc(
				doctype="Serial No",
				item_code=item.name,
				serial_no=number,
				batch_no=batch,
				company="_Test Company",
			).insert()
			entries.append({"serial_no": serial.name, "batch_no": batch, "qty": 1})
		if not serial_numbers:
			entries.append({"batch_no": batch, "qty": 3})
		return frappe.get_doc(
			doctype="Serial and Batch Bundle",
			item_code=item.name,
			has_serial_no=bool(serial_numbers),
			has_batch_no=bool(batch_number),
			company="_Test Company",
			warehouse="Stores - _TC",
			voucher_type="Purchase Receipt",
			type_of_transaction="Inward",
			posting_datetime=now_datetime(),
			entries=entries,
		).insert()
