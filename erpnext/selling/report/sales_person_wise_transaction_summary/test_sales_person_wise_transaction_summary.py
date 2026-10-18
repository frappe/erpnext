# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.selling.report.sales_person_wise_transaction_summary.sales_person_wise_transaction_summary import (
	execute,
)
from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.tests.utils import ERPNextTestSuite


class TestSalesPersonWiseTransactionSummary(ERPNextTestSuite):
	"""Item-level summary joining a sales document with its Sales Team rows, showing
	each sales person's contributed qty and amount per item line."""

	def setUp(self):
		self.sales_person = "_Test Sales Person"

	def make_invoice_with_commission(self, qty=5, rate=200, percentage=100):
		si = create_sales_invoice(
			item="_Test Item", qty=qty, rate=rate, do_not_save=True, posting_date="2026-06-01"
		)
		si.append("sales_team", {"sales_person": self.sales_person, "allocated_percentage": percentage})
		si.insert()
		si.submit()
		return si

	def make_closed_delivery_note_in_box_uom(self, qty=1, rate=1000):
		# Box = 10 Nos; base rate is per Box, so the delivered amount must stay per Box
		item = make_item(
			properties={"is_stock_item": 0},
			uoms=[{"uom": "Box", "conversion_factor": 10}],
		)
		dn = create_delivery_note(
			item=item.name, qty=qty, rate=rate, do_not_save=True, posting_date="2026-06-01"
		)
		dn.items[0].uom = "Box"
		dn.items[0].conversion_factor = 10
		dn.append("sales_team", {"sales_person": self.sales_person, "allocated_percentage": 100})
		dn.insert()
		dn.submit()
		dn.db_set("status", "Closed")
		return dn

	def make_invoice_split_between_two_sales_persons(self, qty=5, rate=200):
		si = create_sales_invoice(
			item="_Test Item", qty=qty, rate=rate, do_not_save=True, posting_date="2026-06-01"
		)
		si.append("sales_team", {"sales_person": "_Test Sales Person", "allocated_percentage": 60})
		si.append("sales_team", {"sales_person": "_Test Sales Person 1", "allocated_percentage": 40})
		si.insert()
		si.submit()
		return si

	def run_report(self, **extra):
		filters = frappe._dict(
			{"company": "_Test Company", "doc_type": "Sales Invoice", "sales_person": self.sales_person}
		)
		filters.update(extra)
		return execute(filters)[1]

	def test_doc_type_is_mandatory(self):
		self.assertRaises(frappe.ValidationError, execute, frappe._dict({"company": "_Test Company"}))

	def test_invalid_doc_type_throws(self):
		self.assertRaises(
			frappe.ValidationError,
			execute,
			frappe._dict({"company": "_Test Company", "doc_type": "Purchase Invoice"}),
		)

	def test_item_line_contribution(self):
		si = self.make_invoice_with_commission(qty=5, rate=200, percentage=100)
		item = si.items[0]

		rows = self.run_report()
		row = next((r for r in rows if r[0] == si.name and r[5] == "_Test Item"), None)
		self.assertIsNotNone(row, "Invoice item line missing from report")

		# row: name, customer, territory, warehouse, posting_date, item_code, item_group,
		#      brand, stock_qty, base_net_amount, sales_person, allocated_percentage,
		#      contributed_qty, contribution_amt, currency
		self.assertEqual(row[1], si.customer)
		self.assertEqual(row[8], item.stock_qty)
		self.assertEqual(row[9], item.base_net_amount)
		self.assertEqual(row[10], self.sales_person)
		self.assertEqual(row[11], 100)
		self.assertEqual(row[12], item.stock_qty * 100 / 100)  # contributed qty
		self.assertEqual(row[13], item.base_net_amount * 100 / 100)  # contribution amount

	def test_closed_document_amount_not_scaled_by_conversion_factor(self):
		dn = self.make_closed_delivery_note_in_box_uom(qty=1, rate=1000)
		rows = self.run_report(doc_type="Delivery Note")
		row = next((r for r in rows if r[0] == dn.name), None)
		self.assertIsNotNone(row, "Closed delivery note missing from report")
		self.assertEqual(row[8], 10)  # stock qty: 1 Box = 10 Nos
		self.assertEqual(row[9], 1000)  # amount stays per Box, not multiplied by the conversion factor

	def test_qty_and_amount_shown_once_per_item_line(self):
		si = self.make_invoice_split_between_two_sales_persons(qty=5, rate=200)
		item = si.items[0]
		rows = [
			r for r in self.run_report(sales_person="Sales Team") if r[0] == si.name and r[5] == "_Test Item"
		]
		self.assertEqual(len(rows), 2)
		# qty and amount on the first row of the line only; the rest are blank
		self.assertEqual(rows[0][8], item.stock_qty)
		self.assertEqual(rows[0][9], item.base_net_amount)
		self.assertIsNone(rows[1][8])
		self.assertIsNone(rows[1][9])

	def test_no_blank_row_appended(self):
		self.make_invoice_with_commission()
		rows = self.run_report()
		self.assertTrue(rows)
		self.assertTrue(all(r[0] for r in rows), "execute should not append a blank row")
