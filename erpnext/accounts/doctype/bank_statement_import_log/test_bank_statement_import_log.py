# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe import qb
from frappe.utils import getdate

from erpnext.accounts.doctype.bank_statement_import_log.bank_statement_import_log import (
	BankStatementImportLog,
	build_table_transactions,
	detect_column_mapping,
	detect_header_row,
	extract_pdf_tables,
	get_amount_cr_dr_marker,
	get_float_amount,
	get_statement_details,
	guess_column_mapping_by_content,
	reextract_pdf_table,
	set_header_index,
	set_pdf_table_header,
	should_include_table,
	update_column_mapping,
	update_pdf_tables,
)
from erpnext.accounts.test.accounts_mixin import AccountsTestMixin
from erpnext.tests.utils import ERPNextTestSuite


class TestBankStatementImportLog(ERPNextTestSuite, AccountsTestMixin):
	def setUp(self):
		self.company = "_Test Company"
		self.customer = "_Test Customer"
		self.bank = "HDFC - _TC"
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

	# ------------------------------------------------------------------ #
	# Amount format detection
	# ------------------------------------------------------------------ #

	def test_amount_cr_dr_marker(self):
		"""The marker is read at either end of the cell, but only next to the amount."""
		for amount in ("2,378.00Cr", "50.90 CR", "INR 50.90 Cr.", "1000cr", "5cr", "(100) Cr"):
			self.assertEqual(get_amount_cr_dr_marker(amount), "cr", amount)

		for amount in ("2,378.00Dr", "50.90 DR", "1000dr", "-100 Dr"):
			self.assertEqual(get_amount_cr_dr_marker(amount), "dr", amount)

		# Some banks put the marker in front of the digits instead.
		for amount in ("Cr 100", "Cr100", "CR INR 100", "cr 0.00"):
			self.assertEqual(get_amount_cr_dr_marker(amount), "cr", amount)

		for amount in ("Dr 100", "Dr100", "Dr. 1,234.50"):
			self.assertEqual(get_amount_cr_dr_marker(amount), "dr", amount)

		for amount in ("100.00", "-2,000.00", "INR 25,236.00", "", None, 100.0):
			self.assertIsNone(get_amount_cr_dr_marker(amount), amount)

		# Text that merely starts or ends with the letters must not be read as a marker, or
		# a description that bled into the amount column would reclassify the statement.
		for amount in (
			"CREDIT CARD PAYMENT 500",
			"DRAFT 100",
			"Dr Smith Clinic 500",
			"DR AMBEDKAR ROAD BRANCH 500",
			"500 CRC",
			"Cheque Dr",
			"Cr",
		):
			self.assertIsNone(get_amount_cr_dr_marker(amount), amount)

	def test_sparsely_marked_cr_dr_amount_column(self):
		"""One marker is enough to prove a CR/DR amount column - it is not a majority vote.

		A real HDFC credit-card page carries 18 rows and a single "50.90Cr": the unmarked
		rows are ordinary purchases, and only the exceptions are marked. A frequency vote
		therefore picked "positive/negative" 17-1 and imported that lone credit as a debit.
		"""
		doc = self._create_bank_statement_import_log(
			[
				["Date", "Transaction Description", "Amount (in Rs.)"],
				["21/07/2026", "ITC MAURYA NEW DELHI", "2,495.00"],
				["22/07/2026", "ZOMATO LIMITED Gurugram", "1,288.68"],
				["23/07/2026", "SWIGGY Bangalore", "532.00"],
				["26/07/2026", "SWIGGY Bangalore", "1,043.00"],
				["27/07/2026", "PETRO SURCHARGE WAIVER", "50.90Cr"],
			]
		)

		self.assertEqual(doc.detected_amount_format, 'Amount column has "CR"/"DR" values')
		# Only "Cr" appears, so it is the marked exception and unmarked rows are debits.
		self.assertEqual(doc.total_credits, 50.90)
		self.assertEqual(doc.total_credit_transactions, 1)
		self.assertEqual(doc.total_debits, 5358.68)
		self.assertEqual(doc.total_debit_transactions, 4)

	def test_dr_only_statement_treats_unmarked_rows_as_deposits(self):
		"""The mirror image of a Cr-only statement: only withdrawals are marked.

		The unmarked default cannot be hardcoded to the debit, because which side gets
		marked varies by bank. It is derived from the markers the statement actually uses -
		here only "Dr" appears, so "Dr" is the exception and everything unmarked is a
		deposit.
		"""
		doc = self._create_bank_statement_import_log(
			[
				["Date", "Narration", "Amount"],
				["01/04/2026", "ATM WITHDRAWAL", "2,000.00Dr"],
				["03/04/2026", "SALARY", "20,000.00"],
				["05/04/2026", "INTEREST", "150.00"],
			]
		)

		self.assertEqual(doc.detected_amount_format, 'Amount column has "CR"/"DR" values')
		self.assertEqual(doc.total_debits, 2000.0)
		self.assertEqual(doc.total_debit_transactions, 1)
		self.assertEqual(doc.total_credits, 20150.0)
		self.assertEqual(doc.total_credit_transactions, 2)

	def test_leading_cr_dr_markers(self):
		"""Some banks print the marker in front of the amount."""
		doc = self._create_bank_statement_import_log(
			[
				["Date", "Narration", "Amount"],
				["01/04/2026", "ATM WITHDRAWAL", "Dr 2,000.00"],
				["03/04/2026", "SALARY", "Cr 20,000.00"],
			]
		)

		self.assertEqual(doc.detected_amount_format, 'Amount column has "CR"/"DR" values')
		self.assertEqual(doc.total_debits, 2000.0)
		self.assertEqual(doc.total_credits, 20000.0)

	def test_partially_marked_cr_dr_amount_column(self):
		"""A CR/DR amount column stays CR/DR even when some rows carry no marker.

		Every unmarked row used to also vote for "positive/negative", so an ordinary
		statement with a few unmarked rows was detected as positive/negative and a
		"2000.00Dr" was then imported as a deposit.
		"""
		doc = self._create_bank_statement_import_log(
			[
				["Date", "Narration", "Amount", "Balance"],
				["01/04/2026", "OPENING FEE", "100.00", "9,900.00"],
				["03/04/2026", "SALARY", "20000.00Cr", "29,900.00"],
				["05/04/2026", "ATM WDL", "2000.00Dr", "27,900.00"],
			]
		)

		self.assertEqual(doc.detected_amount_format, 'Amount column has "CR"/"DR" values')
		# Both markers appear, so an unmarked row is undetermined and stays a debit.
		self.assertEqual(doc.total_debits, 2100.0)
		self.assertEqual(doc.total_debit_transactions, 2)
		self.assertEqual(doc.total_credits, 20000.0)
		self.assertEqual(doc.total_credit_transactions, 1)

	def test_deposit_withdrawal_type_column(self):
		"""The word Withdrawal contains "dr", so a loose CR/DR check claims this column first.

		It then reads "Deposit" (which has no "cr" in it) as a withdrawal, flipping the
		direction of every credit in the statement.
		"""
		doc = self._create_bank_statement_import_log(
			[
				["Date", "Narration", "Transaction Type", "Amount"],
				["01/04/2026", "ATM WDL", "Withdrawal", "2,000.00"],
				["03/04/2026", "SALARY", "Deposit", "20,000.00"],
				["05/04/2026", "ATM WDL", "Withdrawal", "500.00"],
			]
		)

		self.assertEqual(
			doc.detected_amount_format, 'Transaction type column has "Deposit"/"Withdrawal" values'
		)
		self.assertEqual(doc.total_debits, 2500.0)
		self.assertEqual(doc.total_debit_transactions, 2)
		self.assertEqual(doc.total_credits, 20000.0)
		self.assertEqual(doc.total_credit_transactions, 1)

	def test_unrecognised_type_column_falls_back_to_signed_amount(self):
		"""An unrecognised transaction type must not stop the amount being read.

		No tally was incremented for these rows, so max() returned the first key -
		"Separate columns for withdrawal and deposit" - and, with no such columns in the
		file, every amount came through as None.
		"""
		doc = self._create_bank_statement_import_log(
			[
				["Date", "Narration", "Transaction Type", "Amount"],
				["01/04/2026", "ATM WDL", "NEFT", "-2,000.00"],
				["03/04/2026", "SALARY", "IMPS", "20,000.00"],
			]
		)

		self.assertEqual(doc.detected_amount_format, "Amount column has positive/negative values")
		self.assertEqual(doc.total_debits, 2000.0)
		self.assertEqual(doc.total_credits, 20000.0)

	def test_blank_transaction_type_cell(self):
		"""A blank type cell used to raise - `None.lower()` - instead of parsing the row."""
		doc = self._create_bank_statement_import_log(
			[
				["Date", "Narration", "Transaction Type", "Amount"],
				["01/04/2026", "ATM WDL", "Dr", "2,000.00"],
				["03/04/2026", "SALARY", "Cr", "20,000.00"],
				["05/04/2026", "UNKNOWN", None, "500.00"],
			]
		)

		self.assertEqual(doc.detected_amount_format, 'Transaction type column has "CR"/"DR" values')
		# The unmarked row has no direction of its own, so it counts as a withdrawal.
		self.assertEqual(doc.total_debits, 2500.0)
		self.assertEqual(doc.total_credits, 20000.0)

	# ------------------------------------------------------------------ #
	# PDF statement import
	# ------------------------------------------------------------------ #

	@staticmethod
	def _make_pdf(html: str) -> bytes:
		import pdfkit

		return pdfkit.from_string(html, False)

	@staticmethod
	def _encrypt(pdf_bytes: bytes, password: str) -> bytes:
		import io

		from pypdf import PdfReader, PdfWriter

		reader = PdfReader(io.BytesIO(pdf_bytes))
		writer = PdfWriter()
		for page in reader.pages:
			writer.add_page(page)
		writer.encrypt(password)
		buffer = io.BytesIO()
		writer.write(buffer)
		return buffer.getvalue()

	@staticmethod
	def _auto_map(table: dict) -> dict:
		"""Mimic prepare_pdf_tables' best-effort mapping for a single extracted table."""
		header_index, score = detect_header_row(table["rows"])
		if score >= 2:
			table["header_index"] = header_index
			table["column_mapping"] = detect_column_mapping(table["rows"][header_index])
		else:
			table["header_index"] = None
			table["column_mapping"] = guess_column_mapping_by_content(table["rows"])
		final_transactions, _df, _af = build_table_transactions(table)
		table["included"] = should_include_table(table, final_transactions)
		return table

	def test_pdf_multi_page_kept_separate_and_unioned(self):
		"""Tables on separate pages must NOT be merged; transactions are the union."""
		html = """
		<html><body>
		<table border="1"><tr><th>Date</th><th>Narration</th><th>Withdrawal</th><th>Deposit</th><th>Balance</th></tr>
		<tr><td>01/04/2024</td><td>UPI PAYMENT</td><td>500.00</td><td></td><td>9500.00</td></tr>
		<tr><td>03/04/2024</td><td>SALARY</td><td></td><td>20000.00</td><td>29500.00</td></tr></table>
		<div style="page-break-before: always"></div>
		<table border="1"><tr><th>Date</th><th>Narration</th><th>Withdrawal</th><th>Deposit</th><th>Balance</th></tr>
		<tr><td>05/04/2024</td><td>ATM WDL</td><td>2000.00</td><td></td><td>27500.00</td></tr></table>
		</body></html>
		"""
		tables = extract_pdf_tables(self._make_pdf(html))

		# Two separate tables, one per page
		self.assertEqual(len(tables), 2)
		self.assertEqual(sorted(t["page"] for t in tables), [1, 2])
		for table in tables:
			self.assertIn("bbox", table)
			self.assertEqual(len(table["bbox"]), 4)

		union = []
		for table in tables:
			final, _df, _af = build_table_transactions(self._auto_map(table))
			union.extend(final)

		self.assertEqual(len(union), 3)
		self.assertEqual(sorted(t["date"] for t in union), ["2024-04-01", "2024-04-03", "2024-04-05"])

	def test_pdf_junk_table_excluded(self):
		"""A non-transactions table (ad/summary) should yield zero transactions."""
		ad_table = self._auto_map({"rows": [["Open a new account!", "Call 1800-XYZ"]]})
		final, _df, _af = build_table_transactions(ad_table)
		self.assertEqual(final, [])

	def test_pdf_summary_box_not_auto_included(self):
		"""A summary box that happens to parse as one transaction must not start included.

		The "Payment Due Date / Total Dues / Minimum Amount Due" block on an HDFC
		credit-card statement has a date column and a figures column, so it yields a single
		transaction - the due date and the minimum amount - and used to import as a phantom
		row. What it does not have, and a real transaction table always does, is a narration.
		"""
		summary_box = {
			"header_index": 1,
			"rows": [
				["Statement Date:17/08/2025", "Card No: 4341 55XX XXXX 2754", ""],
				["Payment Due Date", "Total Dues", "Minimum Amount Due"],
				["06/09/2025", "73,200.00", "3,660.00"],
				["Credit Limit", "Available Credit Limit", "Available Cash Limit"],
				["", "32,800", ""],
			],
			"column_mapping": [
				{"index": 0, "header_text": "Payment Due Date", "variable": "a", "maps_to": "Date"},
				{"index": 1, "header_text": "Total Dues", "variable": "b", "maps_to": "Do not import"},
				{"index": 2, "header_text": "Minimum Amount Due", "variable": "c", "maps_to": "Amount"},
			],
		}

		final, _df, _af = build_table_transactions(summary_box)
		# It really does parse as a transaction - that is why the previous check missed it.
		self.assertEqual(len(final), 1)
		self.assertFalse(should_include_table(summary_box, final))

		# The transaction table beside it, which does carry a narration, still starts included.
		transactions = self._auto_map(
			{
				"rows": [
					["Date", "Transaction Description", "Amount (in Rs.)"],
					["21/07/2025", "ITC MAURYA NEW DELHI", "2,495.00"],
					["27/07/2025", "PETRO SURCHARGE WAIVER", "50.90Cr"],
				]
			}
		)
		self.assertTrue(transactions["included"])

	def test_pdf_table_without_description_still_importable(self):
		"""No narration column means "starts unticked", NOT "cannot be imported".

		`description` is not mandatory on Bank Transaction, so a bank that omits narration
		must still import once the user ticks the table.
		"""
		table = {
			"header_index": 0,
			"rows": [
				["Date", "Amount", "Balance"],
				["01/04/2025", "500.00", "9,500.00"],
				["03/04/2025", "20000.00", "29,500.00"],
			],
			"column_mapping": [
				{"index": 0, "header_text": "Date", "variable": "a", "maps_to": "Date"},
				{"index": 1, "header_text": "Amount", "variable": "b", "maps_to": "Amount"},
				{"index": 2, "header_text": "Balance", "variable": "c", "maps_to": "Balance"},
			],
		}

		final, _df, _af = build_table_transactions(table)
		self.assertFalse(should_include_table(table, final))

		# The transactions themselves are intact and importable.
		self.assertEqual(len(final), 2)
		self.assertEqual([t["date"] for t in final], ["2025-04-01", "2025-04-03"])

	def test_headerless_content_mapping(self):
		"""Without a header row, columns are guessed from their contents."""
		rows = [
			["01/04/2024", "UPI PAYMENT", "500.00"],
			["03/04/2024", "SALARY CREDIT", "20000.00"],
		]
		mapping = {
			c["maps_to"]: c["index"]
			for c in guess_column_mapping_by_content(rows)
			if c["maps_to"] != "Do not import"
		}
		self.assertEqual(mapping.get("Date"), 0)
		self.assertEqual(mapping.get("Description"), 1)
		self.assertEqual(mapping.get("Amount"), 2)

	def test_pdf_password_protected(self):
		"""Encrypted PDFs error without a password and succeed with the right one."""
		html = """
		<html><body><table border="1">
		<tr><th>Date</th><th>Narration</th><th>Amount</th></tr>
		<tr><td>01/04/2024</td><td>UPI PAYMENT</td><td>500.00</td></tr></table></body></html>
		"""
		encrypted = self._encrypt(self._make_pdf(html), "secret123")

		# No / wrong password -> recognizable error
		self.assertRaises(frappe.ValidationError, extract_pdf_tables, encrypted)
		self.assertRaises(frappe.ValidationError, extract_pdf_tables, encrypted, "wrong")

		# Correct password -> extracts
		tables = extract_pdf_tables(encrypted, "secret123")
		self.assertTrue(tables)

	def test_pdf_no_tables_detected(self):
		"""A PDF with no detectable tables raises a clear error (e.g. scanned PDFs)."""
		html = "<html><body><p>Just some prose with no tabular data at all.</p></body></html>"
		self.assertRaises(frappe.ValidationError, extract_pdf_tables, self._make_pdf(html))

	def _create_pdf_import_log(self, html: str) -> BankStatementImportLog:
		pdf_bytes = self._make_pdf(html)
		file_doc = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": f"test-statement-{frappe.generate_hash(length=8)}.pdf",
				"is_private": 1,
				"content": pdf_bytes,
			}
		).insert(ignore_permissions=True)

		doc = frappe.get_doc(
			{
				"doctype": "Bank Statement Import Log",
				"name": f"test-pdf-{frappe.generate_hash(length=8)}",
				"bank_account": self.bank_account,
				"file": file_doc.file_url,
			}
		)
		return doc.insert()

	def test_pdf_full_lifecycle(self):
		"""End-to-end doc lifecycle: insert -> rasterize -> preview -> edit -> import."""
		html = """
		<html><body>
		<table border="1"><tr><th>Date</th><th>Narration</th><th>Withdrawal</th><th>Deposit</th><th>Balance</th></tr>
		<tr><td>01/04/2024</td><td>UPI PAYMENT</td><td>500.00</td><td></td><td>9500.00</td></tr>
		<tr><td>03/04/2024</td><td>SALARY</td><td></td><td>20000.00</td><td>29500.00</td></tr></table>
		<div style="page-break-before: always"></div>
		<table border="1"><tr><th>Date</th><th>Narration</th><th>Withdrawal</th><th>Deposit</th><th>Balance</th></tr>
		<tr><td>05/04/2024</td><td>ATM WDL</td><td>2000.00</td><td></td><td>27500.00</td></tr></table>
		</body></html>
		"""
		doc = self._create_pdf_import_log(html)

		# before_insert populated the per-table JSON, page images and the union summary
		tables = doc.get_pdf_tables()
		self.assertEqual(len(tables), 2)
		for table in tables:
			self.assertTrue(table.get("page_image"))
			self.assertIn("bbox", table)
			# Page-image File must be attached to the final docname, not the client's temp id
			attached_to = frappe.db.get_value("File", {"file_url": table["page_image"]}, "attached_to_name")
			self.assertEqual(attached_to, doc.name)
		self.assertEqual(doc.number_of_transactions, 3)
		self.assertEqual(doc.total_debit_transactions, 2)
		self.assertEqual(doc.total_credit_transactions, 1)

		# get_statement_details returns the union and the per-table data for the editor
		details = get_statement_details(doc.name)
		self.assertEqual(len(details["final_transactions"]), 3)
		self.assertEqual(details["raw_data"], [])
		self.assertEqual(len(details["pdf_tables"]), 2)

		# Excluding the second table (page 2) drops its single transaction
		tables[1]["included"] = False
		update_pdf_tables(doc.name, tables)
		doc.reload()
		self.assertEqual(doc.number_of_transactions, 2)

		# Re-include and import; transactions are created for the union
		tables[1]["included"] = True
		update_pdf_tables(doc.name, tables)
		doc.reload()
		doc.insert_transactions()
		doc.reload()
		self.assertEqual(doc.status, "Completed")

		created = frappe.get_all(
			"Bank Transaction", filters={"bank_account": self.bank_account, "docstatus": 1}
		)
		self.assertEqual(len(created), 3)

	def test_pdf_reextract_table_from_bbox(self):
		"""Re-extracting a table from an adjusted bbox updates its rows and stores the bbox."""
		html = """
		<html><body>
		<table border="1"><tr><th>Date</th><th>Narration</th><th>Amount</th></tr>
		<tr><td>01/04/2024</td><td>UPI PAYMENT</td><td>500.00</td></tr>
		<tr><td>03/04/2024</td><td>SALARY</td><td>20000.00</td></tr></table>
		</body></html>
		"""
		doc = self._create_pdf_import_log(html)
		table = doc.get_pdf_tables()[0]
		bbox = table["bbox"]

		details = reextract_pdf_table(doc.name, table["page"], table["table_index"], bbox)
		updated = details["pdf_tables"][0]

		# Same region -> same rows; bbox is persisted
		self.assertTrue(updated["rows"])
		self.assertEqual(updated["bbox"], [round(float(v), 2) for v in bbox])
		self.assertEqual(updated["rows"], table["rows"])

	def test_pdf_reextract_changed_bbox_updates_rows_and_transactions(self):
		"""Shrinking a table's bbox must drop rows and update the transaction count end-to-end."""
		html = """
		<html><body>
		<table border="1"><tr><th>Date</th><th>Narration</th><th>Amount</th></tr>
		<tr><td>01/04/2024</td><td>UPI PAYMENT</td><td>500.00</td></tr>
		<tr><td>03/04/2024</td><td>SALARY</td><td>20000.00</td></tr>
		<tr><td>05/04/2024</td><td>ATM WDL</td><td>2000.00</td></tr>
		<tr><td>07/04/2024</td><td>INTEREST</td><td>12.50</td></tr></table>
		</body></html>
		"""
		doc = self._create_pdf_import_log(html)
		original = doc.get_pdf_tables()[0]
		original_rows = len(original["rows"])
		original_txns = doc.number_of_transactions

		# Shrink the box to roughly the top half (simulating a user drag).
		x0, top, x1, bottom = original["bbox"]
		shrunk = [x0, top, x1, top + (bottom - top) * 0.5]

		details = reextract_pdf_table(doc.name, original["page"], original["table_index"], shrunk)
		updated = details["pdf_tables"][0]
		doc.reload()

		self.assertLess(len(updated["rows"]), original_rows)
		self.assertLess(doc.number_of_transactions, original_txns)
		self.assertEqual(len(details["final_transactions"]), doc.number_of_transactions)

	def test_pdf_set_table_header(self):
		"""User can clear a table's header (no header row) or set a specific header row."""
		html = """
		<html><body>
		<table border="1"><tr><th>Date</th><th>Narration</th><th>Amount</th></tr>
		<tr><td>01/04/2024</td><td>UPI PAYMENT</td><td>500.00</td></tr>
		<tr><td>03/04/2024</td><td>SALARY</td><td>20000.00</td></tr></table>
		</body></html>
		"""
		doc = self._create_pdf_import_log(html)
		table = doc.get_pdf_tables()[0]
		self.assertEqual(table["header_index"], 0)
		original = {
			c["maps_to"]: c["index"] for c in table["column_mapping"] if c["maps_to"] != "Do not import"
		}

		# Clear the header (-1): header is removed but the mapping is preserved (not re-guessed).
		details = set_pdf_table_header(doc.name, table["page"], table["table_index"], -1)
		updated = details["pdf_tables"][0]
		self.assertIsNone(updated["header_index"])
		preserved = {
			c["maps_to"]: c["index"] for c in updated["column_mapping"] if c["maps_to"] != "Do not import"
		}
		self.assertEqual(preserved, original)

		# Set row 0 back as the header: it resolves meaningfully, so mapping is re-derived.
		details = set_pdf_table_header(doc.name, table["page"], table["table_index"], 0)
		updated = details["pdf_tables"][0]
		self.assertEqual(updated["header_index"], 0)
		mapped = {
			c["maps_to"]: c["index"] for c in updated["column_mapping"] if c["maps_to"] != "Do not import"
		}
		self.assertEqual(mapped.get("Date"), 0)
		self.assertEqual(mapped.get("Description"), 1)

	# ------------------------------------------------------------------ #
	# CSV/XLSX column mapping + header overrides
	# ------------------------------------------------------------------ #

	def _create_csv_import_log(self, csv_text: str) -> BankStatementImportLog:
		file_doc = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": f"test-statement-{frappe.generate_hash(length=8)}.csv",
				"is_private": 1,
				"content": csv_text,
			}
		).insert(ignore_permissions=True)

		doc = frappe.get_doc(
			{
				"doctype": "Bank Statement Import Log",
				"bank_account": self.bank_account,
				"file": file_doc.file_url,
			}
		)
		return doc.insert()

	def test_csv_update_column_mapping(self):
		"""Overriding the column mapping recomputes the transaction count."""
		csv_text = "Date,Narration,Amount\n01/04/2024,UPI PAYMENT,500.00\n03/04/2024,SALARY,20000.00\n"
		doc = self._create_csv_import_log(csv_text)
		self.assertEqual(doc.number_of_transactions, 2)

		# Drop the amount column -> no amount -> no transactions detected.
		mapping = [
			{"index": c.index, "maps_to": "Do not import" if c.maps_to == "Amount" else c.maps_to}
			for c in doc.column_mapping
		]
		details = update_column_mapping(doc.name, mapping)
		doc.reload()
		self.assertEqual(doc.number_of_transactions, 0)
		self.assertEqual(len(details["final_transactions"]), 0)

	def test_csv_set_header_index_preserves_mapping(self):
		"""Clearing the header keeps the user's mapping; it is not re-guessed."""
		csv_text = "Date,Narration,Amount\n01/04/2024,UPI PAYMENT,500.00\n03/04/2024,SALARY,20000.00\n"
		doc = self._create_csv_import_log(csv_text)
		self.assertEqual(doc.detected_header_index, 0)

		# Manually map the Narration column (1) as Reference.
		mapping = [
			{
				"index": c.index,
				"maps_to": "Reference" if c.index == 1 else c.maps_to,
				"header_text": c.header_text,
			}
			for c in doc.column_mapping
		]
		update_column_mapping(doc.name, mapping)
		doc.reload()

		# Clear the header row: the manual mapping must be preserved (column 1 stays Reference,
		# not re-guessed to Description). The label row fails date parsing, so 2 transactions remain.
		set_header_index(doc.name, -1)
		doc.reload()
		self.assertEqual(doc.detected_header_index, -1)
		self.assertEqual(doc.number_of_transactions, 2)
		current = {c.index: c.maps_to for c in doc.column_mapping}
		self.assertEqual(current.get(1), "Reference")

		# Restore row 0 as the header (resolves meaningfully -> re-derived from labels).
		set_header_index(doc.name, 0)
		doc.reload()
		self.assertEqual(doc.detected_header_index, 0)
		restored = {c.maps_to: c.index for c in doc.column_mapping if c.maps_to != "Do not import"}
		self.assertEqual(restored.get("Description"), 1)


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
