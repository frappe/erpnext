# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe import qb
from frappe.utils import getdate

from erpnext.accounts.doctype.bank_statement_import_log.bank_statement_import_log import (
	BankStatementImportLog,
	get_float_amount,
)
from erpnext.accounts.test.accounts_mixin import AccountsTestMixin
from erpnext.tests.utils import ERPNextTestSuite


class TestBankStatementImportLog(ERPNextTestSuite, AccountsTestMixin):
	def setUp(self):
		self.create_company()
		self.create_customer()
		self.clear_old_entries()
		bank_dt = qb.DocType("Bank")
		qb.from_(bank_dt).delete().where(bank_dt.name == "HDFC").run()
		self.create_bank_account()

	def create_bank_account(self):
		bank = frappe.get_doc(
			{
				"doctype": "Bank",
				"bank_name": "HDFC",
			}
		).save()

		self.bank_account = (
			frappe.get_doc(
				{
					"doctype": "Bank Account",
					"account_name": "HDFC _current_",
					"bank": bank.name,
					"is_company_account": True,
					"account": self.bank,
					"company": self.company,
				}
			)
			.insert()
			.name
		)

	def _create_bank_statement_import_log(self, test_data: list[list[str]]):
		doc = frappe.get_doc(
			{
				"doctype": "Bank Statement Import Log",
				"bank_account": self.bank_account,
			}
		)

		doc.set_file_properties(test_data)
		return doc

	def get_column_map(self, doc: BankStatementImportLog):
		column_map: dict[str, int] = {}
		for column in doc.column_mapping:
			column_map[column.maps_to] = column.index
		return column_map

	def _check_output(self, doc: BankStatementImportLog, expected_output: dict):
		fields_to_check = [
			"number_of_transactions",
			"detected_date_format",
			"detected_amount_format",
			"detected_header_index",
			"detected_transaction_starting_index",
			"detected_transaction_ending_index",
			"closing_balance",
			"total_debits",
			"total_credits",
			"total_debit_transactions",
			"total_credit_transactions",
			"start_date",
			"end_date",
		]
		for field in fields_to_check:
			self.assertEqual(getattr(doc, field), expected_output[field])

		column_map = self.get_column_map(doc)

		for field, column_index in expected_output["column_mapping"].items():
			self.assertEqual(column_map[field], column_index)

	def test_sample_statement_import_log(self):
		test_data = [
			[test_hdfc_sample_statement_data, test_hdfc_expected_output],
			[test_icici_sample_statement_data, test_icici_expected_output],
			[test_axis_sample_statement_data, test_axis_expected_output],
			[test_amount_with_currency_data, test_amount_with_currency_expected_output],
		]
		for data, expected_output in test_data:
			doc = self._create_bank_statement_import_log(data)
			self._check_output(doc, expected_output)

	def test_amount_parser(self):
		# Parse numeric strings after removing all characters except digits, decimal point, and minus sign
		self.assertEqual(get_float_amount("100.27"), 100.27)
		self.assertEqual(get_float_amount("100.20 INR"), 100.20)
		self.assertEqual(get_float_amount("1,000.20 INR"), 1000.20)
		self.assertEqual(get_float_amount("-1,000.34 INR"), -1000.34)
		self.assertEqual(get_float_amount("100.00 CR"), 100.00)
		self.assertEqual(get_float_amount("100.00 DR"), 100.00)

		# Numbers should be returned as floats
		self.assertEqual(get_float_amount(100), 100.00)

		# Random strings and characters should not throw a ValueError but return None
		self.assertIsNone(get_float_amount("ABCD"))
		self.assertIsNone(get_float_amount("****"))


