# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from unittest.mock import patch

import frappe
from frappe.utils import add_days, flt, getdate, today

from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.buying.doctype.purchase_order.mapper import make_purchase_receipt as make_receipt
from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
from erpnext.buying.doctype.supplier import supplier_overview
from erpnext.buying.doctype.supplier.test_supplier import create_supplier
from erpnext.controllers.item_close import update_closed_status
from erpnext.controllers.sales_and_purchase_return import make_return_doc
from erpnext.stock.doctype.purchase_receipt.mapper import make_purchase_invoice as make_invoice
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt
from erpnext.tests.utils import ERPNextTestSuite

SUPPLIER = "_Test Supplier"
COMPANY = "_Test Company"


class TestSupplierOverview(ERPNextTestSuite):
	def test_overview_sections(self):
		data = supplier_overview.get_supplier_overview(SUPPLIER, COMPANY)
		self.assertEqual(data["period"], "Current Fiscal Year")
		self.assertIn("net_purchases", data["position"])
		self.assertFalse(data["errors"])

	def test_payables_ageing_adds_up_to_outstanding(self):
		data = supplier_overview.get_supplier_payables(SUPPLIER, COMPANY)
		self.assertEqual(flt(data["ageing"]["total"], 2), flt(data["outstanding"]["value"], 2))
		self.assertEqual(flt(data["ageing"]["overdue"], 2), flt(data["overdue"]["value"], 2))

	def test_cash_invoice_counts_as_paid(self):
		supplier = create_supplier(supplier_name="_Test Supplier Overview Cash").name
		pi = make_purchase_invoice(supplier=supplier, is_paid=1, cash_bank_account="Cash - _TC")
		as_of = getdate(today())
		trend = supplier_overview.trend(supplier, COMPANY, as_of.replace(day=1), as_of, True)
		self.assertEqual(flt(trend["paid"], 2), flt(pi.base_paid_amount, 2))

	def test_delivery_stops_at_period_end(self):
		supplier = create_supplier(supplier_name="_Test Supplier Overview Delivery").name
		po = create_purchase_order(
			supplier=supplier, transaction_date=add_days(today(), -10), do_not_submit=True
		)
		po.schedule_date = add_days(today(), -3)
		for item in po.items:
			item.schedule_date = po.schedule_date
		po.submit()

		as_of = getdate(today())
		start = add_days(as_of, -30)
		self.assertEqual(supplier_overview.delivery(supplier, COMPANY, start, as_of, as_of)["overdue"], 1)
		self.assertEqual(
			supplier_overview.delivery(supplier, COMPANY, start, add_days(as_of, -5), as_of)["lines"], 0
		)

		late = supplier_overview.order_tiles(supplier, COMPANY, as_of)["late"]
		self.assertEqual(late["orders"], [po.name])

	def test_pipeline_uses_line_amounts(self):
		supplier = create_supplier(supplier_name="_Test Supplier Overview Lines").name
		po = create_purchase_order(
			supplier=supplier,
			transaction_date=add_days(today(), -10),
			rate=100,
			qty=1,
			do_not_submit=True,
		)
		po.append(
			"items",
			{
				"item_code": "_Test Item 2",
				"qty": 1,
				"rate": 900,
				"warehouse": po.items[0].warehouse,
				"schedule_date": add_days(today(), -3),
			},
		)
		po.items[0].schedule_date = add_days(today(), -5)
		po.schedule_date = po.items[0].schedule_date
		po.submit()

		pr = make_receipt(po.name)
		pr.items = [row for row in pr.items if row.purchase_order_item == po.items[0].name]
		pr.submit()
		make_invoice(pr.name).submit()

		tiles = supplier_overview.order_tiles(supplier, COMPANY, getdate(today()))
		self.assertEqual(tiles["receipt"]["value"], 900)
		self.assertEqual(tiles["receipt"]["orders"], [po.name])
		self.assertEqual(tiles["billing"]["value"], 0)
		self.assertEqual(tiles["billing"]["orders"], [])
		self.assertEqual(tiles["late"]["value"], 900)
		self.assertEqual(tiles["late"]["orders"], [po.name])

	def test_closed_line_leaves_billing(self):
		supplier = create_supplier(supplier_name="_Test Supplier Overview Closed").name
		po = create_purchase_order(supplier=supplier, rate=100, qty=1, do_not_submit=True)
		po.append(
			"items",
			{
				"item_code": "_Test Item 2",
				"qty": 1,
				"rate": 900,
				"warehouse": po.items[0].warehouse,
				"schedule_date": po.items[0].schedule_date,
			},
		)
		po.submit()

		pr = make_receipt(po.name)
		pr.items = [row for row in pr.items if row.purchase_order_item == po.items[0].name]
		pr.submit()
		update_closed_status("Purchase Order", po.name, [po.items[0].name], 1)

		tiles = supplier_overview.order_tiles(supplier, COMPANY, getdate(today()))
		self.assertEqual(tiles["billing"]["value"], 0)
		self.assertEqual(tiles["billing"]["orders"], [])
		self.assertEqual(tiles["receipt"]["value"], 900)
		self.assertEqual(tiles["receipt"]["orders"], [po.name])

	def test_extra_unit_after_due_date_keeps_line_on_time(self):
		supplier = create_supplier(supplier_name="_Test Supplier Overview Timing").name
		po = create_purchase_order(
			supplier=supplier, transaction_date=add_days(today(), -10), qty=10, do_not_submit=True
		)
		po.schedule_date = add_days(today(), -2)
		po.items[0].schedule_date = po.schedule_date
		po.submit()
		frappe.db.set_value("Item", po.items[0].item_code, "over_delivery_receipt_allowance", 50)

		for days_ago, qty in ((-5, 10), (0, 1)):
			pr = make_receipt(po.name)
			pr.set_posting_time = 1
			pr.posting_date = add_days(today(), days_ago)
			pr.items[0].qty = qty
			pr.items[0].received_qty = qty
			pr.submit()

		as_of = getdate(today())
		data = supplier_overview.delivery(supplier, COMPANY, add_days(as_of, -30), as_of, as_of)
		self.assertEqual((data["on_time"], data["late"]), (1, 0))

	def test_late_replacement_after_return_is_late(self):
		supplier = create_supplier(supplier_name="_Test Supplier Overview Return").name
		po = create_purchase_order(
			supplier=supplier, transaction_date=add_days(today(), -10), qty=10, do_not_submit=True
		)
		po.schedule_date = add_days(today(), -2)
		po.items[0].schedule_date = po.schedule_date
		po.submit()

		def receive(days_ago):
			pr = make_receipt(po.name)
			pr.set_posting_time = 1
			pr.posting_date = add_days(today(), days_ago)
			pr.submit()
			return pr

		first = receive(-5)
		returned = make_return_doc("Purchase Receipt", first.name)
		returned.set_posting_time = 1
		returned.posting_date = add_days(today(), -4)
		returned.submit()
		receive(0)

		as_of = getdate(today())
		data = supplier_overview.delivery(supplier, COMPANY, add_days(as_of, -30), as_of, as_of)
		self.assertEqual((data["on_time"], data["late"]), (0, 1))

	def test_received_line_without_receipt_is_not_counted(self):
		supplier = create_supplier(supplier_name="_Test Supplier Overview Drop Ship").name
		po = create_purchase_order(
			supplier=supplier, transaction_date=add_days(today(), -10), qty=5, do_not_submit=True
		)
		po.schedule_date = add_days(today(), -2)
		po.items[0].schedule_date = po.schedule_date
		po.submit()
		frappe.db.set_value("Purchase Order Item", po.items[0].name, "received_qty", 5)

		as_of = getdate(today())
		data = supplier_overview.delivery(supplier, COMPANY, add_days(as_of, -30), as_of, as_of)
		self.assertEqual(data["lines"], 0)

	def test_receipt_only_supplier_has_a_company(self):
		supplier = create_supplier(supplier_name="_Test Supplier Overview Receipt").name
		make_purchase_receipt(supplier=supplier)
		self.assertEqual(supplier_overview.get_supplier_companies(supplier), [COMPANY])

	def test_restricted_ledger_hides_advances(self):
		with patch.object(supplier_overview, "_unrestricted_read", return_value=False):
			data = supplier_overview.get_supplier_payables(SUPPLIER, COMPANY)
		self.assertIsNone(data["advances"]["value"])

	def test_company_outside_user_permissions_is_refused(self):
		with patch.object(
			frappe.permissions, "get_user_permissions", return_value={"Company": [{"doc": "_Test Company 1"}]}
		):
			self.assertRaises(
				frappe.PermissionError, supplier_overview.get_supplier_overview, SUPPLIER, COMPANY
			)
			self.assertRaises(
				frappe.PermissionError, supplier_overview.get_supplier_payables, SUPPLIER, COMPANY
			)
