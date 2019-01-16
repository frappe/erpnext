# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from __future__ import unicode_literals
import frappe
import json
import os
import unittest
import datetime

test_records = frappe.get_test_records('Report')


class TestReport(unittest.TestCase):
    def test_Permitted_Documents_For_User(self):
        report = frappe.get_doc('Report', 'Permitted Documents For User')
        columns, data = report.get_data(
            filters={'user': 'test@example.com', 'doctype': 'DocType'})
        self.assertEqual(report.report_type, 'Script Report')
        self.assertTrue(('DocType', 'Core') in [d for d in data])

    def test_address_and_contacts(self):
        report = frappe.get_doc('Report', 'Address And Contacts')
        columns, data = report.get_data(
            filters={'party_type': 'Supplier', 'party_name': '_Test Supplier'})
        self.assertEqual(report.report_type, 'Script Report')
        self.assertEqual(data[0], ['_Test Supplier', '_Test Supplier Group',
                                   '', '', '', '', '', '', '', '', '', '', '', '', ''])
        self.assertEqual(len(data), 1)

    def test_balance_sheet(self):
        report = frappe.get_doc('Report', 'Balance Sheet')
        columns, data = report.get_data(
            filters={'company': '_Test Company', 'from_fiscal_year': frappe.get_doc('Fiscal Year', '_Test Fiscal Year 2013').year, 'to_fiscal_year':   frappe.get_doc('Fiscal Year', '_Test Fiscal Year 2013').year, 'periodicity': 'Yearly'})
        self.assertEqual(report.report_type, 'Script Report')
        self.assertRow(data, 0, 'Application of Funds (Assets)', 'INR')
        self.assertRow(data, 1, 'Current Assets', 'INR', -1900.0)
        self.assertRow(data, 2, '_Test Receivable', 'INR', -3600.0)
        self.assertRow(data, 3, 'Bank Accounts', 'INR',  1700.0)
        self.assertRow(data, 4, '_Test Bank', 'INR', 1700.0)
        self.assertRow(data, 5, r"'Total Asset (Debit)'", 'INR', -1900.0)
        self.assertRow(data, 7, 'Source of Funds (Liabilities)', 'INR')
        self.assertRow(data, 8, 'Current Liabilities', 'INR', -1600.0)
        self.assertRow(data, 9, '_Test Payable', 'INR', -1600.0)
        self.assertRow(data, 10, r"'Total Liability (Credit)'", 'INR', -1600.0)
        self.assertRow(
            data, 12, r"'Provisional Profit / Loss (Credit)'", 'INR', -300.0)
        self.assertRow(data, 13, r"'Total (Credit)'", 'INR', -1900.0)
        self.assertEqual(len(data), 14)

    def assertRow(self, data, index, account_name, currency=None, amount=None):
        self.assertEqual(data[index]['account_name'], account_name)
        if currency is not None:
            self.assertEqual(data[index]['currency'], currency)
        if amount is not None:
            self.assertEqual(data[index]['total'], amount)

    def test_profit_and_loss_statement(self):
        report = frappe.get_doc('Report', 'Profit and Loss Statement')
        columns, data = report.get_data(
            filters={'company': '_Test Company', 'from_fiscal_year': frappe.get_doc('Fiscal Year', '_Test Fiscal Year 2013').year, 'to_fiscal_year':   frappe.get_doc('Fiscal Year', '_Test Fiscal Year 2013').year, 'periodicity': 'Yearly'})
        self.assertEqual(report.report_type, 'Script Report')
        self.assertRow(data, 0, 'Expenses', 'INR')
        self.assertRow(
            data, 1, '_Test Account Cost for Goods Sold', 'INR', 300.03)
        self.assertRow(data, 2, r"'Total Expense (Debit)'", 'INR', 300.03)
        self.assertRow(data, 4, r"'Profit for the year'", 'INR', -300.03)
        self.assertEqual(len(data), 5)

    def test_cash_flow(self):
        report = frappe.get_doc('Report', 'Cash Flow')
        columns, data = report.get_data(
            filters={'company': '_Test Company', 'from_fiscal_year': frappe.get_doc('Fiscal Year', '_Test Fiscal Year 2013').year, 'to_fiscal_year':   frappe.get_doc('Fiscal Year', '_Test Fiscal Year 2013').year, 'periodicity': 'Yearly'})
        self.assertEqual(report.report_type, 'Script Report')
        self.assertRow(data, 0, 'Cash Flow from Operations')
        self.assertRow(data, 1, r"'Profit for the year'", 'INR', -300.03)
        self.assertRow(data, 2, 'Depreciation', 'INR', None)
        self.assertRow(
            data, 3, 'Net Change in Accounts Receivable', 'INR', 3600.00)
        self.assertRow(
            data, 4, 'Net Change in Accounts Payable', 'INR', -1600.00)
        self.assertRow(data, 5, 'Net Change in Inventory', 'INR')
        self.assertRow(data, 6, r"'Net Cash from Operations'",
                       'INR', 1699.9700000000003)
        self.assertRow(data, 8, 'Cash Flow from Investing')
        self.assertRow(data, 9, 'Net Change in Fixed Asset', 'INR')
        self.assertRow(data, 10, r"'Net Cash from Investing'", 'INR')
        self.assertRow(data, 12, 'Cash Flow from Financing')
        self.assertRow(data, 13, 'Net Change in Equity', 'INR')
        self.assertRow(data, 14, r"'Net Cash from Financing'", 'INR')
        self.assertRow(data, 16, r"'Net Change in Cash'",
                       'INR', 1699.9700000000003)
        self.assertEqual(len(data), 18)

    def test_general_ledger(self):
        report = frappe.get_doc('Report', 'General Ledger')
        columns, data = report.get_data(filters={'company': '_Test Company', 'from_date': datetime.date(
            2013, 1, 1), 'to_date': datetime.date(2013, 12, 31)})
        self.assertEqual(report.report_type, 'Script Report')
        self.assertEqual(data[0]['account'], r"'Opening'")
        self.assertEqual(data[1], {u'balance': 100.01, u'party': None, u'account': u'_Test Account Cost for Goods Sold - _TC', u'credit_in_account_currency': 0.0, u'against_voucher': None, u'party_type': None, u'is_opening': u'No', u'voucher_type': u'Journal Entry', u'against': u'_Test Bank - _TC',
                                   u'against_voucher_type': None, u'project': None, u'credit': 0.0, u'debit': 100.01, u'remarks': u'Note: test', u'posting_date': datetime.date(2013, 2, 14), u'voucher_no': u'ACC-JV-2018-00001', u'debit_in_account_currency': 100.0, u'cost_center': u'_Test Cost Center - _TC', u'account_currency': None, u'bill_no': u''})
        self.assertEqual(data[2],
                         {u'balance': 200.02, u'party': None, u'account': u'_Test Account Cost for Goods Sold - _TC', u'credit_in_account_currency': 0.0, u'against_voucher': None, u'party_type': None, u'is_opening': u'No', u'voucher_type': u'Journal Entry', u'against': u'_Test Bank - _TC', u'against_voucher_type': None, u'project': None, u'credit': 0.0, u'debit': 100.01, u'remarks': u'Note: test', u'posting_date': datetime.date(2013, 2, 14), u'voucher_no': u'ACC-JV-2018-00002', u'debit_in_account_currency': 100.0, u'cost_center': u'_Test Cost Center - _TC', u'account_currency': None, u'bill_no': u''})
        self.assertEqual(data[3], {u'balance': 300.03000000000003, u'party': None, u'account': u'_Test Account Cost for Goods Sold - _TC', u'credit_in_account_currency': 0.0, u'against_voucher': None, u'party_type': None, u'is_opening': u'No', u'voucher_type': u'Journal Entry', u'against': u'_Test Bank - _TC',
                                   u'against_voucher_type': None, u'project': None, u'credit': 0.0, u'debit': 100.01, u'remarks': u'Note: test', u'posting_date': datetime.date(2013, 2, 14), u'voucher_no': u'ACC-JV-2018-00003', u'debit_in_account_currency': 100.0, u'cost_center': u'_Test Cost Center - _TC', u'account_currency': None, u'bill_no': u''})
        self.assertEqual(data[4], {u'balance': 200.03000000000003, u'party': None, u'account': u'_Test Bank - _TC', u'credit_in_account_currency': 100.0, u'against_voucher': None, u'party_type': None, u'is_opening': u'No', u'voucher_type': u'Journal Entry', u'against': u'_Test Account Cost for Goods Sold - _TC',
                                   u'against_voucher_type': None, u'project': None, u'credit': 100.0, u'debit': 0.0, u'remarks': u'Note: test', u'posting_date': datetime.date(2013, 2, 14), u'voucher_no': u'ACC-JV-2018-00001', u'debit_in_account_currency': 0.0, u'cost_center': None, u'account_currency': None, u'bill_no': u''})
        self.assertEqual(data[5], {u'balance': 100.03000000000003, u'party': None, u'account': u'_Test Bank - _TC', u'credit_in_account_currency': 100.0, u'against_voucher': None, u'party_type': None, u'is_opening': u'No', u'voucher_type': u'Journal Entry', u'against': u'_Test Account Cost for Goods Sold - _TC',
                                   u'against_voucher_type': None, u'project': None, u'credit': 100.0, u'debit': 0.0, u'remarks': u'Note: test', u'posting_date': datetime.date(2013, 2, 14), u'voucher_no': u'ACC-JV-2018-00002', u'debit_in_account_currency': 0.0, u'cost_center': None, u'account_currency': None, u'bill_no': u''})
        self.assertEqual(data[6], {u'balance': 0.03000000000002956, u'party': None, u'account': u'_Test Bank - _TC', u'credit_in_account_currency': 100.0, u'against_voucher': None, u'party_type': None, u'is_opening': u'No', u'voucher_type': u'Journal Entry', u'against': u'_Test Account Cost for Goods Sold - _TC',
                                   u'against_voucher_type': None, u'project': None, u'credit': 100.0, u'debit': 0.0, u'remarks': u'Note: test', u'posting_date': datetime.date(2013, 2, 14), u'voucher_no': u'ACC-JV-2018-00003', u'debit_in_account_currency': 0.0, u'cost_center': None, u'account_currency': None, u'bill_no': u''})
        self.assertEqual(data[7], {u'balance': 400.03000000000003, u'party': None, u'account': u'_Test Bank - _TC', u'credit_in_account_currency': 0.0, u'against_voucher': None, u'party_type': None, u'is_opening': u'No', u'voucher_type': u'Journal Entry', u'against': u'_Test Customer', u'against_voucher_type': None,
                                   u'project': None, u'credit': 0.0, u'debit': 400.0, u'remarks': u'Note: test\nReference #33 dated 03-14-2013', u'posting_date': datetime.date(2013, 2, 14), u'voucher_no': u'_T-Journal Entry-00005', u'debit_in_account_currency': 400.0, u'cost_center': None, u'account_currency': None, u'bill_no': u''})
        self.assertEqual(data[8], {u'balance': 0.03000000000002956, u'party': None, u'account': u'_Test Bank - _TC', u'credit_in_account_currency': 400.0, u'against_voucher': None, u'party_type': None, u'is_opening': u'No', u'voucher_type': u'Journal Entry', u'against': u'_Test Supplier', u'against_voucher_type': None, u'project': None,
                                   u'credit': 400.0, u'debit': 0.0, u'remarks': u'Note: test\nReference #33 dated 02-14-2013\n\u20b9 0.00 against Purchase Order PUR-ORD-2018-00001', u'posting_date': datetime.date(2013, 2, 14), u'voucher_no': u'_T-Journal Entry-00006', u'debit_in_account_currency': 0.0, u'cost_center': None, u'account_currency': None, u'bill_no': u''})
        self.assertEqual(data[9], {u'balance': 400.03000000000003, u'party': None, u'account': u'_Test Bank - _TC', u'credit_in_account_currency': 0.0, u'against_voucher': None, u'party_type': None, u'is_opening': u'No', u'voucher_type': u'Journal Entry', u'against': u'_Test Customer', u'against_voucher_type': None, u'project': None,
                                   u'credit': 0.0, u'debit': 400.0, u'remarks': u'Note: test\nReference #33 dated 03-14-2013\n\u20b9 400.00 against Sales Order SAL-ORD-2018-00001', u'posting_date': datetime.date(2013, 2, 14), u'voucher_no': u'_T-Journal Entry-00007', u'debit_in_account_currency': 400.0, u'cost_center': None, u'account_currency': None, u'bill_no': u''})
        self.assertEqual(data[10], {u'balance': 800.03, u'party': None, u'account': u'_Test Bank - _TC', u'credit_in_account_currency': 0.0, u'against_voucher': None, u'party_type': None, u'is_opening': u'No', u'voucher_type': u'Journal Entry', u'against': u'_Test Customer', u'against_voucher_type': None,
                                    u'project': None, u'credit': 0.0, u'debit': 400.0, u'remarks': u'Note: test\nReference #33 dated 03-14-2013', u'posting_date': datetime.date(2013, 2, 14), u'voucher_no': u'_T-Journal Entry-00010', u'debit_in_account_currency': 400.0, u'cost_center': None, u'account_currency': None, u'bill_no': u''})
        self.assertEqual(data[11], {u'balance': 400.03, u'party': None, u'account': u'_Test Bank - _TC', u'credit_in_account_currency': 400.0, u'against_voucher': None, u'party_type': None, u'is_opening': u'No', u'voucher_type': u'Journal Entry', u'against': u'_Test Supplier', u'against_voucher_type': None, u'project': None, u'credit': 400.0,
                                    u'debit': 0.0, u'remarks': u'Note: test\nReference #33 dated 02-14-2013\n\u20b9 0.00 against Purchase Order PUR-ORD-2018-00002', u'posting_date': datetime.date(2013, 2, 14), u'voucher_no': u'_T-Journal Entry-00011', u'debit_in_account_currency': 0.0, u'cost_center': None, u'account_currency': None, u'bill_no': u''})
        self.assertEqual(data[12], {u'balance': 800.03, u'party': None, u'account': u'_Test Bank - _TC', u'credit_in_account_currency': 0.0, u'against_voucher': None, u'party_type': None, u'is_opening': u'No', u'voucher_type': u'Journal Entry', u'against': u'_Test Customer', u'against_voucher_type': None, u'project': None, u'credit': 0.0,
                                    u'debit': 400.0, u'remarks': u'Note: test\nReference #33 dated 03-14-2013\n\u20b9 400.00 against Sales Order SAL-ORD-2018-00002', u'posting_date': datetime.date(2013, 2, 14), u'voucher_no': u'_T-Journal Entry-00012', u'debit_in_account_currency': 400.0, u'cost_center': None, u'account_currency': None, u'bill_no': u''})
        self.assertEqual(data[13], {u'balance': 1200.03, u'party': None, u'account': u'_Test Bank - _TC', u'credit_in_account_currency': 0.0, u'against_voucher': None, u'party_type': None, u'is_opening': u'No', u'voucher_type': u'Journal Entry', u'against': u'_Test Customer', u'against_voucher_type': None,
                                    u'project': None, u'credit': 0.0, u'debit': 400.0, u'remarks': u'Note: test\nReference #33 dated 03-14-2013', u'posting_date': datetime.date(2013, 2, 14), u'voucher_no': u'_T-Journal Entry-00015', u'debit_in_account_currency': 400.0, u'cost_center': None, u'account_currency': None, u'bill_no': u''})
        self.assertEqual(data[14], {u'balance': 800.03, u'party': None, u'account': u'_Test Bank - _TC', u'credit_in_account_currency': 400.0, u'against_voucher': None, u'party_type': None, u'is_opening': u'No', u'voucher_type': u'Journal Entry', u'against': u'_Test Supplier', u'against_voucher_type': None, u'project': None, u'credit': 400.0,
                                    u'debit': 0.0, u'remarks': u'Note: test\nReference #33 dated 02-14-2013\n\u20b9 0.00 against Purchase Order PUR-ORD-2018-00003', u'posting_date': datetime.date(2013, 2, 14), u'voucher_no': u'_T-Journal Entry-00016', u'debit_in_account_currency': 0.0, u'cost_center': None, u'account_currency': None, u'bill_no': u''})
        self.assertEqual(data[15], {u'balance': 1200.03, u'party': None, u'account': u'_Test Bank - _TC', u'credit_in_account_currency': 0.0, u'against_voucher': None, u'party_type': None, u'is_opening': u'No', u'voucher_type': u'Journal Entry', u'against': u'_Test Customer', u'against_voucher_type': None, u'project': None, u'credit': 0.0,
                                    u'debit': 400.0, u'remarks': u'Note: test\nReference #33 dated 03-14-2013\n\u20b9 400.00 against Sales Order SAL-ORD-2018-00003', u'posting_date': datetime.date(2013, 2, 14), u'voucher_no': u'_T-Journal Entry-00017', u'debit_in_account_currency': 400.0, u'cost_center': None, u'account_currency': None, u'bill_no': u''})
        self.assertEqual(data[16], {u'balance': 1600.03, u'party': None, u'account': u'_Test Bank - _TC', u'credit_in_account_currency': 0.0, u'against_voucher': None, u'party_type': None, u'is_opening': u'No', u'voucher_type': u'Journal Entry', u'against': u'_Test Customer', u'against_voucher_type': None,
                                    u'project': None, u'credit': 0.0, u'debit': 400.0, u'remarks': u'Note: test\nReference #33 dated 03-14-2013', u'posting_date': datetime.date(2013, 2, 14), u'voucher_no': u'_T-Journal Entry-00020', u'debit_in_account_currency': 400.0, u'cost_center': None, u'account_currency': None, u'bill_no': u''})
        self.assertEqual(data[17], {u'balance': 1200.03, u'party': None, u'account': u'_Test Bank - _TC', u'credit_in_account_currency': 400.0, u'against_voucher': None, u'party_type': None, u'is_opening': u'No', u'voucher_type': u'Journal Entry', u'against': u'_Test Supplier', u'against_voucher_type': None, u'project': None, u'credit': 400.0,
                                    u'debit': 0.0, u'remarks': u'Note: test\nReference #33 dated 02-14-2013\n\u20b9 0.00 against Purchase Order PUR-ORD-2018-00004', u'posting_date': datetime.date(2013, 2, 14), u'voucher_no': u'_T-Journal Entry-00021', u'debit_in_account_currency': 0.0, u'cost_center': None, u'account_currency': None, u'bill_no': u''})
        self.assertEqual(data[18], {u'balance': 1600.03, u'party': None, u'account': u'_Test Bank - _TC', u'credit_in_account_currency': 0.0, u'against_voucher': None, u'party_type': None, u'is_opening': u'No', u'voucher_type': u'Journal Entry', u'against': u'_Test Customer', u'against_voucher_type': None, u'project': None, u'credit': 0.0,
                                    u'debit': 400.0, u'remarks': u'Note: test\nReference #33 dated 03-14-2013\n\u20b9 400.00 against Sales Order SAL-ORD-2018-00004', u'posting_date': datetime.date(2013, 2, 14), u'voucher_no': u'_T-Journal Entry-00022', u'debit_in_account_currency': 400.0, u'cost_center': None, u'account_currency': None, u'bill_no': u''})
        self.assertEqual(data[19], {u'balance': 2000.03, u'party': None, u'account': u'_Test Bank - _TC', u'credit_in_account_currency': 0.0, u'against_voucher': None, u'party_type': None, u'is_opening': u'No', u'voucher_type': u'Journal Entry', u'against': u'_Test Customer', u'against_voucher_type': None,
                                    u'project': None, u'credit': 0.0, u'debit': 400.0, u'remarks': u'Note: test\nReference #33 dated 03-14-2013', u'posting_date': datetime.date(2013, 2, 14), u'voucher_no': u'_T-Journal Entry-00025', u'debit_in_account_currency': 400.0, u'cost_center': None, u'account_currency': None, u'bill_no': u''})
        self.assertEqual(data[20], {u'balance': 2400.0299999999997, u'party': u'_Test Supplier', u'account': u'_Test Payable - _TC', u'credit_in_account_currency': 0.0, u'against_voucher': u'PUR-ORD-2018-00001', u'party_type': u'Supplier', u'is_opening': u'No', u'voucher_type': u'Journal Entry', u'against': u'_Test Bank - _TC', u'against_voucher_type': u'Purchase Order',
                                    u'project': None, u'credit': 0.0, u'debit': 400.0, u'remarks': u'Note: test\nReference #33 dated 02-14-2013\n\u20b9 0.00 against Purchase Order PUR-ORD-2018-00001', u'posting_date': datetime.date(2013, 2, 14), u'voucher_no': u'_T-Journal Entry-00006', u'debit_in_account_currency': 400.0, u'cost_center': None, u'account_currency': None, u'bill_no': u''})
        self.assertEqual(data[21], {u'balance': 2800.0299999999997, u'party': u'_Test Supplier', u'account': u'_Test Payable - _TC', u'credit_in_account_currency': 0.0, u'against_voucher': u'PUR-ORD-2018-00002', u'party_type': u'Supplier', u'is_opening': u'No', u'voucher_type': u'Journal Entry', u'against': u'_Test Bank - _TC', u'against_voucher_type': u'Purchase Order',
                                    u'project': None, u'credit': 0.0, u'debit': 400.0, u'remarks': u'Note: test\nReference #33 dated 02-14-2013\n\u20b9 0.00 against Purchase Order PUR-ORD-2018-00002', u'posting_date': datetime.date(2013, 2, 14), u'voucher_no': u'_T-Journal Entry-00011', u'debit_in_account_currency': 400.0, u'cost_center': None, u'account_currency': None, u'bill_no': u''})
        self.assertEqual(data[22], {u'balance': 3200.0299999999997, u'party': u'_Test Supplier', u'account': u'_Test Payable - _TC', u'credit_in_account_currency': 0.0, u'against_voucher': u'PUR-ORD-2018-00003', u'party_type': u'Supplier', u'is_opening': u'No', u'voucher_type': u'Journal Entry', u'against': u'_Test Bank - _TC', u'against_voucher_type': u'Purchase Order',
                                    u'project': None, u'credit': 0.0, u'debit': 400.0, u'remarks': u'Note: test\nReference #33 dated 02-14-2013\n\u20b9 0.00 against Purchase Order PUR-ORD-2018-00003', u'posting_date': datetime.date(2013, 2, 14), u'voucher_no': u'_T-Journal Entry-00016', u'debit_in_account_currency': 400.0, u'cost_center': None, u'account_currency': None, u'bill_no': u''})
        self.assertEqual(data[23], {u'balance': 3600.0299999999997, u'party': u'_Test Supplier', u'account': u'_Test Payable - _TC', u'credit_in_account_currency': 0.0, u'against_voucher': u'PUR-ORD-2018-00004', u'party_type': u'Supplier', u'is_opening': u'No', u'voucher_type': u'Journal Entry', u'against': u'_Test Bank - _TC', u'against_voucher_type': u'Purchase Order',
                                    u'project': None, u'credit': 0.0, u'debit': 400.0, u'remarks': u'Note: test\nReference #33 dated 02-14-2013\n\u20b9 0.00 against Purchase Order PUR-ORD-2018-00004', u'posting_date': datetime.date(2013, 2, 14), u'voucher_no': u'_T-Journal Entry-00021', u'debit_in_account_currency': 400.0, u'cost_center': None, u'account_currency': None, u'bill_no': u''})
        self.assertEqual(data[24], {u'balance': 3200.0299999999997, u'party': u'_Test Customer', u'account': u'_Test Receivable - _TC', u'credit_in_account_currency': 400.0, u'against_voucher': None, u'party_type': u'Customer', u'is_opening': u'No', u'voucher_type': u'Journal Entry', u'against': u'_Test Bank - _TC',
                                    u'against_voucher_type': None, u'project': None, u'credit': 400.0, u'debit': 0.0, u'remarks': u'Note: test\nReference #33 dated 03-14-2013', u'posting_date': datetime.date(2013, 2, 14), u'voucher_no': u'_T-Journal Entry-00005', u'debit_in_account_currency': 0.0, u'cost_center': None, u'account_currency': None, u'bill_no': u''})
        self.assertEqual(data[25], {u'balance': 2800.0299999999997, u'party': u'_Test Customer', u'account': u'_Test Receivable - _TC', u'credit_in_account_currency': 400.0, u'against_voucher': u'SAL-ORD-2018-00001', u'party_type': u'Customer', u'is_opening': u'No', u'voucher_type': u'Journal Entry', u'against': u'_Test Bank - _TC', u'against_voucher_type': u'Sales Order',
                                    u'project': None, u'credit': 400.0, u'debit': 0.0, u'remarks': u'Note: test\nReference #33 dated 03-14-2013\n\u20b9 400.00 against Sales Order SAL-ORD-2018-00001', u'posting_date': datetime.date(2013, 2, 14), u'voucher_no': u'_T-Journal Entry-00007', u'debit_in_account_currency': 0.0, u'cost_center': None, u'account_currency': None, u'bill_no': u''})
        self.assertEqual(data[26], {u'balance': 2400.0299999999997, u'party': u'_Test Customer', u'account': u'_Test Receivable - _TC', u'credit_in_account_currency': 400.0, u'against_voucher': None, u'party_type': u'Customer', u'is_opening': u'No', u'voucher_type': u'Journal Entry', u'against': u'_Test Bank - _TC',
                                    u'against_voucher_type': None, u'project': None, u'credit': 400.0, u'debit': 0.0, u'remarks': u'Note: test\nReference #33 dated 03-14-2013', u'posting_date': datetime.date(2013, 2, 14), u'voucher_no': u'_T-Journal Entry-00010', u'debit_in_account_currency': 0.0, u'cost_center': None, u'account_currency': None, u'bill_no': u''})
        self.assertEqual(data[27], {u'balance': 2000.0299999999997, u'party': u'_Test Customer', u'account': u'_Test Receivable - _TC', u'credit_in_account_currency': 400.0, u'against_voucher': u'SAL-ORD-2018-00002', u'party_type': u'Customer', u'is_opening': u'No', u'voucher_type': u'Journal Entry', u'against': u'_Test Bank - _TC', u'against_voucher_type': u'Sales Order',
                                    u'project': None, u'credit': 400.0, u'debit': 0.0, u'remarks': u'Note: test\nReference #33 dated 03-14-2013\n\u20b9 400.00 against Sales Order SAL-ORD-2018-00002', u'posting_date': datetime.date(2013, 2, 14), u'voucher_no': u'_T-Journal Entry-00012', u'debit_in_account_currency': 0.0, u'cost_center': None, u'account_currency': None, u'bill_no': u''})
        self.assertEqual(data[28], {u'balance': 1600.0299999999997, u'party': u'_Test Customer', u'account': u'_Test Receivable - _TC', u'credit_in_account_currency': 400.0, u'against_voucher': None, u'party_type': u'Customer', u'is_opening': u'No', u'voucher_type': u'Journal Entry', u'against': u'_Test Bank - _TC',
                                    u'against_voucher_type': None, u'project': None, u'credit': 400.0, u'debit': 0.0, u'remarks': u'Note: test\nReference #33 dated 03-14-2013', u'posting_date': datetime.date(2013, 2, 14), u'voucher_no': u'_T-Journal Entry-00015', u'debit_in_account_currency': 0.0, u'cost_center': None, u'account_currency': None, u'bill_no': u''})
        self.assertEqual(data[29], {u'balance': 1200.0299999999997, u'party': u'_Test Customer', u'account': u'_Test Receivable - _TC', u'credit_in_account_currency': 400.0, u'against_voucher': u'SAL-ORD-2018-00003', u'party_type': u'Customer', u'is_opening': u'No', u'voucher_type': u'Journal Entry', u'against': u'_Test Bank - _TC', u'against_voucher_type': u'Sales Order',
                                    u'project': None, u'credit': 400.0, u'debit': 0.0, u'remarks': u'Note: test\nReference #33 dated 03-14-2013\n\u20b9 400.00 against Sales Order SAL-ORD-2018-00003', u'posting_date': datetime.date(2013, 2, 14), u'voucher_no': u'_T-Journal Entry-00017', u'debit_in_account_currency': 0.0, u'cost_center': None, u'account_currency': None, u'bill_no': u''})
        self.assertEqual(data[30], {u'balance': 800.0299999999997, u'party': u'_Test Customer', u'account': u'_Test Receivable - _TC', u'credit_in_account_currency': 400.0, u'against_voucher': None, u'party_type': u'Customer', u'is_opening': u'No', u'voucher_type': u'Journal Entry', u'against': u'_Test Bank - _TC',
                                    u'against_voucher_type': None, u'project': None, u'credit': 400.0, u'debit': 0.0, u'remarks': u'Note: test\nReference #33 dated 03-14-2013', u'posting_date': datetime.date(2013, 2, 14), u'voucher_no': u'_T-Journal Entry-00020', u'debit_in_account_currency': 0.0, u'cost_center': None, u'account_currency': None, u'bill_no': u''})
        self.assertEqual(data[31], {u'balance': 400.02999999999975, u'party': u'_Test Customer', u'account': u'_Test Receivable - _TC', u'credit_in_account_currency': 400.0, u'against_voucher': u'SAL-ORD-2018-00004', u'party_type': u'Customer', u'is_opening': u'No', u'voucher_type': u'Journal Entry', u'against': u'_Test Bank - _TC', u'against_voucher_type': u'Sales Order',
                                    u'project': None, u'credit': 400.0, u'debit': 0.0, u'remarks': u'Note: test\nReference #33 dated 03-14-2013\n\u20b9 400.00 against Sales Order SAL-ORD-2018-00004', u'posting_date': datetime.date(2013, 2, 14), u'voucher_no': u'_T-Journal Entry-00022', u'debit_in_account_currency': 0.0, u'cost_center': None, u'account_currency': None, u'bill_no': u''})
        self.assertEqual(data[32], {u'balance': 0.02999999999974534, u'party': u'_Test Customer', u'account': u'_Test Receivable - _TC', u'credit_in_account_currency': 400.0, u'against_voucher': None, u'party_type': u'Customer', u'is_opening': u'No', u'voucher_type': u'Journal Entry', u'against': u'_Test Bank - _TC',
                                    u'against_voucher_type': None, u'project': None, u'credit': 400.0, u'debit': 0.0, u'remarks': u'Note: test\nReference #33 dated 03-14-2013', u'posting_date': datetime.date(2013, 2, 14), u'voucher_no': u'_T-Journal Entry-00025', u'debit_in_account_currency': 0.0, u'cost_center': None, u'account_currency': None, u'bill_no': u''})
        self.assertEqual(data[33], {u'balance': 0.01999999999974534, u'party': None, u'account': u'_Test Write Off - _TC', u'credit_in_account_currency': 0.01, u'against_voucher': None, u'party_type': None, u'is_opening': u'No', u'voucher_type': u'Journal Entry', u'against': None, u'against_voucher_type': None,
                                    u'project': None, u'credit': 0.01, u'debit': 0.0, u'remarks': u'Note: test', u'posting_date': datetime.date(2013, 2, 14), u'voucher_no': u'ACC-JV-2018-00001', u'debit_in_account_currency': 0.0, u'cost_center': u'_Test Cost Center - _TC', u'account_currency': None, u'bill_no': u''})
        self.assertEqual(data[34], {u'balance': 0.00999999999974534, u'party': None, u'account': u'_Test Write Off - _TC', u'credit_in_account_currency': 0.01, u'against_voucher': None, u'party_type': None, u'is_opening': u'No', u'voucher_type': u'Journal Entry', u'against': None, u'against_voucher_type': None,
                                    u'project': None, u'credit': 0.01, u'debit': 0.0, u'remarks': u'Note: test', u'posting_date': datetime.date(2013, 2, 14), u'voucher_no': u'ACC-JV-2018-00002', u'debit_in_account_currency': 0.0, u'cost_center': u'_Test Cost Center - _TC', u'account_currency': None, u'bill_no': u''})
        self.assertEqual(data[35], {u'balance': -2.5466087572034724e-13, u'party': None, u'account': u'_Test Write Off - _TC', u'credit_in_account_currency': 0.01, u'against_voucher': None, u'party_type': None, u'is_opening': u'No', u'voucher_type': u'Journal Entry', u'against': None, u'against_voucher_type': None,
                                    u'project': None, u'credit': 0.01, u'debit': 0.0, u'remarks': u'Note: test', u'posting_date': datetime.date(2013, 2, 14), u'voucher_no': u'ACC-JV-2018-00003', u'debit_in_account_currency': 0.0, u'cost_center': u'_Test Cost Center - _TC', u'account_currency': None, u'bill_no': u''})
        self.assertEqual(data[36], {u'bill_no': u'', 'account': u"'Total'", 'debit_in_account_currency': 5500.0, 'credit': 5500.030000000001,
                                    'debit': 5500.03, u'account_currency': None, u'balance': -9.094947017729282e-13, 'credit_in_account_currency': 5500.030000000001})
        self.assertEqual(data[37], {u'bill_no': u'', 'account': u"'Closing (Opening + Total)'", 'debit_in_account_currency': 5500.0, 'credit': 5500.030000000001,
                                    'debit': 5500.03, u'account_currency': None, u'balance': -9.094947017729282e-13, 'credit_in_account_currency': 5500.030000000001})
        self.assertEqual(len(data), 38)

    def test_trial_balance(self):
        report = frappe.get_doc('Report', 'Trial Balance')
        columns, data = report.get_data(
            filters={'company': '_Test Company', 'fiscal_year': frappe.get_doc('Fiscal Year', '_Test Fiscal Year 2013').year})
        self.assertEqual(report.report_type, 'Script Report')
