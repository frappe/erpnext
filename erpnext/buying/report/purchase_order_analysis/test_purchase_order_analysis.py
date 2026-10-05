# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from frappe.utils import add_days, nowdate

from erpnext.accounts.doctype.purchase_invoice.mapper import make_debit_note
from erpnext.buying.doctype.purchase_order.mapper import make_purchase_invoice
from erpnext.buying.doctype.purchase_order.test_purchase_order import (
	create_pr_against_po,
	create_purchase_order,
)
from erpnext.buying.report.purchase_order_analysis.purchase_order_analysis import (
	AGGREGATED_FIELDS,
	execute,
	group_by_item,
)
from erpnext.stock.doctype.item.test_item import create_item
from erpnext.tests.utils import ERPNextTestSuite

ITEM_CODE = "_Test PO Analysis Item"


class TestPurchaseOrderAnalysis(ERPNextTestSuite):
	def get_filters(self, **filters):
		return {
			"company": "_Test Company",
			"from_date": add_days(nowdate(), -1),
			"to_date": add_days(nowdate(), 1),
			**filters,
		}

	def make_purchase_order(self, qty, uom=None):
		create_item(ITEM_CODE)
		po = create_purchase_order(item_code=ITEM_CODE, qty=qty, do_not_save=True)
		if uom:
			po.items[0].uom = uom
		po.set_missing_values()
		po.insert()
		po.submit()
		return po

	def add_uom(self, uom, conversion_factor):
		item = frappe.get_doc("Item", ITEM_CODE)
		if not any(row.uom == uom for row in item.uoms):
			item.append("uoms", {"uom": uom, "conversion_factor": conversion_factor})
			item.save()

	def make_item_row(self, company, qty):
		row = frappe._dict(dict.fromkeys(AGGREGATED_FIELDS, 0))
		row.update({"company": company, "item_code": ITEM_CODE, "uom": "Nos", "qty": qty})
		return row

	def get_item_rows(self, data):
		return [row for row in data if row["item_code"] == ITEM_CODE]

	def test_report_executes_and_lists_po(self):
		po = create_purchase_order(company="_Test Company")

		result = execute(self.get_filters())
		columns, data = result[0], result[1]

		self.assertTrue(columns)
		self.assertIn(po.name, {row.get("purchase_order") for row in data})

	def test_group_by_item_across_purchase_orders(self):
		po = self.make_purchase_order(qty=10)
		billed_po = self.make_purchase_order(qty=4)
		create_pr_against_po(po.name, received_qty=3)

		pi = make_purchase_invoice(billed_po.name)
		pi.items[0].qty = 2
		pi.insert().submit()

		columns, data, message, chart = execute(self.get_filters(group_by_item=1))

		expected_value = {
			"uom": "Nos",
			"qty": 14,
			"received_qty": 3,
			"pending_qty": 11,
			"billed_qty": 2,
			"qty_to_bill": 12,
			"amount": 7000,
			"received_qty_amount": 1500,
			"billed_amount": 1000,
			"pending_amount": 6000,
		}
		rows = self.get_item_rows(data)
		self.assertEqual(len(rows), 1)
		for key, val in expected_value.items():
			with self.subTest(key=key, val=val):
				self.assertEqual(rows[0][key], val)

		fieldnames = [column["fieldname"] for column in columns]
		self.assertIn("uom", fieldnames)
		self.assertNotIn("purchase_order", fieldnames)

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

	def test_group_by_item_keeps_each_uom_apart(self):
		self.make_purchase_order(qty=10)
		self.add_uom("Box", 10)
		self.make_purchase_order(qty=2, uom="Box")

		columns, data, message, chart = execute(self.get_filters(group_by_item=1))

		self.assertEqual(
			[(row["uom"], row["qty"]) for row in self.get_item_rows(data)],
			[("Box", 2), ("Nos", 10)],
		)

	def test_group_by_filters_cannot_be_combined(self):
		self.assertRaises(
			frappe.ValidationError,
			execute,
			self.get_filters(group_by_po=1, group_by_item=1),
		)

	def test_group_by_item_keeps_each_company_apart(self):
		rows = [
			self.make_item_row("_Test Company", 10),
			self.make_item_row("_Test Company 1", 4),
			self.make_item_row("_Test Company", 6),
		]

		self.assertEqual(
			[(row["company"], row["qty"]) for row in group_by_item(rows)],
			[("_Test Company", 16), ("_Test Company 1", 4)],
		)

	def test_company_falls_back_to_the_default(self):
		po = self.make_purchase_order(qty=10)
		filters = self.get_filters(company=None)

		with patch("erpnext.get_default_company", return_value="_Test Company"):
			columns, data, message, chart = execute(filters)

		self.assertIn(po.name, [row["purchase_order"] for row in data])

		with patch("erpnext.get_default_company", return_value="_Test Company 1"):
			columns, data, message, chart = execute(filters)

		self.assertNotIn(po.name, [row["purchase_order"] for row in data])

	def test_company_is_mandatory_without_a_default(self):
		with patch("erpnext.get_default_company", return_value=None):
			self.assertRaises(frappe.ValidationError, execute, self.get_filters(company=None))
