import frappe

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.serial_batch_identity import SerialBatchIdentity, validate_item_merge
from erpnext.stock.utils import scan_barcode
from erpnext.tests.utils import ERPNextTestSuite


class TestSerialBatchIdentityMatching(ERPNextTestSuite):
	def make_number(self, doctype, number):
		identity = SerialBatchIdentity(doctype)
		item = make_item(
			properties={"has_serial_no": int(doctype == "Serial No"), "has_batch_no": int(doctype == "Batch")}
		)
		name = identity.resolve(item.name, [number], create=True, defaults={"company": "_Test Company"})[0]
		return identity, item, name

	def test_case_insensitive_resolution_preserves_physical_label(self):
		for doctype in ("Serial No", "Batch"):
			identity, item, name = self.make_number(doctype, "Mixed-Lot-001")
			for number in ("mixed-lot-001", "MIXED-LOT-001"):
				self.assertEqual(identity.resolve(item.name, [number]), [name])
				self.assertEqual(identity.resolve(item.name, [number], create=True), [name])
			self.assertEqual(identity.labels([name]), {name: "Mixed-Lot-001"})

	def test_case_insensitive_scan_keeps_items_separate(self):
		for doctype, field in (("Serial No", "serial_no"), ("Batch", "batch_no")):
			number = "SCAN-" + frappe.generate_hash().upper()
			_, item_a, name_a = self.make_number(doctype, number)
			_, item_b, name_b = self.make_number(doctype, number.lower())
			matches = scan_barcode(number.swapcase(), allow_multiple=True)["candidates"]
			self.assertEqual({match[field] for match in matches}, {name_a, name_b})
			for item, name in ((item_a, name_a), (item_b, name_b)):
				self.assertEqual(scan_barcode(number.swapcase(), {"item_code": item.name})[field], name)

	def test_controller_rejects_case_variant_for_same_item(self):
		for doctype in ("Serial No", "Batch"):
			identity, _, name = self.make_number(doctype, "Mixed-Lot-001")
			duplicate = frappe.copy_doc(frappe.get_doc(doctype, name))
			duplicate.set(identity.number_field, "MIXED-LOT-001")
			with self.assertRaises(frappe.DuplicateEntryError):
				duplicate.insert()

	def test_database_rejects_case_variant_without_controller_validation(self):
		for doctype in ("Serial No", "Batch"):
			identity, _, name = self.make_number(doctype, "Mixed-Lot-001")
			duplicate = frappe.get_doc(doctype, name)
			duplicate.name = frappe.generate_hash()
			duplicate.set(identity.number_field, "MIXED-LOT-001")
			frappe.db.savepoint("case_variant")
			try:
				with self.assertRaises((frappe.DuplicateEntryError, frappe.UniqueValidationError)):
					duplicate.db_insert()
			finally:
				frappe.db.rollback(save_point="case_variant")

	def test_item_merge_rejects_case_variants(self):
		for doctype in ("Serial No", "Batch"):
			_, item_a, _ = self.make_number(doctype, "Mixed-Lot-001")
			_, item_b, _ = self.make_number(doctype, "MIXED-LOT-001")
			with self.assertRaises(frappe.ValidationError):
				validate_item_merge(item_a.name, item_b.name)

	def test_generated_numbers_skip_case_variant_collisions(self):
		from erpnext.stock.doctype.serial_no.serial_no import get_new_serial_number

		for doctype in ("Serial No", "Batch"):
			prefix = "CASE-" + frappe.generate_hash().upper() + "-"
			_, item, _ = self.make_number(doctype, prefix.lower() + "00001")
			series = prefix + ".#####"
			if doctype == "Serial No":
				number = get_new_serial_number(series, item.name)
			else:
				item.create_new_batch = 1
				item.batch_number_series = series
				item.save()
				number = frappe.get_doc({"doctype": "Batch", "item": item.name}).insert().batch_id
			self.assertEqual(number, prefix + "00002")
