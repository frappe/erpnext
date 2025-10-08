import unittest
from unittest.mock import patch, MagicMock
import frappe
from frappe.tests.utils import FrappeTestCase
from datetime import date, datetime

# Import the module being tested
from erpnext.accounts.report.cheques_and_deposits_incorrectly_cleared.cheques_and_deposits_incorrectly_cleared import (
    execute,
    build_payment_entry_dict,
    build_journal_entry_dict,
    build_data,
    get_amounts_not_reflected_in_system_for_bank_reconciliation_statement,
    get_columns
)


class TestChequesAndDepositsIncorrectlyCleared(FrappeTestCase):
    
    def setUp(self):
        self.filters = frappe._dict({
            'account': 'Test Bank Account - TC',
            'report_date': '2024-01-31'
        })
        
        self.sample_payment_entry = frappe._dict({
            'doctype': 'Payment Entry',
            'name': 'PE-00001',
            'posting_date': '2024-02-01',
            'clearance_date': '2024-01-30',
            'amount': 1000.0,
            'payment_type': 'Receive',
            'party_type': 'Customer'
        })
        
        self.sample_journal_entry = frappe._dict({
            'doctype': 'Journal Entry',
            'name': 'JE-00001',
            'posting_date': '2024-02-01',
            'clearance_date': '2024-01-30',
            'debit_in_account_currency': 500.0,
            'credit_in_account_currency': 0.0
        })

    def test_build_payment_entry_dict_receive_customer_TC_ACC_505(self):
        result = build_payment_entry_dict(self.sample_payment_entry)
        
        expected = {
            'payment_document': 'Payment Entry',
            'payment_entry': 'PE-00001',
            'posting_date': '2024-02-01',
            'clearance_date': '2024-01-30',
            'debit': 1000.0,
            'credit': 0
        }
        
        for key, value in expected.items():
            self.assertEqual(result[key], value)

    def test_build_payment_entry_dict_payment_TC_ACC_506(self):
        payment_data = self.sample_payment_entry.copy()
        payment_data.payment_type = 'Pay'
        
        result = build_payment_entry_dict(payment_data)
        
        self.assertEqual(result['debit'], 0)
        self.assertEqual(result['credit'], 1000.0)

    def test_build_payment_entry_dict_receive_non_customer_TC_ACC_507(self):
        payment_data = self.sample_payment_entry.copy()
        payment_data.party_type = 'Employee'
        
        result = build_payment_entry_dict(payment_data)
        
        self.assertEqual(result['debit'], 0)
        self.assertEqual(result['credit'], 1000.0)

    def test_build_journal_entry_dict_TC_ACC_508(self):
        result = build_journal_entry_dict(self.sample_journal_entry)
        
        expected = {
            'payment_document': 'Journal Entry',
            'payment_entry': 'JE-00001',
            'posting_date': '2024-02-01',
            'clearance_date': '2024-01-30',
            'debit': 500.0,
            'credit': 0.0
        }
        
        for key, value in expected.items():
            self.assertEqual(result[key], value)

    @patch('erpnext.accounts.report.cheques_and_deposits_incorrectly_cleared.cheques_and_deposits_incorrectly_cleared.get_amounts_not_reflected_in_system_for_bank_reconciliation_statement')
    def test_build_data_TC_ACC_509(self, mock_get_amounts):
        mock_get_amounts.return_value = [
            self.sample_payment_entry,
            self.sample_journal_entry
        ]
        result = build_data(self.filters)
        self.assertEqual(len(result), 2)
        
        self.assertEqual(result[0]['payment_document'], 'Payment Entry')
        self.assertEqual(result[0]['debit'], 1000.0)
        
        self.assertEqual(result[1]['payment_document'], 'Journal Entry')
        self.assertEqual(result[1]['debit'], 500.0)

    def test_build_data_empty_vouchers_TC_ACC_510(self):
        with patch('erpnext.accounts.report.cheques_and_deposits_incorrectly_cleared.cheques_and_deposits_incorrectly_cleared.get_amounts_not_reflected_in_system_for_bank_reconciliation_statement') as mock_get_amounts:
            mock_get_amounts.return_value = []
            
            result = build_data(self.filters)
            
            self.assertEqual(result, [])

    def test_edge_cases_payment_entry_dict_TC_ACC_511(self):
        incomplete_entry = frappe._dict({
            'doctype': 'Payment Entry',
            'name': 'PE-00002'
        })
        
        result = build_payment_entry_dict(incomplete_entry)
        
        self.assertEqual(result['payment_document'], 'Payment Entry')
        self.assertEqual(result['payment_entry'], 'PE-00002')
        self.assertIsNone(result.get('posting_date'))
        self.assertIsNone(result.get('clearance_date'))

    def test_edge_cases_journal_entry_dict_TC_ACC_512(self):
        incomplete_entry = frappe._dict({
            'doctype': 'Journal Entry',
            'name': 'JE-00002',
            'debit_in_account_currency': None,
            'credit_in_account_currency': None
        })
        
        result = build_journal_entry_dict(incomplete_entry)
        
        self.assertEqual(result['payment_document'], 'Journal Entry')
        self.assertEqual(result['payment_entry'], 'JE-00002')
        self.assertIsNone(result['debit'])
        self.assertIsNone(result['credit'])

    
    @patch('frappe.qb.from_')
    @patch('frappe.qb.DocType')
    def test_get_amounts_not_reflected_in_system_for_bank_reconciliation_statement_TC_ACC_513(self, mock_doctype, mock_from):
        mock_journal_entries = [
            frappe._dict({
                'doctype': 'Journal Entry',
                'name': 'JE-00001',
                'debit_in_account_currency': 1500.0,
                'credit_in_account_currency': 0.0,
                'posting_date': '2024-02-01',
                'clearance_date': '2024-01-30'
            })
        ]
        
        mock_payment_entries = [
            frappe._dict({
                'doctype': 'Payment Entry',
                'name': 'PE-00001',
                'amount': 2000.0,
                'payment_type': 'Receive',
                'party_type': 'Customer',
                'posting_date': '2024-02-01',
                'clearance_date': '2024-01-30'
            })
        ]
        
        mock_query = MagicMock()
        mock_query.inner_join.return_value = mock_query
        mock_query.on.return_value = mock_query
        mock_query.select.return_value = mock_query
        mock_query.where.return_value = mock_query
        
        mock_query.run.side_effect = [mock_journal_entries, mock_payment_entries]
        
        mock_from.return_value = mock_query
        mock_doctype.return_value = MagicMock()
        
        result = get_amounts_not_reflected_in_system_for_bank_reconciliation_statement(self.filters)
        
        self.assertEqual(len(result), 2)
        
        # Check journal entry is included
        journal_entry = result[0]
        self.assertEqual(journal_entry['doctype'], 'Journal Entry')
        self.assertEqual(journal_entry['name'], 'JE-00001')
        self.assertEqual(journal_entry['debit_in_account_currency'], 1500.0)
        
        # Check payment entry is included
        payment_entry = result[1]
        self.assertEqual(payment_entry['doctype'], 'Payment Entry')
        self.assertEqual(payment_entry['name'], 'PE-00001')
        self.assertEqual(payment_entry['amount'], 2000.0)
        
        self.assertEqual(mock_query.run.call_count, 2)