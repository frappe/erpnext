# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import frappe
from frappe.utils import cint

from erpnext.selling.doctype.product_bundle.test_product_bundle import make_product_bundle
from erpnext.stock.doctype.delivery_note.mapper import make_packing_slip
from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.tests.utils import ERPNextTestSuite


class TestPackingSlip(ERPNextTestSuite):
	def test_packing_slip(self):
		# Step - 1: Create a Product Bundle
		items = create_items()
		make_product_bundle(items[0], items[1:], 5)

		# Step - 2: Create a Delivery Note (Draft) with Product Bundle
		dn = create_delivery_note(
			item_code=items[0],
			qty=2,
			do_not_save=True,
		)
		dn.append(
			"items",
			{
				"item_code": items[1],
				"warehouse": "_Test Warehouse - _TC",
				"qty": 10,
			},
		)
		dn.save()

		# Step - 3: Make a Packing Slip from Delivery Note for 4 Qty
		ps1 = make_packing_slip(dn.name)
		for item in ps1.items:
			item.qty = 4
		ps1.save()
		ps1.submit()

		# Test - 1: `Packed Qty` should be updated to 4 in Delivery Note Items and Packed Items.
		dn.load_from_db()
		for item in dn.items:
			if not frappe.db.exists("Product Bundle", {"new_item_code": item.item_code}):
				self.assertEqual(item.packed_qty, 4)

		for item in dn.packed_items:
			self.assertEqual(item.packed_qty, 4)

		# Step - 4: Make another Packing Slip from Delivery Note for 6 Qty
		ps2 = make_packing_slip(dn.name)
		ps2.save()
		ps2.submit()

		# Test - 2: `Packed Qty` should be updated to 10 in Delivery Note Items and Packed Items.
		dn.load_from_db()
		for item in dn.items:
			if not frappe.db.exists("Product Bundle", {"new_item_code": item.item_code}):
				self.assertEqual(item.packed_qty, 10)

		for item in dn.packed_items:
			self.assertEqual(item.packed_qty, 10)

		# Step - 5: Cancel Packing Slip [1]
		ps1.cancel()

		# Test - 3: `Packed Qty` should be updated to 4 in Delivery Note Items and Packed Items.
		dn.load_from_db()
		for item in dn.items:
			if not frappe.db.exists("Product Bundle", {"new_item_code": item.item_code}):
				self.assertEqual(item.packed_qty, 6)

		for item in dn.packed_items:
			self.assertEqual(item.packed_qty, 6)

		# Step - 6: Cancel Packing Slip [2]
		ps2.cancel()

		# Test - 4: `Packed Qty` should be updated to 0 in Delivery Note Items and Packed Items.
		dn.load_from_db()
		for item in dn.items:
			if not frappe.db.exists("Product Bundle", {"new_item_code": item.item_code}):
				self.assertEqual(item.packed_qty, 0)

		for item in dn.packed_items:
			self.assertEqual(item.packed_qty, 0)

		# Step - 7: Make Packing Slip for more Qty than Delivery Note
		ps3 = make_packing_slip(dn.name)
		ps3.items[0].qty = 20

		# Test - 5: Should throw an ValidationError, as Packing Slip Qty is more than Delivery Note Qty
		self.assertRaises(frappe.exceptions.ValidationError, ps3.save)

		# Step - 8: Make Packing Slip for less Qty than Delivery Note
		ps4 = make_packing_slip(dn.name)
		ps4.items[0].qty = 5
		ps4.save()
		ps4.submit()

		# Test - 6: Delivery Note should throw a ValidationError on Submit, as Packed Qty and Delivery Note Qty are not the same
		dn.load_from_db()
		self.assertRaises(frappe.exceptions.ValidationError, dn.submit)


def create_items():
	items_properties = [
		{"is_stock_item": 0},
		{"is_stock_item": 1, "stock_uom": "Nos"},
		{"is_stock_item": 1, "stock_uom": "Box"},
	]

	items = []
	for properties in items_properties:
		items.append(make_item(properties=properties).name)

	return items


class TestPackingSlipValidation(ERPNextTestSuite):
	"""Package-number and item validations, exercised on the document directly so no
	Delivery Note fixture is needed (the integration test above covers the full pack)."""

	def make_slip(self, **fields):
		doc = frappe.new_doc("Packing Slip")
		doc.update(fields)
		return doc

	def test_from_package_no_must_be_positive(self):
		self.assertRaises(frappe.ValidationError, self.make_slip(from_case_no=0).validate_case_nos)

	def test_to_package_no_cannot_be_less_than_from(self):
		doc = self.make_slip(from_case_no=5, to_case_no=3)
		self.assertRaises(frappe.ValidationError, doc.validate_case_nos)

	def test_to_package_no_defaults_to_from(self):
		doc = self.make_slip(from_case_no=3)
		doc.validate_case_nos()
		self.assertEqual(cint(doc.to_case_no), 3)

	def test_item_qty_must_be_greater_than_zero(self):
		doc = self.make_slip()
		doc.append("items", {"item_code": "_Test Item", "qty": 0, "dn_detail": "dummy"})
		self.assertRaises(frappe.ValidationError, doc.validate_items)

	def test_item_requires_a_source_reference(self):
		doc = self.make_slip()
		# positive qty but neither a Delivery Note Item nor a Packed Item reference
		doc.append("items", {"item_code": "_Test Item", "qty": 1})
		self.assertRaises(frappe.ValidationError, doc.validate_items)
