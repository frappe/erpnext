# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from frappe.desk.query_report import run


class SalesPartnerTransactionSummaryAssertions:
	def assert_sales_partner_transaction_summary_report(self):
		filters = self.filters.copy()
		filters["show_return_entries"] = 1
		report_data = run("Sales Partner Transaction Summary", filters)

		self.transaction_report_result = report_data.get("result")
		self.transaction_report_result_without_total_row = self.transaction_report_result[:-1]

		self.assertIsNotNone(self.transaction_report_result_without_total_row)

		self.assert_transaction_7pc_commission()
		self.assert_transaction_5pc_commission_with_multiple_items()
		self.assert_transaction_doc_with_no_sp()
		self.assert_transaction_doc_with_posting_date_out_of_range()
		self.assert_transaction_doc_with_revoked_commission()
		self.assert_transaction_doc_not_submitted()
		self.assert_transaction_doc_cancelled()
		self.assert_transaction_commission()

		if self.filters["doctype"] != "Sales Order":
			self.assert_transaction_returned_doc()

	def assert_transaction_7pc_commission(self):
		row = self._get_transaction_report_row(self.seven_pc_doc.name)

		self.assertIsNotNone(row)
		self.assertEqual(row["customer"], "_Test Customer")
		self.assertEqual(row["item_code"], "_Test Item")
		self.assertEqual(row["item_group"], "_Test Item Group")
		self.assertEqual(row["amount"], 1000)
		self.assertEqual(row["commission_rate"], 7)
		self.assertEqual(row["commission"], 70)

	def assert_transaction_5pc_commission_with_multiple_items(self):
		row1 = self._get_transaction_report_row(self.five_pc_doc.name, "_Test Item")
		self.assertIsNotNone(row1)

		row2 = self._get_transaction_report_row(self.five_pc_doc.name, "_Test Item 2")
		self.assertIsNotNone(row2)

		self.assertEqual(row1["amount"], 120)
		self.assertEqual(row1["commission_rate"], 5)
		self.assertEqual(row1["commission"], 6)

		self.assertEqual(row2["amount"], 120)
		self.assertEqual(row2["commission_rate"], 5)
		self.assertEqual(row2["commission"], 6)

	def assert_transaction_doc_with_no_sp(self):
		row = self._get_transaction_report_row(self.no_sp_doc.name)
		self.assertIsNone(row)

	def assert_transaction_doc_with_posting_date_out_of_range(self):
		row = self._get_transaction_report_row(self.date_out_of_range_doc.name)
		self.assertIsNone(row)

	def assert_transaction_doc_with_revoked_commission(self):
		row = self._get_transaction_report_row(self.revoked_comm_doc.name)

		self.assertIsNotNone(row)
		self.assertEqual(row["amount"], 800)
		self.assertEqual(row["commission_rate"], 7)
		self.assertEqual(row["commission"], 0)

	def assert_transaction_doc_not_submitted(self):
		row = self._get_transaction_report_row(self.doc_not_submitted.name)
		self.assertIsNone(row)

	def assert_transaction_doc_cancelled(self):
		row = self._get_transaction_report_row(self.cancelled_doc.name)
		self.assertIsNone(row)

	def assert_transaction_commission(self):
		total_row = self.transaction_report_result[-1]

		self.assertEqual(total_row[-4], 2040)
		self.assertEqual(total_row[-1], 82)

	def assert_transaction_returned_doc(self):
		outward_row = self._get_transaction_report_row(self.to_be_returned_doc.name)
		inward_row = self._get_transaction_report_row(self.returned_doc.name)

		self.assertIsNotNone(outward_row)
		self.assertIsNotNone(inward_row)
		self.assertEqual(outward_row["amount"], 900)
		self.assertEqual(outward_row["commission"], 45)
		self.assertEqual(inward_row["amount"], -900)
		self.assertEqual(inward_row["commission"], -45)

	def _get_transaction_report_row(self, doc_name, item_code=None):
		return next(
			(
				row
				for row in self.transaction_report_result_without_total_row
				if row.get("name") == doc_name and (not item_code or row.get("item_code") == item_code)
			),
			None,
		)
