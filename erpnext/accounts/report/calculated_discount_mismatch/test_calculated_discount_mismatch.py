# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import json

import frappe
from frappe.utils.formatters import format_value

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.report.calculated_discount_mismatch.calculated_discount_mismatch import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestCalculatedDiscountMismatch(ERPNextTestSuite):
	"""Integrity detector: flag transactions whose stored ``discount_amount`` was tampered
	after the fact (a Version records the change) while ``additional_discount_percentage``
	stayed the same, so the stored amount no longer matches the percentage-derived value.
	"""

	def run_report(self, docname: str) -> dict | None:
		"""Run the (filter-less) report and return the row for ``docname``, if any."""
		_columns, data = execute(frappe._dict({}))
		return next((row for row in data if row["docname"] == docname), None)

	def create_discounted_invoice(self) -> "frappe.Document":
		"""Draft Sales Invoice (rate 1000) with a 10% additional discount.

		The controller derives ``discount_amount`` = 10% of the grand total = 100.00,
		so the stored amount is consistent with the percentage.
		"""
		invoice = create_sales_invoice(rate=1000, qty=1, do_not_submit=1)
		invoice.additional_discount_percentage = 10
		invoice.save()
		invoice.reload()
		return invoice

	def test_consistent_discount_is_not_flagged(self):
		"""A submitted invoice whose discount_amount matches its percentage is not reported."""
		invoice = self.create_discounted_invoice()
		invoice.submit()
		invoice.reload()

		self.assertEqual(invoice.discount_amount, 100.0)
		self.assertIsNone(self.run_report(invoice.name))

	def test_tampered_discount_is_flagged(self):
		"""Directly overwriting discount_amount (leaving the percentage intact) is reported.

		This reproduces the real-world integrity breach: a Version records the
		``discount_amount`` change, its ``new`` value equals the current stored amount, and
		``additional_discount_percentage`` was not touched -- exactly the shape the report
		queries for.
		"""
		invoice = self.create_discounted_invoice()
		consistent_amount = invoice.discount_amount  # 100.00, matches the 10% percentage
		tampered_amount = 250.0

		discount_field = frappe.get_meta("Sales Invoice").get_field("discount_amount")
		# Format exactly as the report does so version.new == format_value(current amount).
		suspected = format_value(consistent_amount, df=discount_field, currency=invoice.currency)
		actual = format_value(tampered_amount, df=discount_field, currency=invoice.currency)

		# Tamper the stored amount directly, bypassing the controller that would recompute it.
		frappe.db.set_value("Sales Invoice", invoice.name, "discount_amount", tampered_amount)
		self.record_discount_change(invoice.name, suspected, actual)

		row = self.run_report(invoice.name)

		self.assertIsNotNone(row)
		self.assertEqual(row["doctype"], "Sales Invoice")
		self.assertEqual(row["actual_discount_percentage"], 10.0)
		self.assertEqual(row["actual_discount_amount"], actual)
		self.assertEqual(row["suspected_discount_amount"], suspected)

	def record_discount_change(self, docname: str, old: str, new: str) -> None:
		"""Insert the Version audit row a direct discount_amount edit would have produced."""
		version = frappe.new_doc("Version")
		version.ref_doctype = "Sales Invoice"
		version.docname = docname
		version.data = json.dumps({"changed": [["discount_amount", old, new]]}, separators=(",", ":"))
		version.flags.ignore_version = True
		version.insert(ignore_permissions=True)
