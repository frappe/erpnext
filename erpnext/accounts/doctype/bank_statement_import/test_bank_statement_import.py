# Copyright (c) 2020, Frappe Technologies and Contributors
# See license.txt

import mt940

from erpnext.accounts.doctype.bank_statement_import.bank_statement_import import (
	get_transaction_reference,
	is_mt940_format,
	preprocess_mt940_content,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestBankStatementImport(ERPNextTestSuite):
	"""Unit tests for Bank Statement Import functions"""

	def test_preprocess_mt940_content_with_long_statement_number(self):
		"""Test that statement numbers longer than 5 digits are truncated to last 5 digits"""
		# Test case with 6-digit statement number (167619 -> 67619)
		mt940_content = ":28C:167619/1"
		expected_content = ":28C:67619/1"
		result = preprocess_mt940_content(mt940_content)
		self.assertEqual(result, expected_content)

	def test_preprocess_mt940_content_with_normal_statement_number(self):
		"""Test that statement numbers with 5 or fewer digits are unchanged"""
		# Test case with 5-digit statement number (should remain unchanged)
		mt940_content = ":28C:12345/1"
		result = preprocess_mt940_content(mt940_content)
		self.assertEqual(result, mt940_content)  # Should be unchanged

		# Test case with 4-digit statement number (should remain unchanged)
		mt940_content = ":28C:1234/1"
		result = preprocess_mt940_content(mt940_content)
		self.assertEqual(result, mt940_content)  # Should be unchanged

	def test_preprocess_mt940_content_without_sequence_number(self):
		"""Test statement number truncation without sequence number"""
		# Test case with long statement number but no sequence (no /1)
		mt940_content = ":28C:987654321"
		expected_content = ":28C:54321"
		result = preprocess_mt940_content(mt940_content)
		self.assertEqual(result, expected_content)

	def test_preprocess_mt940_content_multiple_occurrences(self):
		"""Test multiple statement numbers in the same content"""
		mt940_content = """:28C:167619/1
:28C:987654/2"""
		expected_content = """:28C:67619/1
:28C:87654/2"""
		result = preprocess_mt940_content(mt940_content)
		self.assertEqual(result, expected_content)

	def test_preprocess_mt940_content_edge_cases(self):
		"""Test edge cases like empty content and content without :28C: tags"""
		# Test empty content
		self.assertEqual(preprocess_mt940_content(""), "")

		# Test content without :28C: tags
		content_without_28c = """:20:STARTUMSE
:25:12345678901234567890
:60F:C031002EUR0,00"""
		result = preprocess_mt940_content(content_without_28c)
		self.assertEqual(result, content_without_28c)  # Should be unchanged

	def test_preprocess_mt940_content_with_full_mt940_document(self):
		"""Test preprocessing with complete MT940 document"""
		mt940_content = """:20:STARTUMSE
:25:12345678901234567890
:28C:167619/1
:60F:C031002EUR0,00
:61:0310021002DR123,45NMSCNONREF//8327000090031789
:86:806?20EREF+NONREF?21MREF+M180031?22CRED+DE98ZZZ09999999999
:62F:C031002EUR-123,45
-"""
		expected_content = """:20:STARTUMSE
:25:12345678901234567890
:28C:67619/1
:60F:C031002EUR0,00
:61:0310021002DR123,45NMSCNONREF//8327000090031789
:86:806?20EREF+NONREF?21MREF+M180031?22CRED+DE98ZZZ09999999999
:62F:C031002EUR-123,45
-"""
		result = preprocess_mt940_content(mt940_content)
		self.assertEqual(result, expected_content)

	def test_is_mt940_format_detection(self):
		"""Test MT940 format detection function"""
		# Valid MT940 content with all required tags
		valid_mt940 = """:20:STARTUMSE
:25:12345678901234567890
:28C:167619/1
:60F:C031002EUR0,00
:61:0310021002DR123,45NMSCNONREF//8327000090031789"""
		self.assertTrue(is_mt940_format(valid_mt940))

		# Invalid MT940 content (CSV format)
		invalid_mt940 = """Date,Description,Amount
2023-01-01,Test Transaction,100.00
2023-01-02,Another Transaction,-50.00"""
		self.assertFalse(is_mt940_format(invalid_mt940))

		# Partially valid MT940 (missing some required tags)
		partial_mt940 = """:20:STARTUMSE
:25:12345678901234567890
:60F:C031002EUR0,00"""
		self.assertFalse(is_mt940_format(partial_mt940))

		# Empty content
		self.assertFalse(is_mt940_format(""))

	def test_preprocess_mt940_content_boundary_conditions(self):
		"""Test boundary conditions for statement number length"""
		# Test exactly 6 digits (should be truncated)
		mt940_content = ":28C:123456/1"
		expected_content = ":28C:23456/1"
		result = preprocess_mt940_content(mt940_content)
		self.assertEqual(result, expected_content)

		# Test exactly 5 digits (should remain unchanged)
		mt940_content = ":28C:12345/1"
		result = preprocess_mt940_content(mt940_content)
		self.assertEqual(result, mt940_content)

		# Test very long statement number
		mt940_content = ":28C:123456789012345/1"
		expected_content = ":28C:12345/1"  # Last 5 digits
		result = preprocess_mt940_content(mt940_content)
		self.assertEqual(result, expected_content)

	def test_preprocess_mt940_content_real_world_case(self):
		"""Test with real-world MT940 content that was failing in production"""
		# This is based on actual MT940 content that was causing parsing errors (sanitized)
		mt940_content = """{1:F0112345678901X0000000000}{2:I94012345678901XN}{4:
:20:STMTREF167619
:25:1234567890
:28C:167619/1
:60F:C250622USD0,00
:61:2507170717C100000,00NMSCNOREF
:86:BY EXAMPLE INST 123456/03-07-25/TESTBANK/CITY
:61:2507240724C1,00NMSCNEFTINW-1234567890
:86:NEFT TEST123456789 EXAMPLE MERCHANT SERVICES
:61:2507310731D305,62NMSCTBMS-1234567890
:86:Chrg: Debit Card Annual Fee 1234 for 2025
:61:2508030803D1066,00NMSC123456789
:86:PCD/1234/EXAMPLE DOMAIN/01234567890123/23:27
:61:2508060806D2000,00NMSCUPI-123456789
:86:UPI/TEST USER/123456789/PaidViaTestApp
:61:2508140814D5000,00NMSCUPI-123456789
:86:UPI/TEST USER/123456789/PaidViaTestApp
:61:2509190919D900,00NMSCUPI-123456789
:86:UPI/EXAMPLE MERCHANT/123456789/Pay
:61:2509190919D2606,00NMSCUPI-123456789
:86:UPI/JOHN DOE/123456789/PaidViaTestApp
:62F:C250922USD88123,38
-}"""

		# Expected result with statement number 167619 truncated to 67619
		expected_content = """{1:F0112345678901X0000000000}{2:I94012345678901XN}{4:
:20:STMTREF167619
:25:1234567890
:28C:67619/1
:60F:C250622USD0,00
:61:2507170717C100000,00NMSCNOREF
:86:BY EXAMPLE INST 123456/03-07-25/TESTBANK/CITY
:61:2507240724C1,00NMSCNEFTINW-1234567890
:86:NEFT TEST123456789 EXAMPLE MERCHANT SERVICES
:61:2507310731D305,62NMSCTBMS-1234567890
:86:Chrg: Debit Card Annual Fee 1234 for 2025
:61:2508030803D1066,00NMSC123456789
:86:PCD/1234/EXAMPLE DOMAIN/01234567890123/23:27
:61:2508060806D2000,00NMSCUPI-123456789
:86:UPI/TEST USER/123456789/PaidViaTestApp
:61:2508140814D5000,00NMSCUPI-123456789
:86:UPI/TEST USER/123456789/PaidViaTestApp
:61:2509190919D900,00NMSCUPI-123456789
:86:UPI/EXAMPLE MERCHANT/123456789/Pay
:61:2509190919D2606,00NMSCUPI-123456789
:86:UPI/JOHN DOE/123456789/PaidViaTestApp
:62F:C250922USD88123,38
-}"""

		result = preprocess_mt940_content(mt940_content)
		self.assertEqual(result, expected_content)

		# Verify that the problematic statement number was actually changed
		self.assertIn(":28C:67619/1", result)
		self.assertNotIn(":28C:167619/1", result)

		# Verify that other content remains unchanged
		self.assertIn(":20:STMTREF167619", result)  # Reference should remain unchanged
		self.assertIn("UPI/TEST USER/123456789/PaidViaTestApp", result)

	def test_get_transaction_reference_uses_customer_reference(self):
		"""Per-transaction reference must come from :61: customer_reference, not :20:."""
		self.assertEqual(
			get_transaction_reference(
				{"customer_reference": "UPI-100000000001", "transaction_reference": "STMTREF12345"}
			),
			"UPI-100000000001",
		)

	def test_get_transaction_reference_rejoins_overflow(self):
		"""When a bank emits a single-line :61: with >16-char reference, the regex
		splits the tail into extra_details. We must rejoin them."""
		self.assertEqual(
			get_transaction_reference(
				{
					"customer_reference": "NEFTINW-12345678",
					"extra_details": "90",
					"transaction_reference": "STMTREF12345",
				}
			),
			"NEFTINW-1234567890",
		)

	def test_get_transaction_reference_falls_back_to_bank_reference_on_nonref(self):
		"""NONREF is the MT940 'no customer reference' sentinel; prefer bank_reference."""
		self.assertEqual(
			get_transaction_reference(
				{
					"customer_reference": "NONREF",
					"bank_reference": "1234567890123456",
					"transaction_reference": "STMTREF12345",
				}
			),
			"1234567890123456",
		)

	def test_get_transaction_reference_falls_back_to_bank_reference_on_nonref_with_extra_details(self):
		"""NONREF sentinel must trigger the bank_reference fallback even when
		extra_details is populated. Without the 16-char gate, the old naive concat
		would produce a junk reference like 'NONREFsome info' and bypass the check."""
		self.assertEqual(
			get_transaction_reference(
				{
					"customer_reference": "NONREF",
					"extra_details": "some info",
					"bank_reference": "1234567890123456",
					"transaction_reference": "STMTREF12345",
				}
			),
			"1234567890123456",
		)

	def test_get_transaction_reference_does_not_append_extra_details_below_16_chars(self):
		"""When customer_reference is below the 16-char cap, extra_details is a
		genuine supplementary-info field from :61: — not overflow — and must not
		be appended to the reference."""
		self.assertEqual(
			get_transaction_reference(
				{
					"customer_reference": "TBMS-123456789",
					"extra_details": "note field",
					"transaction_reference": "STMTREF12345",
				}
			),
			"TBMS-123456789",
		)

	def test_get_transaction_reference_keeps_noref_literal(self):
		"""Bare 'NOREF' (without bank_reference) stays as-is; still better than the
		statement-level reference which is identical across all transactions."""
		self.assertEqual(
			get_transaction_reference(
				{
					"customer_reference": "NOREF",
					"bank_reference": None,
					"transaction_reference": "STMTREF12345",
				}
			),
			"NOREF",
		)

	def test_mt940_parse_per_transaction_reference_mapping(self):
		"""End-to-end: every transaction in a statement must get its own distinct
		reference from :61: customer_reference, never the statement-level :20: reference."""
		mt940_content = """{1:F0112345678901X0000000000}{2:I94012345678901XN}{4:
:20:STMTREF12345
:25:1234567890
:28C:12345/1
:60F:C250716INR88123,38
:61:2509280928D5000,00NMSCUPI-100000000001
:86:UPI/TEST PAYEE ONE/111111111111/TestApp
:61:2509190919D2606,00NMSCUPI-100000000002
:86:UPI/TEST PAYEE TWO/222222222222/TestApp
:61:2509190919D900,00NMSCUPI-100000000003
:86:UPI/TEST PAYEE THREE/333333333333/TestApp
:61:2508140814D5000,00NMSCUPI-100000000004
:86:UPI/TEST PAYEE FOUR/444444444444/TestApp
:61:2508060806D2000,00NMSCUPI-100000000005
:86:UPI/TEST PAYEE FIVE/555555555555/TestApp
:61:2508030803D1066,00NMSC123456789012
:86:PCD/1234/TEST MERCHANT/01234567890123/12:00
:61:2507310731D305,62NMSCTBMS-123456789
:86:Chrg: Debit Card Annual Fee 1234 for 2025
:61:2507240724C1,00NMSCNEFTINW-1234567890
:86:NEFT TEST123456789 TEST SERVICES
:61:2507170717C100000,00NMSCNOREF
:86:BY CLG INST 123456/01-01-25/TESTBANK/TESTCITY
:62F:C250930INR100000,00
-}"""
		transactions = list(mt940.parse(preprocess_mt940_content(mt940_content)))
		references = [get_transaction_reference(t.data) for t in transactions]

		self.assertEqual(
			references,
			[
				"UPI-100000000001",
				"UPI-100000000002",
				"UPI-100000000003",
				"UPI-100000000004",
				"UPI-100000000005",
				"123456789012",
				"TBMS-123456789",
				"NEFTINW-1234567890",
				"NOREF",
			],
		)
		# No transaction should carry the statement-level reference from :20:
		self.assertNotIn("STMTREF12345", references)

	def test_preprocess_mt940_content_whitespace_variants(self):
		"""Test handling of whitespace and different line endings"""
		# Test with trailing spaces
		mt940_content = ":28C:167619/1   \n"
		expected_content = ":28C:67619/1   \n"
		result = preprocess_mt940_content(mt940_content)
		self.assertEqual(result, expected_content)

		# Test with Windows line endings (CRLF)
		mt940_content = ":28C:167619/1\r\n"
		expected_content = ":28C:67619/1\r\n"
		result = preprocess_mt940_content(mt940_content)
		self.assertEqual(result, expected_content)

		# Test with leading spaces (should not match as it's not line start)
		mt940_content = "   :28C:167619/1\n"
		result = preprocess_mt940_content(mt940_content)
		self.assertEqual(result, mt940_content)  # Should remain unchanged
