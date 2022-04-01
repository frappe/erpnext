# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from unittest import TestCase

import frappe

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.regional.doctype.gstr_3b_report.test_gstr_3b_report import (
	make_company as setup_company,
)
from erpnext.regional.doctype.gstr_3b_report.test_gstr_3b_report import (
	make_customers as setup_customers,
)
from erpnext.regional.doctype.gstr_3b_report.test_gstr_3b_report import (
	set_account_heads as setup_gst_settings,
)
from erpnext.regional.report.hsn_wise_summary_of_outward_supplies.hsn_wise_summary_of_outward_supplies import (
	execute as run_report,
)
from erpnext.stock.doctype.item.test_item import make_item


class TestHSNWiseSummaryReport(TestCase):
	@classmethod
	def setUpClass(cls):
		setup_company()
		setup_customers()
		setup_gst_settings()
		make_item("Golf Car", properties={"gst_hsn_code": "999900"})

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()

	def test_hsn_summary_for_invoice_with_duplicate_items(self):
		si = create_sales_invoice(
			company="_Test Company GST",
			customer="_Test GST Customer",
			currency="INR",
			warehouse="Finished Goods - _GST",
			debit_to="Debtors - _GST",
			income_account="Sales - _GST",
			expense_account="Cost of Goods Sold - _GST",
			cost_center="Main - _GST",
			do_not_save=1,
		)

		si.items = []
		si.append(
			"items",
			{
				"item_code": "Golf Car",
				"gst_hsn_code": "999900",
				"qty": "1",
				"rate": "120",
				"cost_center": "Main - _GST",
			},
		)
		si.append(
			"items",
			{
				"item_code": "Golf Car",
				"gst_hsn_code": "999900",
				"qty": "1",
				"rate": "140",
				"cost_center": "Main - _GST",
			},
		)
		si.append(
			"taxes",
			{
				"charge_type": "On Net Total",
				"account_head": "Output Tax IGST - _GST",
				"cost_center": "Main - _GST",
				"description": "IGST @ 18.0",
				"rate": 18,
			},
		)
		si.posting_date = "2020-11-17"
		si.submit()
		si.reload()

		[columns, data] = run_report(
			filters=frappe._dict(
				{
					"company": "_Test Company GST",
					"gst_hsn_code": "999900",
					"company_gstin": si.company_gstin,
					"from_date": si.posting_date,
					"to_date": si.posting_date,
				}
			)
		)

		filtered_rows = list(filter(lambda row: row["gst_hsn_code"] == "999900", data))
		self.assertTrue(filtered_rows)

		hsn_row = filtered_rows[0]
		self.assertEquals(hsn_row["stock_qty"], 2.0)
		self.assertEquals(hsn_row["total_amount"], 306.8)
