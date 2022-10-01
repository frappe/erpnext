import unittest

import frappe


class TestUtils(unittest.TestCase):
	def test_validate_for_items_purchase_receipt_items_qty(self):
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		pr = make_purchase_receipt(do_not_save=True)

		# Reset accepted qty to 0
		for d in pr.items:
			d.qty = 0
			d.received_qty = 0

		# The document should save without any errors.
		pr.save()

		# The document should not be submitted if 0 qty has been accepted.
		self.assertRaises(frappe.ValidationError, pr.submit)
		pr.load_from_db()

		for d in pr.items:
			d.qty = 5
			d.received_qty = 5

		pr.submit()