test_hdfc_sample_statement_data = [
	["HDFC BANK Ltd.  Page No .: 1  Statement of accounts", "", "", "", "", "", ""],
	["", "", "", "", "Account Branch :SOBO", "", ""],
	["Test Company", "", "", "", "Address :Some Address", "", ""],
	["********", "", "", "", "", "", ""],
	["Date", "Narration", "Chq./Ref.No.", "Value Dt", "Withdrawal Amt.", "Deposit Amt.", "Closing Balance"],
	["********", "*********", "************", "********", "*********", "**********", "**********"],
	["08/08/25", "CRAFTSMAN", "0000252193", "08/08/25", "", 10.0, 574318.9],
	["08/08/25", "ACH C- PID", "00000020", "08/08/25", "", 100.0, 573918.9],
	["09/08/25", "UPI-APPLE SERVICES-BILLDESKPG", "0000101169070023", "09/08/25", 5000.0, "", 568918.9],
	["09/08/25", "UPI-APPLE SERVICES-BILLDESKPG", "0000101174017987", "09/08/25", 10000.0, "", 558518.9],
	["10/08/25", "UPI-ENTERPRIS-9082053531", "0000109578171801", "10/08/25", 300.0, "", 558218.9],
	["11/08/25", "HDFC BANK SPL INT DIV 2025-26", "00920", "11/08/25", "", 35.0, 558253.9],
	["", "", "", "", "", "", ""],
	["********", "****************", "************", "********", "************", "*********", "*********"],
	["*********", "", "", "", "", "", ""],
	["---  End Of Statement ---", "", "", "", "", "", ""],
]
test_hdfc_expected_output = {
	"number_of_transactions": 6,
	"detected_date_format": "%d/%m/%y",
	"detected_amount_format": "Separate columns for withdrawal and deposit",
	"detected_header_index": 4,
	"detected_transaction_starting_index": 6,
	"detected_transaction_ending_index": 11,
	"closing_balance": 558253.9,
	"total_debits": 15300,
	"total_credits": 145,
	"total_debit_transactions": 3,
	"total_credit_transactions": 3,
	"start_date": getdate("2025-08-08"),
	"end_date": getdate("2025-08-11"),
	"column_mapping": {
		"Date": 0,
		"Description": 1,
		"Reference": 2,
		"Withdrawal": 4,
		"Deposit": 5,
		"Balance": 6,
	},
}

test_icici_sample_statement_data = [
	["DETAILED STATEMENT", "", "", "", "", "", "", "", ""],
	[" ", "", "", "", "", "", "", "", ""],
	[" ", "", "", "", "", "", "", "", ""],
	[" ", "", "", "", "", "", "", "", ""],
	[" ", "", "", "", "", "", "", "", ""],
	["Transactions List -Test Company", "", "", "", "", "", "", "", ""],
	[
		"No.",
		"Transaction ID",
		"Value Date",
		"Txn Posted Date",
		"ChequeNo.",
		"Description",
		"Cr/Dr",
		"Transaction Amount(INR)",
		"Available Balance(INR)",
	],
	[1.0, "S00000001", "15/04/2024", "15/04/2024 02:05:31 PM ", "-", "Mob alrt", "DR", 29.5, 261454.89],
	[2.0, "S00000002", "19/04/2024", "19/04/2024 04:08:02 PM ", "-", "GIB/0020", "DR", 12600.0, 248854.89],
	[3.0, "S00000003", "10/05/2024", "10/05/2024 03:32:02 PM ", "-", "Test Co", "CR", 3000000.0, 3248854.89],
	[4.0, "S00000004", "10/05/2024", "10/05/2024 03:40:50 PM ", "-", "TRF TO", "DR", 3000000.0, 248854.89],
	[5.0, "S00000005", "20/05/2024", "20/05/2024 03:52:17 PM ", "-", "BIL/MAKE", "DR", 68811.0, 180043.89],
	[6.0, "S00000006", "20/05/2024", "20/05/2024 03:55:27 PM ", "-", "BIL/MAKE", "DR", 40126.0, 139917.89],
	[7.0, "S00000007", "31/05/2024", "31/05/2024 03:42:34 PM ", "-", "NEFT-FRAPPE", "CR", 32400.0, 172317.89],
	[8.0, "S00000008", "24/06/2024", "24/06/2024 04:09:25 PM ", "-", "GIB/STAX", "DR", 2500.0, 169817.89],
	[
		9.0,
		"S00000009",
		"24/06/2024",
		"24/06/2024 04:15:37 PM ",
		"-",
		"BIL/ONL/00085",
		"DR",
		2150.0,
		167667.89,
	],
	[
		10.0,
		"S00000010",
		"05/07/2024",
		"05/07/2024 05:50:10 PM ",
		"-",
		"NEFT-N18724",
		"CR",
		75600.0,
		243267.89,
	],
	[11.0, "S00000011", "30/07/2024", "30/07/2024 12:18:01 PM ", "-", "Mob al", "DR", 29.5, 243238.39],
	[12.0, "S00000012", "01/08/2024", "01/08/2024 12:45:49 PM ", "-", "NEFT-N214", "CR", 117720.0, 360958.39],
]
test_icici_expected_output = {
	"number_of_transactions": 12,
	"detected_date_format": "%d/%m/%Y",
	"detected_amount_format": 'Transaction type column has "CR"/"DR" values',
	"detected_header_index": 6,
	"detected_transaction_starting_index": 7,
	"detected_transaction_ending_index": 18,
	"closing_balance": 360958.39,
	"total_debits": 3126246.0,
	"total_credits": 3225720.0,
	"total_debit_transactions": 8,
	"total_credit_transactions": 4,
	"start_date": getdate("2024-04-15"),
	"end_date": getdate("2024-08-01"),
	"column_mapping": {
		"Date": 2,
		"Description": 5,
		"Reference": 1,
		"Debit/Credit": 6,
		"Amount": 7,
		"Balance": 8,
	},
}

