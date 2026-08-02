# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from erpnext.tests.utils import ERPNextTestSuite


def max_of(values):
	rows = " UNION ALL ".join(f"SELECT {frappe.db.escape(value)} AS v" for value in values)
	return frappe.db.sql(f"SELECT MAX(v) FROM ({rows}) t")[0][0]


class TestTextCollationParity(ERPNextTestSuite):
	"""Does MAX() over text pick the same value on MariaDB and PostgreSQL?

	The PostgreSQL parity effort wrapped many descriptive text columns in Max() to satisfy strict
	GROUP BY, on the reasoning that Max() returns the value MariaDB picked arbitrarily. Where the
	column genuinely varies within its group that reasoning does not hold: Max() over text is a
	sort, and the two engines sort text by different rules.

	These expectations are MariaDB's (utf8mb4 case-insensitive collation: case folded, punctuation
	and spaces significant). A failure on the PostgreSQL job means the Max()-over-varying-text
	sites are a live parity gap, not only a row-coherence one.
	"""

	def test_case_is_folded_not_byte_ordered(self):
		self.assertEqual(max_of(["apple", "Banana", "cherry"]), "cherry")
		self.assertEqual(max_of(["abc", "ABD"]), "ABD")

	def test_punctuation_and_space_are_significant(self):
		# glibc en_US.UTF-8 ignores punctuation at the primary level and would answer "ITEM-C";
		# MariaDB compares '-' (0x2D) against 'B' (0x42) and answers "ITEMB"
		self.assertEqual(max_of(["ITEM-C", "ITEMB"]), "ITEMB")
		self.assertEqual(max_of(["Stores - TC", "StoresbTC"]), "StoresbTC")
