# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

import frappe
from frappe.utils import add_to_date, today

from erpnext.accounts.doctype.tax_withholding_category.test_tax_withholding_category import (
	create_purchase_invoice,
	create_records,
)
from erpnext.accounts.report.tax_withholding_details.test_tax_withholding_details import (
	create_tax_category,
)
from erpnext.accounts.report.tds_computation_summary.tds_computation_summary import execute
from erpnext.accounts.utils import get_fiscal_year
from erpnext.tests.utils import ERPNextTestSuite


class TestTDSComputationSummary(ERPNextTestSuite):
	def setUp(self):
		create_records()

	def test_amounts_at_different_rates_get_separate_rows(self):
		fiscal_year = get_fiscal_year(today(), company="_Test Company")
		mid_year = add_to_date(fiscal_year[1], months=6)
		self.create_category_with_rate_change(mid_year)

		for posting_date in (add_to_date(fiscal_year[1], days=1), add_to_date(mid_year, days=1)):
			invoice = create_purchase_invoice(
				supplier="Test TDS Supplier", rate=5000, posting_date=posting_date, set_posting_time=True
			)
			invoice.submit()

		rows = execute(
			frappe._dict(
				company="_Test Company",
				party_type="Supplier",
				from_date=fiscal_year[1],
				to_date=fiscal_year[2],
			)
		)[1]

		self.assertEqual(
			sorted((row["rate"], row["total_amount"], row["tax_amount"]) for row in rows),
			[(10.0, 5000.0, 500.0), (20.0, 5000.0, 1000.0)],
		)

	def create_category_with_rate_change(self, mid_year):
		create_tax_category("TDS - Summary", rate=10, account="TDS - _TC", cumulative_threshold=1)
		category = frappe.get_doc("Tax Withholding Category", "TDS - Summary")
		category.rates[0].to_date = mid_year
		category.append(
			"rates",
			{
				"tax_withholding_rate": 20,
				"from_date": add_to_date(mid_year, days=1),
				"to_date": get_fiscal_year(today(), company="_Test Company")[2],
				"single_threshold": 1,
				"cumulative_threshold": 1,
			},
		)
		category.save()
		frappe.db.set_value("Supplier", "Test TDS Supplier", "tax_withholding_category", category.name)
