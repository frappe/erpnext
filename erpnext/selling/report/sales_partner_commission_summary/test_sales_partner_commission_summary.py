# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.desk.query_report import run
from frappe.utils.data import comma_or

from erpnext.selling.report.sales_partner_commission_summary.sales_partner_commission_summary import (
	SALES_TRANSACTION_DOCTYPES,
)
from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
from erpnext.tests.utils import ERPNextTestSuite


class SalesPartnerSummaryReportTestMixin(ERPNextTestSuite):
	def assert_doctype_filters(self):
		self.filters["doctype"] = "Purchase Invoice"

		with self.assertRaisesRegex(
			frappe.ValidationError,
			_("DocType can be one of them {0}").format(comma_or(SALES_TRANSACTION_DOCTYPES)),
		):
			run(self.report_name, self.filters)

	def assert_posting_date_label(self):
		data = run(self.report_name, self.filters)

		posting_date_column = next(
			(column for column in data.get("columns") if column.fieldname == "posting_date"), None
		)

		self.assertNotEqual(posting_date_column.get("label"), "Posting Date")
		self.assertEqual(posting_date_column.get("label"), "Order Date")

		self.filters["doctype"] = "Sales Invoice"

		data = run(self.report_name, self.filters)

		posting_date_column = next(
			(column for column in data.get("columns") if column.fieldname == "posting_date"), None
		)

		self.assertEqual(posting_date_column.get("label"), "Posting Date")
		self.assertNotEqual(posting_date_column.get("label"), "Order Date")

	def create_transactions(self, doctype):
		from erpnext.accounts.doctype.pos_invoice.test_pos_invoice import (
			POSInvoiceTestMixin,
			create_pos_invoice,
		)
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
		from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note

		make_transaction_funcs = {
			"Sales Order": make_sales_order,
			"Sales Invoice": create_sales_invoice,
			"Delivery Note": create_delivery_note,
			"POS Invoice": create_pos_invoice,
		}
		self.date_field = "transaction_date" if doctype == "Sales Order" else "posting_date"

		self.make_transaction_func = make_transaction_funcs[doctype]

		make_stock_entry(
			item_code="_Test Item 2",
			qty=10,
			company="_Test Company",
			to_warehouse="_Test Warehouse - _TC",
			purpose="Material Receipt",
			posting_date="2026-01-01",
		)

		if doctype == "POS Invoice":
			POSInvoiceTestMixin.setUp(self)

			from erpnext.accounts.doctype.pos_opening_entry.test_pos_opening_entry import create_opening_entry

			pos_opening_entry = create_opening_entry(self.pos_profile, self.test_user.name, get_obj=1)

		self.transaction_doc_with_7pc_commision()
		self.transaction_doc_with_5pc_commission()
		self.transaction_doc_with_no_sales_partner()
		self.transaction_doc_date_out_of_range_of_filters()
		self.transaction_doc_with_revoked_commission()
		self.transaction_doc_not_submitted()
		self.transaction_doc_cancelled()

		if doctype == "Sales Order":
			return

		self.transaction_doc_returned()

		if doctype == "POS Invoice":
			pos_opening_entry.cancel()

	def transaction_doc_with_7pc_commision(self):
		args = {"rate": 100, "qty": 10, self.date_field: "2026-01-14", "do_not_save": 1}
		self.seven_pc_doc = self.make_transaction_func(**args)
		self.seven_pc_doc.sales_partner = "_Test Sales Partner India - 1"
		if self.seven_pc_doc.doctype == "POS Invoice":
			self.seven_pc_doc.append("payments", {"mode_of_payment": "Cash", "amount": 1000, "default": 1})

		self.seven_pc_doc.save()
		self.seven_pc_doc.submit()

	def transaction_doc_with_5pc_commission(self):
		args = {"rate": 20, "qty": 6, self.date_field: "2026-01-15", "do_not_save": 1}
		self.five_pc_doc = self.make_transaction_func(**args)
		self.five_pc_doc.sales_partner = "_Test Sales Partner India - 2"

		self.five_pc_doc.append(
			"items",
			{
				"item_code": "_Test Item 2",
				"qty": 4,
				"rate": 30,
			},
		)

		if self.five_pc_doc.doctype == "POS Invoice":
			self.five_pc_doc.append("payments", {"mode_of_payment": "Cash", "amount": 500, "default": 1})

		self.five_pc_doc.save()
		self.five_pc_doc.submit()

	def transaction_doc_with_no_sales_partner(self):
		args = {
			"item_code": "_Test Item",
			"rate": 50,
			"qty": 10,
			self.date_field: "2026-01-19",
			"do_not_save": 1,
		}
		self.no_sp_doc = self.make_transaction_func(**args)
		if self.no_sp_doc.doctype == "POS Invoice":
			self.no_sp_doc.append("payments", {"mode_of_payment": "Cash", "amount": 500, "default": 1})

		self.no_sp_doc.save()
		self.no_sp_doc.submit()

	def transaction_doc_date_out_of_range_of_filters(self):
		args = {
			"item_code": "_Test Item",
			"rate": 60,
			"qty": 10,
			self.date_field: "2026-02-04",
			"do_not_save": 1,
		}
		self.date_out_of_range_doc = self.make_transaction_func(**args)
		self.date_out_of_range_doc.sales_partner = "_Test Sales Partner India - 1"
		if self.date_out_of_range_doc.doctype == "POS Invoice":
			self.date_out_of_range_doc.append(
				"payments", {"mode_of_payment": "Cash", "amount": 600, "default": 1}
			)

		self.date_out_of_range_doc.save()
		self.date_out_of_range_doc.submit()

	def transaction_doc_with_revoked_commission(self):
		try:
			frappe.db.set_value("Item", "_Test Item", "grant_commission", 0)
			args = {
				"item_code": "_Test Item",
				"rate": 80,
				"qty": 10,
				self.date_field: "2026-01-26",
				"do_not_save": 1,
			}
			self.revoked_comm_doc = self.make_transaction_func(**args)
			self.revoked_comm_doc.sales_partner = "_Test Sales Partner India - 1"

			if self.revoked_comm_doc.doctype == "POS Invoice":
				self.revoked_comm_doc.append(
					"payments", {"mode_of_payment": "Cash", "amount": 800, "default": 1}
				)

			self.revoked_comm_doc.save()
			self.revoked_comm_doc.submit()
		finally:
			frappe.db.set_value("Item", "_Test Item", "grant_commission", 1)

	def transaction_doc_not_submitted(self):
		args = {
			"item_code": "_Test Item",
			"rate": 80,
			"qty": 10,
			self.date_field: "2026-01-26",
			"do_not_save": 1,
		}
		self.doc_not_submitted = self.make_transaction_func(**args)
		self.doc_not_submitted.set(self.date_field, "2026-01-26")
		self.doc_not_submitted.sales_partner = "_Test Sales Partner India - 1"
		if self.doc_not_submitted.doctype == "POS Invoice":
			self.doc_not_submitted.append(
				"payments", {"mode_of_payment": "Cash", "amount": 800, "default": 1}
			)

		self.doc_not_submitted.save()

	def transaction_doc_cancelled(self):
		args = {
			"item_code": "_Test Item",
			"rate": 80,
			"qty": 10,
			self.date_field: "2026-01-26",
			"do_not_save": 1,
		}
		self.cancelled_doc = self.make_transaction_func(**args)
		self.cancelled_doc.sales_partner = "_Test Sales Partner India - 1"
		if self.cancelled_doc.doctype == "POS Invoice":
			self.cancelled_doc.append("payments", {"mode_of_payment": "Cash", "amount": 800, "default": 1})

		self.cancelled_doc.save()
		self.cancelled_doc.submit()
		self.cancelled_doc.cancel()

	def transaction_doc_returned(self):
		from erpnext.controllers.sales_and_purchase_return import make_return_doc

		args = {
			"item_code": "_Test Item",
			"rate": 90,
			"qty": 10,
			self.date_field: "2026-01-18",
			"do_not_save": 1,
		}
		self.to_be_returned_doc = self.make_transaction_func(**args)
		self.to_be_returned_doc.sales_partner = "_Test Sales Partner India - 2"
		if self.to_be_returned_doc.doctype == "POS Invoice":
			self.to_be_returned_doc.append(
				"payments", {"mode_of_payment": "Cash", "amount": 900, "default": 1}
			)

		self.to_be_returned_doc.save()
		self.to_be_returned_doc.submit()

		self.returned_doc = make_return_doc(self.to_be_returned_doc.doctype, self.to_be_returned_doc.name)
		self.returned_doc.posting_date = "2026-01-19"
		if self.returned_doc.doctype == "POS Invoice":
			self.returned_doc.payments = []
			self.returned_doc.append("payments", {"mode_of_payment": "Cash", "amount": -900, "default": 1})

		self.returned_doc.save()
		self.returned_doc.submit()