#        01-01-2013 12-31-2013
        self.assertEqual(data[0], {u'closing_credit': 0.0, u'account': u'Application of Funds (Assets) - _TC', u'indent': 0, u'credit': 5500.0, u'opening_debit': 0.0, u'closing_debit': -1900.0, u'parent_account': None,
                                   u'currency': u'INR', u'from_date': datetime.date(2013, 1, 1), u'has_value': True, u'to_date': datetime.date(2013, 12, 31), u'debit': 3600.0, u'opening_credit': 0.0, u'account_name': u'Application of Funds (Assets)'})
        self.assertEqual(data[1], {u'closing_credit': 0.0, u'account': u'Current Assets - _TC', u'indent': 1, u'credit': 5500.0, u'opening_debit': 0.0, u'closing_debit': -1900.0, u'parent_account': u'Application of Funds (Assets) - _TC',
                                   u'currency': u'INR', u'from_date': datetime.date(2013, 1, 1), u'has_value': True, u'to_date': datetime.date(2013, 12, 31), u'debit': 3600.0, u'opening_credit': 0.0, u'account_name': u'Current Assets'})
        self.assertEqual(data[2], {u'closing_credit': 0.0, u'account': u'_Test Receivable - _TC', u'indent': 2, u'credit': 3600.0, u'opening_debit': 0.0, u'closing_debit': -3600.0, u'parent_account': u'Current Assets - _TC',
                                   u'currency': u'INR', u'from_date': datetime.date(2013, 1, 1), u'has_value': True, u'to_date': datetime.date(2013, 12, 31), u'debit': 0.0, u'opening_credit': 0.0, u'account_name': u'_Test Receivable'})
        self.assertEqual(data[3], {u'closing_credit': 0.0, u'account': u'Bank Accounts - _TC', u'indent': 2, u'credit': 1900.0, u'opening_debit': 0.0, u'closing_debit': 1700.0, u'parent_account': u'Current Assets - _TC',
                                   u'currency': u'INR', u'from_date': datetime.date(2013, 1, 1), u'has_value': True, u'to_date': datetime.date(2013, 12, 31), u'debit': 3600.0, u'opening_credit': 0.0, u'account_name': u'Bank Accounts'})
        self.assertEqual(data[4], {u'closing_credit': 0.0, u'account': u'_Test Bank - _TC', u'indent': 3, u'credit': 1900.0, u'opening_debit': 0.0, u'closing_debit': 1700.0, u'parent_account': u'Bank Accounts - _TC',
                                   u'currency': u'INR', u'from_date': datetime.date(2013, 1, 1), u'has_value': True, u'to_date': datetime.date(2013, 12, 31), u'debit': 3600.0, u'opening_credit': 0.0, u'account_name': u'_Test Bank'})
        self.assertEqual(data[5], {u'closing_credit': -1600.0, u'account': u'Source of Funds (Liabilities) - _TC', u'indent': 0, u'credit': 0.0, u'opening_debit': 0.0, u'closing_debit': 0.0, u'parent_account': None,
                                   u'currency': u'INR', u'from_date': datetime.date(2013, 1, 1), u'has_value': True, u'to_date': datetime.date(2013, 12, 31), u'debit': 1600.0, u'opening_credit': 0.0, u'account_name': u'Source of Funds (Liabilities)'})
        self.assertEqual(data[6], {u'closing_credit': -1600.0, u'account': u'Current Liabilities - _TC', u'indent': 1, u'credit': 0.0, u'opening_debit': 0.0, u'closing_debit': 0.0, u'parent_account': u'Source of Funds (Liabilities) - _TC',
                                   u'currency': u'INR', u'from_date': datetime.date(2013, 1, 1), u'has_value': True, u'to_date': datetime.date(2013, 12, 31), u'debit': 1600.0, u'opening_credit': 0.0, u'account_name': u'Current Liabilities'})
        self.assertEqual(data[7], {u'closing_credit': -1600.0, u'account': u'_Test Payable - _TC', u'indent': 2, u'credit': 0.0, u'opening_debit': 0.0, u'closing_debit': 0.0, u'parent_account': u'Current Liabilities - _TC',
                                   u'currency': u'INR', u'from_date': datetime.date(2013, 1, 1), u'has_value': True, u'to_date': datetime.date(2013, 12, 31), u'debit': 1600.0, u'opening_credit': 0.0, u'account_name': u'_Test Payable'})
        self.assertEqual(data[8], {u'closing_credit': 0.0, u'account': u'Expenses - _TC', u'indent': 0, u'credit': 0.03, u'opening_debit': 0.0, u'closing_debit': 300.0, u'parent_account': None,
                                   u'currency': u'INR', u'from_date': datetime.date(2013, 1, 1), u'has_value': True, u'to_date': datetime.date(2013, 12, 31), u'debit': 300.03, u'opening_credit': 0.0, u'account_name': u'Expenses'})
        self.assertEqual(data[10], {u'closing_credit': 0.0, u'account': u'Indirect Expenses - _TC', u'indent': 1, u'credit': 0.03, u'opening_debit': 0.0, u'closing_debit': -0.03, u'parent_account': u'Expenses - _TC',
                                    u'currency': u'INR', u'from_date': datetime.date(2013, 1, 1), u'has_value': True, u'to_date': datetime.date(2013, 12, 31), u'debit': 0.0, u'opening_credit': 0.0, u'account_name': u'Indirect Expenses'})
        self.assertEqual(data[11], {u'closing_credit': 0.0, u'account': u'_Test Write Off - _TC', u'indent': 2, u'credit': 0.03, u'opening_debit': 0.0, u'closing_debit': -0.03, u'parent_account': u'Indirect Expenses - _TC',
                                    u'currency': u'INR', u'from_date': datetime.date(2013, 1, 1), u'has_value': True, u'to_date': datetime.date(2013, 12, 31), u'debit': 0.0, u'opening_credit': 0.0, u'account_name': u'_Test Write Off'})
        self.assertEqual(data[9], {u'closing_credit': 0.0, u'account': u'_Test Account Cost for Goods Sold - _TC', u'indent': 1, u'credit': 0.0, u'opening_debit': 0.0, u'closing_debit': 300.03, u'parent_account': u'Expenses - _TC',
                                   u'currency': u'INR', u'from_date': datetime.date(2013, 1, 1), u'has_value': True, u'to_date': datetime.date(2013, 12, 31), u'debit': 300.03, u'opening_credit': 0.0, u'account_name': u'_Test Account Cost for Goods Sold'})
        self.assertEqual(data[13], {u'closing_credit': -1600.0, u'opening_credit': 0.0, u'parent_account': None, u'currency': u'INR', u'closing_debit': -1600.0, u'account_name': r"'Total'",
                                    u'account': r"'Total'", u'indent': 0, u'has_value': True, u'opening_debit': 0.0, u'warn_if_negative': True, u'credit': 5500.03, u'debit': 5500.03})
        self.assertEqual(len(data), 14)

    def test_accounts_receivable(self):
        report = frappe.get_doc('Report', 'Accounts Receivable')
        columns, data = report.get_data(filters={'company': '_Test Company', 'report_date': datetime.date(
            2013, 3, 30), 'ageing_based_on': 'Posting Date'})
        self.assertEqual(report.report_type, 'Script Report')
        fieldnames = [u'posting_date', u'Customer', u'voucher_type', u'paid_amount', u'outstanding_amount', u'currency',
                      u'Remaining Balance', u'Territory', u'Customer Group', u'Remarks']
        index = self.get_index(fieldnames, columns)
        actual = self.get_elements(data[0], index)
        expected = [datetime.date(2013, 2, 14), u'_Test Customer', u'Journal Entry', 400.0, -400.0, u'INR', -
                    400.0, u'_Test Territory', u'_Test Customer Group', u'Note: test\nReference #33 dated 03-14-2013']
        self.assertEqual(actual, expected)
        self.assertEqual(len(data), 10)

    def get_index(self, fieldnames, columns):
        index = []
        for i in range(len(columns)):
            column = columns[i]
            if column.get('fieldname') in fieldnames:
                index.append(i)
        return index

    def get_elements(self, data, index):
        elements = []
        for i in index:
            elements.append(data[i])
        return elements

    def test_accounts_payable(self):
        report = frappe.get_doc('Report', 'Accounts Payable')
        columns, data = report.get_data(filters={'company': '_Test Company'})
        self.assertEqual(report.report_type, 'Script Report')
        fieldnames = [u'posting_date', u'Supplier', u'voucher_type', u'paid_amount', u'outstanding_amount', u'currency',
                      u'Remaining Balance', u'Territory', u'Supplier Group', u'Remarks']
        index = self.get_index(fieldnames, columns)
        actual = self.get_elements(data[0], index)
        expected = [datetime.date(2013, 2, 14), u'_Test Supplier', u'Journal Entry', 400.0, -400.0, 'INR', -400.0, u'_Test Supplier Group',
                    u'Note: test\nReference #33 dated 02-14-2013\n\u20b9 0.00 against Purchase Order PUR-ORD-2018-00001']
        self.assertEqual(actual, expected)
        self.assertEqual(len(data), 5)

    def test_accounts_receivable_summary(self):
        report = frappe.get_doc('Report', 'Accounts Receivable Summary')
        columns, data = report.get_data(filters={'company': '_Test Company'})
        self.assertEqual(report.report_type, 'Script Report')
        self.assertEqual(data[0], [u'_Test Customer USD', 10000.0, 51320.0, 0.0, -41320.0, -
                                   28740.0, 0.0, -12580.0, 0.0, u'_Test Territory', u'_Test Customer Group', u'INR'])
        self.assertEqual(data[1], [u'_Test Customer', 100.0, 3700.0, 100.0, -3700.0, -
                                   100.0, 0.0, 0.0, -3600.0, u'_Test Territory', u'_Test Customer Group', u'INR'])
        self.assertEqual(data[2], [u"'Total'", 10100.0, 55020.0, 100.0, -
                                   45020.0, -28840.0, u'', -12580.0, -3600.0, u'', u'', u'INR'])
        self.assertEqual(len(data), 3)

    def test_accounts_payable_summary(self):
        report = frappe.get_doc('Report', 'Accounts Payable Summary')
        columns, data = report.get_data(filters={'company': '_Test Company'})
        self.assertEqual(report.report_type, 'Script Report')
        self.assertEqual(data[0], [u'_Test Supplier', 0.0, 1600.0, 0.0, -
                                   1600.0, 0.0, 0.0, 0.0, -1600.0, u'_Test Supplier Group', u'INR'])
        self.assertEqual(data[1], [u"'Total'", u'', 1600.0,
                                   u'', -1600.0, u'', u'', u'', -1600.0, u'', u'INR'])
        self.assertEqual(len(data), 2)
