# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import make_debit_note
from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_invoice
from erpnext.buying.doctype.purchase_order.test_purchase_order import (
	create_pr_against_po,
	create_purchase_order,
)
from erpnext.buying.report.purchase_order_analysis.purchase_order_analysis import execute
from erpnext.stock.doctype.item.test_item import create_item

ITEM_CODE = "_Test PO Analysis Item"


class TestPurchaseOrderAnalysis(FrappeTestCase):
	def get_filters(self, **filters):
		return {
			"company": "_Test Company",
			"from_date": add_days(nowdate(), -1),
			"to_date": add_days(nowdate(), 1),
			**filters,
		}

	def make_purchase_order(self, qty):
		create_item(ITEM_CODE)
		return create_purchase_order(item_code=ITEM_CODE, qty=qty)

	def test_billed_qty_leaves_out_debit_notes_that_keep_the_order_billed(self):
		po = self.make_purchase_order(qty=10)
		pi = make_purchase_invoice(po.name)
		pi.items[0].qty = 6
		pi.insert().submit()

		debit_note = make_debit_note(pi.name)
		debit_note.items[0].qty = -2
		debit_note.insert().submit()

		row = next(row for row in execute(self.get_filters())[1] if row["purchase_order"] == po.name)
		self.assertEqual(row["billed_qty"], 6)
		self.assertEqual(row["billed_amount"], 3000)

	def test_closed_order_has_nothing_pending(self):
		po = self.make_purchase_order(qty=10)
		create_pr_against_po(po.name, received_qty=4)
		po.reload()
		po.update_status("Closed")

		row = next(row for row in execute(self.get_filters())[1] if row["purchase_order"] == po.name)
		self.assertEqual((row["pending_qty"], row["qty_to_bill"], row["pending_amount"]), (0, 0, 0))
