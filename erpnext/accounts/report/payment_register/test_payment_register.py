# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import add_days, nowdate

from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.report.payment_register.payment_register import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestPaymentRegister(ERPNextTestSuite):
	def setUp(self):
		self.company = "_Test Company"
		self.cost_center = "_Test Cost Center - _TC"
		self.filters = frappe._dict(
			{
				"company": self.company,
				"from_date": add_days(nowdate(), -30),
				"to_date": nowdate(),
			}
		)

	def rows_for_voucher(self, data, voucher_no):
		return [row for row in data if row.voucher_no == voucher_no]

	def test_payment_entry_pay_and_receive(self):
		si = create_sales_invoice(company=self.company)
		receive_pe = get_payment_entry(si.doctype, si.name, bank_account="_Test Bank - _TC")
		receive_pe.reference_no = "REC-001"
		receive_pe.reference_date = nowdate()
		receive_pe.insert()
		receive_pe.submit()

		pi = make_purchase_invoice(company=self.company)
		pay_pe = get_payment_entry(pi.doctype, pi.name, bank_account="_Test Bank - _TC")
		pay_pe.reference_no = "PAY-001"
		pay_pe.reference_date = nowdate()
		pay_pe.insert()
		pay_pe.submit()

		columns, data = execute(self.filters)

		receive_rows = self.rows_for_voucher(data, receive_pe.name)
		self.assertEqual(len(receive_rows), 1)
		self.assertEqual(receive_rows[0].direction, "Receive")
		self.assertEqual(receive_rows[0].voucher_subtype, "Receive")
		self.assertEqual(receive_rows[0].account, "_Test Bank - _TC")
		self.assertEqual(receive_rows[0].amount, receive_pe.paid_amount)
		self.assertEqual(receive_rows[0].reference_no, "REC-001")

		pay_rows = self.rows_for_voucher(data, pay_pe.name)
		self.assertEqual(len(pay_rows), 1)
		self.assertEqual(pay_rows[0].direction, "Pay")
		self.assertEqual(pay_rows[0].voucher_subtype, "Pay")
		self.assertEqual(pay_rows[0].account, "_Test Bank - _TC")
		self.assertEqual(pay_rows[0].amount, pay_pe.paid_amount)

	def test_internal_transfer_surfaces_two_rows(self):
		pe = frappe.get_doc(
			{
				"doctype": "Payment Entry",
				"payment_type": "Internal Transfer",
				"company": self.company,
				"posting_date": nowdate(),
				"paid_from": "_Test Bank - _TC",
				"paid_to": "_Test Cash - _TC",
				"paid_amount": 500,
				"received_amount": 500,
				"reference_no": "IT-001",
				"reference_date": nowdate(),
			}
		)
		pe.insert()
		pe.submit()

		columns, data = execute(self.filters)
		rows = self.rows_for_voucher(data, pe.name)

		self.assertEqual(len(rows), 2)
		by_account = {row.account: row for row in rows}
		self.assertEqual(by_account["_Test Bank - _TC"].direction, "Pay")
		self.assertEqual(by_account["_Test Cash - _TC"].direction, "Receive")
		for row in rows:
			self.assertEqual(row.amount, 500)
			self.assertEqual(row.voucher_subtype, "Internal Transfer")

	def test_bank_entry_journal_entry_surfaces_one_row(self):
		je = make_journal_entry(
			"_Test Bank - _TC",
			"_Test Account Sales - _TC",
			400,
			cost_center=self.cost_center,
			submit=False,
		)
		je.voucher_type = "Bank Entry"
		je.cheque_no = "BE-001"
		je.cheque_date = nowdate()
		je.submit()

		columns, data = execute(self.filters)
		rows = self.rows_for_voucher(data, je.name)

		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].account, "_Test Bank - _TC")
		self.assertEqual(rows[0].direction, "Receive")
		self.assertEqual(rows[0].voucher_subtype, "Bank Entry")
		self.assertEqual(rows[0].amount, 400)

	def test_contra_entry_journal_entry_surfaces_two_rows(self):
		je = make_journal_entry(
			"_Test Cash - _TC",
			"_Test Bank - _TC",
			300,
			cost_center=self.cost_center,
			submit=False,
		)
		je.voucher_type = "Contra Entry"
		je.submit()

		columns, data = execute(self.filters)
		rows = self.rows_for_voucher(data, je.name)

		self.assertEqual(len(rows), 2)
		by_account = {row.account: row for row in rows}
		self.assertEqual(by_account["_Test Cash - _TC"].direction, "Receive")
		self.assertEqual(by_account["_Test Bank - _TC"].direction, "Pay")

	def test_plain_journal_entry_gated_by_account_type_not_voucher_type(self):
		non_bank_je = make_journal_entry(
			"_Test Account Sales - _TC",
			"_Test Account Cost for Goods Sold - _TC",
			200,
			cost_center=self.cost_center,
			submit=True,
		)
		columns, data = execute(self.filters)
		self.assertEqual(self.rows_for_voucher(data, non_bank_je.name), [])

		bank_interest_je = make_journal_entry(
			"_Test Bank - _TC",
			"_Test Account Sales - _TC",
			150,
			cost_center=self.cost_center,
			submit=True,
		)
		columns, data = execute(self.filters)
		rows = self.rows_for_voucher(data, bank_interest_je.name)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].account, "_Test Bank - _TC")
		self.assertEqual(rows[0].voucher_subtype, "Journal Entry")

	def test_purchase_invoice_instant_payment_surfaces_with_blank_reference(self):
		pi = make_purchase_invoice(
			company=self.company,
			is_paid=1,
			cash_bank_account="_Test Cash - _TC",
		)

		columns, data = execute(self.filters)
		rows = self.rows_for_voucher(data, pi.name)

		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].account, "_Test Cash - _TC")
		self.assertEqual(rows[0].voucher_type, "Purchase Invoice")
		self.assertFalse(rows[0].mode_of_payment)
		self.assertFalse(rows[0].reference_no)

	def test_cancelled_and_opening_entries_excluded(self):
		je = make_journal_entry(
			"_Test Bank - _TC",
			"_Test Account Sales - _TC",
			175,
			cost_center=self.cost_center,
			submit=True,
		)
		voucher_no = je.name
		je.cancel()

		columns, data = execute(self.filters)
		self.assertEqual(self.rows_for_voucher(data, voucher_no), [])

		opening_je = frappe.get_doc(
			{
				"doctype": "Journal Entry",
				"voucher_type": "Opening Entry",
				"company": self.company,
				"posting_date": nowdate(),
				"is_opening": "Yes",
				"accounts": [
					{
						"account": "_Test Bank - _TC",
						"debit_in_account_currency": 100,
						"cost_center": self.cost_center,
					},
					{
						"account": "_Test Cash - _TC",
						"credit_in_account_currency": 100,
						"cost_center": self.cost_center,
					},
				],
			}
		)
		opening_je.insert()
		opening_je.submit()

		columns, data = execute(self.filters)
		self.assertEqual(self.rows_for_voucher(data, opening_je.name), [])

	def test_filters_narrow_results(self):
		si = create_sales_invoice(company=self.company, customer="_Test Customer")
		pe = get_payment_entry(si.doctype, si.name, bank_account="_Test Bank - _TC")
		pe.reference_no = "FILT-001"
		pe.reference_date = nowdate()
		pe.insert()
		pe.submit()

		base_filters = frappe._dict(self.filters.copy())

		filters = base_filters.copy()
		filters["party_type"] = "Customer"
		filters["party"] = ["_Test Customer"]
		columns, data = execute(filters)
		self.assertTrue(self.rows_for_voucher(data, pe.name))

		filters = base_filters.copy()
		filters["party"] = ["_Test Customer 1"]
		columns, data = execute(filters)
		self.assertEqual(self.rows_for_voucher(data, pe.name), [])

		filters = base_filters.copy()
		filters["account"] = ["_Test Cash - _TC"]
		columns, data = execute(filters)
		self.assertEqual(self.rows_for_voucher(data, pe.name), [])

		filters = base_filters.copy()
		filters["voucher_type"] = ["Journal Entry"]
		columns, data = execute(filters)
		self.assertEqual(self.rows_for_voucher(data, pe.name), [])

		filters = base_filters.copy()
		filters["reference_no"] = "FILT-001"
		columns, data = execute(filters)
		self.assertTrue(self.rows_for_voucher(data, pe.name))

		filters = base_filters.copy()
		filters["reference_no"] = "NO-SUCH-REF"
		columns, data = execute(filters)
		self.assertEqual(self.rows_for_voucher(data, pe.name), [])

		filters = base_filters.copy()
		filters["cost_center"] = "_Test Cost Center 2 - _TC"
		columns, data = execute(filters)
		self.assertEqual(self.rows_for_voucher(data, pe.name), [])

	def test_date_range_excludes_out_of_range_postings(self):
		je = make_journal_entry(
			"_Test Bank - _TC",
			"_Test Account Sales - _TC",
			250,
			cost_center=self.cost_center,
			posting_date=add_days(nowdate(), -90),
			submit=True,
		)

		columns, data = execute(self.filters)
		self.assertEqual(self.rows_for_voucher(data, je.name), [])

		wide_filters = frappe._dict(self.filters.copy())
		wide_filters["from_date"] = add_days(nowdate(), -120)
		columns, data = execute(wide_filters)
		self.assertTrue(self.rows_for_voucher(data, je.name))

	def test_multi_currency_payment_entry(self):
		si = create_sales_invoice(
			company=self.company,
			customer="_Test Customer USD",
			currency="USD",
			conversion_rate=50,
			debit_to="_Test Receivable USD - _TC",
			do_not_submit=True,
		)
		si.submit()

		pe = get_payment_entry(si.doctype, si.name, bank_account="_Test Bank USD - _TC")
		pe.source_exchange_rate = 50
		pe.target_exchange_rate = 50
		pe.reference_no = "MC-001"
		pe.reference_date = nowdate()
		pe.insert()
		pe.submit()

		columns, data = execute(self.filters)
		rows = self.rows_for_voucher(data, pe.name)

		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].account_currency, "USD")
		self.assertEqual(rows[0].amount, pe.paid_amount)
		self.assertEqual(rows[0].amount_in_company_currency, pe.base_paid_amount)