class TestSalesPartnerCommissionSummary(SalesPartnerSummaryReportTestMixin):
	def setUp(self):
		self.filters = {
			"company": "_Test Company",
			"doctype": "Sales Order",
			"from_date": "2026-01-01",
			"to_date": "2026-01-31",
		}
		self.report_name = "Sales Partner Commission Summary"

	def test_doctype_filters(self):
		self.assert_doctype_filters()

	def test_posting_date_column_label(self):
		self.assert_posting_date_label()

	def test_sales_order_sp_commission_summary(self):
		self.filters["doctype"] = "Sales Order"
		self.create_transactions(self.filters["doctype"])

		self.assert_sales_partner_commission_summary_report()

	def test_sales_invoice_sp_commission_summary(self):
		self.filters["doctype"] = "Sales Invoice"
		self.create_transactions(self.filters["doctype"])

		self.assert_sales_partner_commission_summary_report()

	def test_delivery_note_sp_commission_summary(self):
		self.filters["doctype"] = "Delivery Note"
		self.create_transactions(self.filters["doctype"])

		self.assert_sales_partner_commission_summary_report()

	def test_pos_invoice_sp_commission_summary(self):
		self.filters["doctype"] = "POS Invoice"
		self.create_transactions(self.filters["doctype"])

		self.assert_sales_partner_commission_summary_report()

	def assert_sales_partner_commission_summary_report(self):
		report_data = run(self.report_name, self.filters)

		self.report_result = report_data.get("result")
		self.report_result_without_total_row = self.report_result[:-1]

		self.assertIsNotNone(self.report_result_without_total_row)

		self.assert_7pc_commission()
		self.assert_5pc_commission_with_multiple_items()
		self.assert_doc_with_no_sp()
		self.assert_doc_with_posting_date_out_of_range()
		self.assert_doc_with_revoked_commission()
		self.assert_doc_not_submitted()
		self.assert_doc_cancelled()
		self.assert_total_commission()

		if self.filters["doctype"] != "Sales Order":
			self.assert_returned_doc()

	def assert_7pc_commission(self):
		doc_name = self.seven_pc_doc.name

		row = next((row for row in self.report_result_without_total_row if row.get("name") == doc_name), None)

		self.assertIsNotNone(row)
		self.assertEqual(row["amount"], 1000)
		self.assertEqual(row["commission_rate"], 7)
		self.assertEqual(row["total_commission"], 70)

	def assert_5pc_commission_with_multiple_items(self):
		doc_name = self.five_pc_doc.name

		row = next((row for row in self.report_result_without_total_row if row.get("name") == doc_name), None)

		self.assertIsNotNone(row)
		self.assertEqual(row["amount"], 240)
		self.assertEqual(row["commission_rate"], 5)
		self.assertEqual(row["total_commission"], 12)

	def assert_doc_with_no_sp(self):
		doc_name = self.no_sp_doc.name

		row = next((row for row in self.report_result_without_total_row if row.get("name") == doc_name), None)

		self.assertIsNone(row)

	def assert_doc_with_posting_date_out_of_range(self):
		doc_name = self.date_out_of_range_doc.name

		row = next((row for row in self.report_result_without_total_row if row.get("name") == doc_name), None)

		self.assertIsNone(row)

	def assert_doc_with_revoked_commission(self):
		doc_name = self.revoked_comm_doc.name

		row = next((row for row in self.report_result_without_total_row if row.get("name") == doc_name), None)

		self.assertIsNotNone(row)
		self.assertEqual(row["amount"], 800)
		self.assertEqual(row["commission_rate"], 7)
		self.assertEqual(row["total_commission"], 0)

	def assert_doc_not_submitted(self):
		doc_name = self.doc_not_submitted.name

		row = next((row for row in self.report_result_without_total_row if row.get("name") == doc_name), None)

		self.assertIsNone(row)

	def assert_doc_cancelled(self):
		doc_name = self.cancelled_doc.name

		row = next((row for row in self.report_result_without_total_row if row.get("name") == doc_name), None)

		self.assertIsNone(row)

	def assert_total_commission(self):
		total_row = self.report_result[-1]

		# Total Amount
		self.assertEqual(total_row[-4], 2040)

		# Total Commission
		self.assertEqual(total_row[-1], 82)

	def assert_returned_doc(self):
		doc_name = self.to_be_returned_doc.name
		returned_doc_name = self.returned_doc.name

		outward_row = next(
			(row for row in self.report_result_without_total_row if row.get("name") == doc_name), None
		)
		inward_row = next(
			(row for row in self.report_result_without_total_row if row.get("name") == returned_doc_name),
			None,
		)

		self.assertIsNotNone(outward_row)
		self.assertIsNotNone(inward_row)

		self.assertEqual(outward_row["amount"], 900)
		self.assertEqual(outward_row["total_commission"], 45)

		self.assertEqual(inward_row["amount"], -900)
		self.assertEqual(inward_row["total_commission"], -45)
