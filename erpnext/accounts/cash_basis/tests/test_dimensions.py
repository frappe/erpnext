# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Accounting dimensions on the cash basis rows of deferred items (open point 14).

A deferred row of the invoice matches its item by cost center, project and each enabled
accounting dimension. The recognition rows then keep the dimension of the item.
"""

import frappe

from erpnext.accounts.cash_basis.tests.cash_basis_case import CashBasisTestCase
from erpnext.accounts.cash_basis.tests.fixtures import acc
from erpnext.accounts.cash_basis.tests.vouchers import line, make_sales_invoice, pay

SALES = acc("Sales")
SERVICE = acc("Service")
DEFERRED = acc("Deferred Revenue")
SCHEDULE = {"service_start_date": "2026-03-01", "service_end_date": "2026-05-31"}
RECOGNITION = "Cash basis: recognition"


def deferred_line(amount, account, **extra):
	return line(
		amount,
		account=account,
		enable_deferred_revenue=1,
		deferred_revenue_account=DEFERRED,
		**SCHEDULE,
		**extra,
	)


def make_value(doctype, name, field):
	if not frappe.db.exists(doctype, name):
		frappe.get_doc({"doctype": doctype, field: name}).insert()
	return name


class DimensionCase(CashBasisTestCase):
	def recognised(self, to_date, field):
		"""The recognised income by account and dimension value."""
		totals = {}
		for row in self.adjustments(to_date):
			if row["remarks"] == RECOGNITION and row["account"] in (SALES, SERVICE):
				key = (row["account"], row.get(field))
				totals[key] = totals.get(key, 0) + row["credit"] - row["debit"]
		return totals

	def make_paid_invoice(self, first, second, **fields):
		# 60 on Sales and 40 on Service, both deferred; 50 paid on 10 April.
		invoice = make_sales_invoice(
			"2026-03-01", [deferred_line(60, SALES, **first), deferred_line(40, SERVICE, **second)], **fields
		)
		pay(invoice, "2026-04-10", 50)
		return invoice


class TestCashBasisDimensions(DimensionCase):
	"""Branch is an enabled accounting dimension of the test site."""

	def setUp(self):
		super().setUp()
		self.north = make_value("Branch", "_Test Cash Basis North", "branch")
		self.south = make_value("Branch", "_Test Cash Basis South", "branch")

	def test_enabled_dimension_on_the_items(self):
		# Two deferred rows, one for each branch. Each matches only its own item.
		self.make_paid_invoice({"branch": self.north}, {"branch": self.south})
		self.assertEqual(self.exception_reasons(), {})
		self.assertEqual(
			self.recognised("2026-04-30", "branch"), {(SALES, self.north): 30, (SERVICE, self.south): 20}
		)
		self.assert_invariants("2026-04-30")

	def test_dimension_of_the_invoice(self):
		# The items have no branch, so their GL rows take the branch of the invoice.
		self.make_paid_invoice({}, {}, branch=self.north)
		self.assertEqual(self.exception_reasons(), {})
		self.assertEqual(
			self.recognised("2026-04-30", "branch"), {(SALES, self.north): 30, (SERVICE, self.north): 20}
		)
		self.assert_invariants("2026-04-30")

	def test_disabled_dimension_is_left_out(self):
		# A disabled dimension is not on the GL rows. The two items share one deferred row, which
		# is split between the income accounts by the item amounts.
		frappe.db.set_value("Accounting Dimension", "Branch", "disabled", 1)
		invoice = self.make_paid_invoice({"branch": self.north}, {"branch": self.south})
		self.assertFalse(
			frappe.db.get_value("GL Entry", {"voucher_no": invoice.name, "account": DEFERRED}, "branch")
		)
		self.assertEqual(self.exception_reasons(), {})
		self.assertEqual(self.recognised("2026-04-30", "branch"), {(SALES, None): 30, (SERVICE, None): 20})
		self.assert_invariants("2026-04-30")

	def test_dimension_disabled_after_posting(self):
		# The GL rows keep the branches, but the match leaves out a disabled dimension: each
		# deferred row is split between both items. The totals by account stay correct.
		self.make_paid_invoice({"branch": self.north}, {"branch": self.south})
		frappe.db.set_value("Accounting Dimension", "Branch", "disabled", 1)
		self.assertEqual(self.exception_reasons(), {})
		totals = {}
		for (account, _branch), amount in self.recognised("2026-04-30", "branch").items():
			totals[account] = totals.get(account, 0) + amount
		self.assertEqual(totals, {SALES: 30, SERVICE: 20})
		self.assert_invariants("2026-04-30")


class TestCashBasisNewDimension(DimensionCase):
	"""A dimension created by the user adds a custom field to the accounting doctypes.

	The custom fields change the tables, so the dimension is made once for the class and deleted
	after it.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.db.delete("Accounting Dimension", {"document_type": "Designation"})
		cls.dimension = frappe.get_doc(
			{"doctype": "Accounting Dimension", "document_type": "Designation"}
		).insert()
		# The custom fields change the tables, which commits on MariaDB. Commit on Postgres too.
		frappe.db.commit()  # nosemgrep

	@classmethod
	def tearDownClass(cls):
		frappe.delete_doc("Accounting Dimension", cls.dimension.name)
		# The custom fields change the tables, which commits on MariaDB. Commit on Postgres too.
		frappe.db.commit()  # nosemgrep
		super().tearDownClass()

	def setUp(self):
		super().setUp()
		self.field = self.dimension.fieldname
		self.first = make_value("Designation", "_Test Cash Basis Analyst", "designation_name")
		self.second = make_value("Designation", "_Test Cash Basis Engineer", "designation_name")

	def test_new_dimension_on_the_items(self):
		self.assertTrue(frappe.get_meta("Sales Invoice Item").has_field(self.field))
		self.make_paid_invoice({self.field: self.first}, {self.field: self.second})
		self.assertEqual(self.exception_reasons(), {})
		self.assertEqual(
			self.recognised("2026-04-30", self.field), {(SALES, self.first): 30, (SERVICE, self.second): 20}
		)
		self.assert_invariants("2026-04-30")