test_axis_sample_statement_data = [
	["Name :- XXXXXXXX", None, None, None, None, None, None, None, None, None, None],
	["Joint Holder :-- ", None, None, None, None, None, None, None, None, None, None],
	[None, None, None, None, None, None, None, None, None, None, None],
	[None, None, None, None, None, None, None, None, None, None, None],
	[
		"Statement",
		None,
		None,
		None,
		None,
		None,
		None,
		None,
		None,
		None,
		None,
	],
	[None, None, None, None, None, None, None, None, None, None, None],
	[
		"S.NO",
		"Transaction Date (dd/mm/yyyy)",
		"Value Date (dd/mm/yyyy)",
		"Particulars",
		"Amount(INR)",
		"Debit/Credit",
		"Balance(INR)",
		"Cheque Number",
		"Branch Name(SOL)",
		None,
		None,
	],
	["1", "", "", "OPENING BAL", "", "", "3,25,867.05", "", "NAG MH", None, None],
	["2", "05/04/2026", "05/04/2026", "NEFT", "59,000.00", "CR", "3,84,867.05", "", "NAG", None, None],
	[
		"3",
		"05/04/2026",
		"05/04/2026",
		"XXXInt.Coll",
		"1,13,969.00",
		"DR",
		"2,70,898.05",
		"",
		"NAG",
		None,
		None,
	],
	["4", "", "", "TOTAL DR/CR", "1,13,969.00/59,000.00", "", "", "", "NAG", None, None],
	["5", "", "", "CLOSING BAL", "", "", "2,70,898.05", "", "NAG", None, None],
]
test_axis_expected_output = {
	"number_of_transactions": 2,
	"detected_date_format": "%d/%m/%Y",
	"detected_amount_format": 'Transaction type column has "CR"/"DR" values',
	"detected_header_index": 6,
	"detected_transaction_starting_index": 8,
	"detected_transaction_ending_index": 9,
	"closing_balance": 270898.05,
	"total_debits": 113969.00,
	"total_credits": 59000.00,
	"total_debit_transactions": 1,
	"total_credit_transactions": 1,
	"start_date": getdate("2026-04-05"),
	"end_date": getdate("2026-04-05"),
	"column_mapping": {
		"Date": 1,
		"Description": 3,
		"Reference": 7,
		"Debit/Credit": 5,
		"Amount": 4,
		"Balance": 6,
	},
}

test_amount_with_currency_data = [
	["Statement"],
	["Opening Balance:  INR 1,11,71,360.24"],
	[
		"S. No.",
		"Transaction Date",
		"Transaction ID",
		"Transaction Serial Number",
		"Cheque Number",
		"Transaction Particulars",
		"Remarks",
		"Debit Amount",
		"Credit Amount",
	],
	[2, "01/04/2026", "S68420508", "1", "", "INB/NEFT/AXODH091982", "GP2026", "INR 25,236.00", ""],
	[3, "01/04/2026", "S68517082", "1", "", "INB/RTGS/UTIBR620", "GP202", "INR 5,52,386.00", ""],
	[4, "01/04/2026", "S68543043", "1", "", "INB/RTGS/UTIBR62", "7072L", "INR 3,55,791.00", ""],
	[None, None, None, None, None, None, None, None, None],
	["Closing Balance: INR -5,89,376.74", None, None, None, None, None, None, None, None],
]
test_amount_with_currency_expected_output = {
	"number_of_transactions": 3,
	"detected_date_format": "%d/%m/%Y",
	"detected_amount_format": "Separate columns for withdrawal and deposit",
	"detected_header_index": 2,
	"detected_transaction_starting_index": 3,
	"detected_transaction_ending_index": 5,
	"closing_balance": None,
	"total_debits": 933413.00,
	"total_credits": 0,
	"total_debit_transactions": 3,
	"total_credit_transactions": 0,
	"start_date": getdate("2026-04-01"),
	"end_date": getdate("2026-04-01"),
	"column_mapping": {
		"Date": 1,
		"Description": 5,
		"Reference": 2,
		"Withdrawal": 7,
		"Deposit": 8,
	},
}
