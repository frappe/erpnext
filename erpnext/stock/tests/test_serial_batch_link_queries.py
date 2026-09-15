import frappe
from frappe.desk.search import build_for_autosuggest
from frappe.utils import add_days, nowdate

from erpnext.controllers.queries import get_batch_no, get_batch_numbers, get_empty_batches
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.report.serial_and_batch_summary.serial_and_batch_summary import (
	get_batch_nos,
	get_serial_nos,
)
from erpnext.stock.serial_batch_identity import SerialBatchIdentity
from erpnext.tests.utils import ERPNextTestSuite


class TestSerialBatchLinkQueries(ERPNextTestSuite):
	def setUp(self):
		self.item = make_item("_Identity Link Item A", {"has_serial_no": 1, "has_batch_no": 1})
		self.other_item = make_item("_Identity Link Item B", {"has_serial_no": 1, "has_batch_no": 1})
		self.warehouse = "_Test Warehouse - _TC"

	def test_batch_link_combines_ledger_quantities_and_uses_physical_title(self):
		batch = self.make_number("Batch", "Link-Batch")
		other = self.make_number("Batch", "Link-Batch", self.other_item.name)
		self.make_ledger(batch_no=batch.name, actual_qty=2)
		self.make_ledger(item_code=self.other_item.name, batch_no=other.name, actual_qty=9)
		bundle = self.make_bundle("Link-Voucher", batch=batch.name, qty=3)
		self.make_ledger(serial_and_batch_bundle=bundle.name, actual_qty=3)
		rows = get_batch_no(
			"Batch",
			"link-batch",
			"name",
			0,
			20,
			{"item_code": self.item.name, "warehouse": self.warehouse},
		)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0][:3], (batch.name, "Link-Batch", 5))
		option = build_for_autosuggest(rows, "Batch")[0]
		self.assertEqual(option["value"], batch.name)
		self.assertEqual(option["label"], "Link-Batch")

	def test_empty_batch_search_preserves_expired_batches(self):
		stocked = self.make_number("Batch", "Link-Stocked")
		empty = self.make_number("Batch", "Link-Empty")
		unrelated = self.make_number("Batch", "Unrelated")
		expired = self.make_number("Batch", "Link-Expired")
		expired.db_set("expiry_date", add_days(nowdate(), -1))
		disabled = self.make_number("Batch", "Link-Disabled")
		disabled.db_set("disabled", 1)
		self.make_number("Batch", "Link-Empty", self.other_item.name)
		filters = {"item_code": self.item.name, "is_inward": 1}
		rows = get_empty_batches(filters, 0, 20, [(stocked.name, 1)], "link-")
		self.assertEqual([row[0] for row in rows], [expired.name, empty.name])
		filters["include_expired_batches"] = 1
		rows = get_empty_batches(filters, 0, 20, [(stocked.name, 1)], "link-")
		self.assertCountEqual([row[0] for row in rows], [empty.name, expired.name])
		self.assertNotIn(unrelated.name, [row[0] for row in rows])
		rows = get_empty_batches(filters, 1, 1, [(stocked.name, 1)], "link-")
		self.assertEqual([row[0] for row in rows], [empty.name])

	def test_batch_number_query_returns_ids_and_titles_for_the_selected_item(self):
		batch = self.make_number("Batch", "Link-Batch")
		other = self.make_number("Batch", "Link-Batch", self.other_item.name)
		rows = get_batch_numbers("Batch", "link-batch", "name", 0, 20, {"item": self.item.name})
		self.assertEqual([tuple(row) for row in rows], [(batch.name, "Link-Batch", self.item.name)])
		option = build_for_autosuggest(rows, "Batch")[0]
		self.assertEqual(option["value"], batch.name)
		self.assertEqual(option["label"], "Link-Batch")
		rows = get_batch_numbers("Batch", batch.name, "name", 0, 20, {"item": self.item.name})
		self.assertEqual([row[0] for row in rows], [batch.name])
		rows = get_batch_numbers("Batch", "link-batch", "name", 0, 20, {})
		self.assertCountEqual([row[0] for row in rows], [batch.name, other.name])
		page = get_batch_numbers("Batch", "link-batch", "name", 1, 1, {})
		self.assertEqual(page, rows[1:2])
		with self.set_user("Guest"), self.assertRaises(frappe.PermissionError):
			get_batch_numbers("Batch", "link-batch", "name", 0, 20, {"item": self.item.name})

	def test_batch_link_search_runs_for_roles_without_batch_document_access(self):
		batch = self.make_number("Batch", "Link-Batch")
		self.make_ledger(batch_no=batch.name, actual_qty=2)
		filters = {"item_code": self.item.name, "warehouse": self.warehouse}
		for role in ("Stock User", "Sales User"):
			with self.subTest(role=role), self.set_user(self.make_user(role)):
				rows = get_batch_no("Batch", "link-batch", "name", 0, 20, filters)
				self.assertEqual(rows[0][:3], (batch.name, "Link-Batch", 2))

	def test_report_links_include_all_selected_vouchers_and_preserve_item_scope(self):
		serials = [self.make_number("Serial No", f"Link-Serial-{i}") for i in (1, 2)]
		batches = [self.make_number("Batch", f"Link-Batch-{i}") for i in (1, 2)]
		for i, (serial, batch) in enumerate(zip(serials, batches, strict=True), start=1):
			self.make_bundle(f"Link-Voucher-{i}", serial=serial.name, batch=batch.name)
		other = self.make_number("Serial No", "Link-Serial-1", self.other_item.name)
		self.make_bundle("Link-Voucher-1", serial=other.name, item_code=self.other_item.name)
		self.make_bundle("Link-Voucher-3", serial=serials[0].name, batch=batches[0].name)
		filters = {
			"item_code": self.item.name,
			"voucher_type": "Stock Entry",
			"voucher_no": ["Link-Voucher-1", "Link-Voucher-2"],
		}
		for doctype, query, records, text in (
			("Serial No", get_serial_nos, serials, "link-serial"),
			("Batch", get_batch_nos, batches, "link-batch"),
		):
			with self.subTest(doctype=doctype):
				rows = query(doctype, text, "name", 0, 20, filters)
				self.assertEqual([row[0] for row in rows], [record.name for record in records])
				self.assertEqual([row[2] for row in rows], [self.item.name, self.item.name])
				page = query(doctype, text, "name", 1, 1, filters)
				self.assertEqual([row[0] for row in page], [records[1].name])
				self.assertEqual(query(doctype, "missing", "name", 0, 20, filters), [])
				with self.set_user("Guest"), self.assertRaises(frappe.PermissionError):
					query(doctype, text, "name", 0, 20, filters)

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

	def make_user(self, role):
		email = f"identity-link-{frappe.scrub(role)}@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				doctype="User",
				email=email,
				first_name="Identity Link",
				send_welcome_email=0,
				roles=[{"role": role}],
			).insert(ignore_permissions=True)
		return email

	def make_bundle(self, voucher, serial=None, batch=None, qty=1, item_code=None):
		bundle = frappe.get_doc(
			doctype="Serial and Batch Bundle",
			item_code=item_code or self.item.name,
			voucher_type="Stock Entry",
			voucher_no=voucher,
			docstatus=1,
			is_cancelled=0,
		)
		bundle.db_insert()
		frappe.get_doc(
			doctype="Serial and Batch Entry",
			parent=bundle.name,
			parenttype=bundle.doctype,
			parentfield="entries",
			serial_no=serial,
			batch_no=batch,
			qty=qty,
			warehouse=self.warehouse,
		).db_insert()
		return bundle

	def make_ledger(self, **values):
		frappe.get_doc(
			{
				"doctype": "Stock Ledger Entry",
				"item_code": self.item.name,
				"warehouse": self.warehouse,
				"posting_date": nowdate(),
				"posting_time": "12:00:00",
				"is_cancelled": 0,
				**values,
			}
		).db_insert()
