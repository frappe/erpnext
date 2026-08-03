# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestSalesAndPurchaseReturn(ERPNextTestSuite):
	@staticmethod
	def _cancel_and_delete(doctype, name):
		if not frappe.db.exists(doctype, name):
			return
		doc = frappe.get_doc(doctype, name)
		if doc.docstatus == 1:
			doc.cancel()
		frappe.delete_doc(doctype, name, force=1)

	def test_purchase_invoice_zero_qty_return_is_rejected(self):
		# A return with every item at qty 0 moves no stock and no value, so it must be
		# rejected the same way a return with no items at all would be.
		from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice

		pi = make_purchase_invoice(qty=10)
		self.addCleanup(self._cancel_and_delete, "Purchase Invoice", pi.name)

		return_pi = make_purchase_invoice(
			is_return=1,
			return_against=pi.name,
			qty=0,
			do_not_save=True,
		)

		self.assertRaises(frappe.ValidationError, return_pi.save)

	def test_purchase_invoice_item_name_only_zero_qty_return_is_rejected(self):
		# Item Code is not mandatory on Purchase Invoice Item - a row can have only an
		# item_name (e.g. a free-text/non-stock line). Such rows fall through to the
		# item_name-only branch, which must also reject an all-zero-qty return instead
		# of unconditionally treating the row as returned.
		from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice

		pi = make_purchase_invoice(item_name="_Test Item", qty=10, do_not_submit=True)
		pi.items[0].item_code = ""
		pi.save()
		pi.submit()
		self.addCleanup(self._cancel_and_delete, "Purchase Invoice", pi.name)

		return_pi = make_purchase_invoice(
			item_name="_Test Item",
			is_return=1,
			return_against=pi.name,
			qty=0,
			do_not_save=True,
		)
		return_pi.items[0].item_code = ""

		self.assertRaises(frappe.ValidationError, return_pi.save)
