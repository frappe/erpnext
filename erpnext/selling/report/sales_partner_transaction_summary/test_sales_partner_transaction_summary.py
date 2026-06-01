# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from frappe.desk.query_report import run

from erpnext.selling.report.sales_partner_commission_summary.test_sales_partner_commission_summary import (
	SalesPartnerSummaryReportTestMixin,
)


class TestSalesPartnerTransactionSummary(SalesPartnerSummaryReportTestMixin):
	def setUp(self):
		self.filters = {
			"company": "_Test Company",
			"doctype": "Sales Order",
			"from_date": "2026-01-01",
			"to_date": "2026-01-31",
			"show_return_entries": 1,
		}
		self.report_name = "Sales Partner Transaction Summary"

	def test_doctype_filters(self):
		self.assert_doctype_filters()

	def test_posting_date_column_label(self):
		self.assert_posting_date_label()

	def test_sales_order_sp_transaction_summary(self):
		self.filters["doctype"] = "Sales Order"
		self.create_transactions(self.filters["doctype"])

		self.assert_sales_partner_transaction_summary_report()

	def test_sales_invoice_sp_transaction_summary(self):
		self.filters["doctype"] = "Sales Invoice"
		self.create_transactions(self.filters["doctype"])

		self.assert_sales_partner_transaction_summary_report()

	def test_delivery_note_sp_transaction_summary(self):
		self.filters["doctype"] = "Delivery Note"
		self.create_transactions(self.filters["doctype"])

		self.assert_sales_partner_transaction_summary_report()

	def test_pos_invoice_sp_transaction_summary(self):
		self.filters["doctype"] = "POS Invoice"
		self.create_transactions(self.filters["doctype"])

		self.assert_sales_partner_transaction_summary_report()

	def assert_sales_partner_transaction_summary_report(self):
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
		self.assert_commission()

		if self.filters["doctype"] != "Sales Order":
			self.assert_returned_doc()

	def assert_7pc_commission(self):
		doc_name = self.seven_pc_doc.name

		row = next((row for row in self.report_result_without_total_row if row.get("name") == doc_name), None)

		self.assertIsNotNone(row)

		self.assertEqual(row["customer"], "_Test Customer")
		self.assertEqual(row["item_code"], "_Test Item")
		self.assertEqual(row["item_group"], "_Test Item Group")
		self.assertEqual(row["amount"], 1000)
		self.assertEqual(row["commission_rate"], 7)
		self.assertEqual(row["commission"], 70)

	def assert_5pc_commission_with_multiple_items(self):
		doc_name = self.five_pc_doc.name

		row1 = next(
			(
				row
				for row in self.report_result_without_total_row
				if row.get("name") == doc_name and row.get("item_code") == "_Test Item"
			),
			None,
		)
		self.assertIsNotNone(row1)

		row2 = next(
			(
				row
				for row in self.report_result_without_total_row
				if row.get("name") == doc_name and row.get("item_code") == "_Test Item 2"
			),
			None,
		)
		self.assertIsNotNone(row2)

		self.assertEqual(row1["amount"], 120)
		self.assertEqual(row1["commission_rate"], 5)
		self.assertEqual(row1["commission"], 6)

		self.assertEqual(row2["amount"], 120)
		self.assertEqual(row2["commission_rate"], 5)
		self.assertEqual(row2["commission"], 6)

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
		self.assertEqual(row["commission"], 0)

	def assert_doc_not_submitted(self):
		doc_name = self.doc_not_submitted.name

		row = next((row for row in self.report_result_without_total_row if row.get("name") == doc_name), None)

		self.assertIsNone(row)

	def assert_doc_cancelled(self):
		doc_name = self.cancelled_doc.name

		row = next((row for row in self.report_result_without_total_row if row.get("name") == doc_name), None)

		self.assertIsNone(row)

	def assert_commission(self):
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
		self.assertEqual(outward_row["commission"], 45)

		self.assertEqual(inward_row["amount"], -900)
		self.assertEqual(inward_row["commission"], -45)
