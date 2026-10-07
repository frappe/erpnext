# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from erpnext.selling.report.sales_partner_commission_summary.test_sales_partner_commission_summary import (
	SalesPartnerSummaryReportTestMixin,
)
from erpnext.selling.report.sales_partner_transaction_summary.test_utils import (
	SalesPartnerTransactionSummaryAssertions,
)


class TestSalesPartnerTransactionSummary(
	SalesPartnerSummaryReportTestMixin, SalesPartnerTransactionSummaryAssertions
):
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

	def test_sales_invoice_sp_transaction_summary(self):
		self.filters["doctype"] = "Sales Invoice"
		self.create_transactions(self.filters["doctype"])

		self.assert_sales_partner_transaction_summary_report()
