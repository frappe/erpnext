# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

"""End-to-end procure-to-pay flow tests.

These exercise the full purchase cycle across module boundaries and assert that
quantity/billing status propagates between documents and that the money and
stock invariants hold (outstanding cleared on payment, received qty reduced on
return).
"""

import frappe
from frappe.utils import flt

from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.buying.doctype.purchase_order.mapper import make_purchase_receipt
from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
from erpnext.controllers.sales_and_purchase_return import make_return_doc
from erpnext.stock.doctype.material_request.mapper import make_purchase_order
from erpnext.stock.doctype.material_request.test_material_request import make_material_request
from erpnext.stock.doctype.purchase_receipt.mapper import make_purchase_invoice
from erpnext.tests.utils import ERPNextTestSuite


class TestProcureToPayFlow(ERPNextTestSuite):
	def test_full_chain_po_to_receipt_to_invoice_to_payment(self):
		po = create_purchase_order(qty=10, rate=100)  # total 1000

		pr = make_purchase_receipt(po.name)
		pr.submit()
		po.reload()
		self.assertEqual(po.per_received, 100)

		pi = make_purchase_invoice(pr.name)
		pi.submit()
		po.reload()
		self.assertEqual(po.per_billed, 100)
		self.assertEqual(flt(pi.outstanding_amount), 1000)

		pe = get_payment_entry("Purchase Invoice", pi.name, bank_account="_Test Cash - _TC")
		pe.submit()

		outstanding, status = frappe.db.get_value(
			"Purchase Invoice", pi.name, ["outstanding_amount", "status"]
		)
		self.assertEqual(flt(outstanding), 0)
		self.assertEqual(status, "Paid")

	def test_partial_receipt_and_billing_propagates_status(self):
		po = create_purchase_order(qty=10, rate=100)

		pr = make_purchase_receipt(po.name)
		pr.items[0].qty = 6
		pr.submit()
		po.reload()
		self.assertEqual(po.per_received, 60)
		# still has qty left to receive and nothing billed yet
		self.assertEqual(po.status, "To Receive and Bill")

		pi = make_purchase_invoice(pr.name)
		pi.submit()
		po.reload()
		self.assertEqual(po.per_billed, 60)

	def test_material_request_to_purchase_order_marks_it_ordered(self):
		mr = make_material_request(qty=10)

		po = make_purchase_order(mr.name)
		po.supplier = "_Test Supplier"
		for item in po.items:
			item.rate = 100
		po.submit()

		mr.reload()
		self.assertEqual(mr.per_ordered, 100)
		self.assertEqual(mr.status, "Ordered")

	def test_purchase_return_reduces_received_qty_on_order(self):
		po = create_purchase_order(qty=10, rate=100)

		pr = make_purchase_receipt(po.name)
		pr.submit()
		po.reload()
		self.assertEqual(po.per_received, 100)

		return_pr = make_return_doc("Purchase Receipt", pr.name)
		return_pr.items[0].qty = -4
		return_pr.items[0].received_qty = -4
		return_pr.submit()

		po.reload()
		self.assertEqual(po.per_received, 60)
