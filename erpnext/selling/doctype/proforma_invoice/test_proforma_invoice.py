# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import json

import frappe
from frappe.utils import flt

from erpnext.selling.doctype.proforma_invoice.proforma_invoice import make_proforma_invoice
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.tests.utils import ERPNextTestSuite


class TestProformaInvoice(ERPNextTestSuite):
	def setUp(self):
		frappe.db.set_single_value("Selling Settings", "enable_proforma_invoice", 1)

	def create_proforma(self, sales_order, lines, **kwargs):
		items = [{"so_detail": so_detail, "qty": qty} for so_detail, qty in lines]
		name = make_proforma_invoice(sales_order.name, json.dumps(items), **kwargs)
		return frappe.get_doc("Proforma Invoice", name)

	def test_partial_proforma_is_non_blocking(self):
		"""A proforma must not touch delivery/billing or the source Sales Order."""
		sales_order = make_sales_order(qty=10)
		so_detail = sales_order.items[0].name

		proforma = self.create_proforma(sales_order, [(so_detail, 4)])

		self.assertEqual(proforma.status, "Issued")
		self.assertEqual(proforma.docstatus, 1)
		self.assertTrue(proforma.proforma_pdf, "PDF should be generated and attached")

		sales_order.reload()
		item = sales_order.items[0]
		# fulfillment untouched
		self.assertEqual(flt(item.delivered_qty), 0)
		self.assertEqual(flt(item.billed_amt), 0)
		self.assertEqual(flt(sales_order.per_delivered), 0)
		self.assertEqual(flt(sales_order.per_billed), 0)
		# ordered qty untouched (in-memory SO copy never persisted)
		self.assertEqual(flt(item.qty), 10)

	def test_taxes_scale_to_partial_qty(self):
		sales_order = make_sales_order(qty=10, do_not_submit=True)
		sales_order.append(
			"taxes",
			{
				"charge_type": "On Net Total",
				"account_head": "_Test Account CST - _TC",
				"description": "CST",
				"rate": 10,
			},
		)
		sales_order.submit()

		# full order: net 1000 + 10% tax = 1100
		self.assertEqual(flt(sales_order.grand_total), 1100)

		proforma = self.create_proforma(sales_order, [(sales_order.items[0].name, 4)])
		# partial (4 of 10): net 400 + 10% tax = 440
		self.assertEqual(flt(proforma.grand_total), 440)

	def test_feature_toggle_is_enforced(self):
		sales_order = make_sales_order(qty=10)
		frappe.db.set_single_value("Selling Settings", "enable_proforma_invoice", 0)

		self.assertRaises(
			frappe.ValidationError,
			self.create_proforma,
			sales_order,
			[(sales_order.items[0].name, 4)],
		)
