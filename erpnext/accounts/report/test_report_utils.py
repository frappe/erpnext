# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from erpnext.accounts.report.utils import (
	add_party_name_column,
	enrich_with_party_names,
	get_party_name_column,
	show_party_name,
)


class IntegrationTestReportUtils(IntegrationTestCase):
	"""Tests for the deterministic party-name-in-reports helpers."""

	def test_show_party_name_respects_customer_setting(self):
		with self.change_settings("Selling Settings", show_customer_name_in_reports=1):
			self.assertTrue(show_party_name("Customer"))
		with self.change_settings("Selling Settings", show_customer_name_in_reports=0):
			self.assertFalse(show_party_name("Customer"))

	def test_show_party_name_respects_supplier_setting(self):
		with self.change_settings("Buying Settings", show_supplier_name_in_reports=1):
			self.assertTrue(show_party_name("Supplier"))
		with self.change_settings("Buying Settings", show_supplier_name_in_reports=0):
			self.assertFalse(show_party_name("Supplier"))

	def test_show_party_name_always_for_other_party_types(self):
		# Employee/Member/Shareholder etc. are always shown regardless of settings.
		for party_type in ("Employee", "Member", "Shareholder"):
			self.assertTrue(show_party_name(party_type))

	def test_show_party_name_always_for_multi_party(self):
		# No party type -> multi-party report (e.g. General Ledger) -> always show.
		self.assertTrue(show_party_name(None))

	def test_get_party_name_column_label_and_fieldname(self):
		with self.change_settings("Selling Settings", show_customer_name_in_reports=1):
			column = get_party_name_column("Customer", fieldname="customer_name")
			self.assertEqual(column["fieldname"], "customer_name")
			self.assertEqual(column["label"], "Customer Name")
			self.assertEqual(column["fieldtype"], "Data")

		# Multi-party falls back to a generic label and the default fieldname.
		column = get_party_name_column(None)
		self.assertEqual(column["fieldname"], "party_name")
		self.assertEqual(column["label"], "Party Name")

	def test_get_party_name_column_empty_when_hidden(self):
		with self.change_settings("Selling Settings", show_customer_name_in_reports=0):
			self.assertEqual(get_party_name_column("Customer"), {})

	def test_add_party_name_column_insert_and_override(self):
		with self.change_settings("Selling Settings", show_customer_name_in_reports=1):
			columns = [{"fieldname": "party"}, {"fieldname": "amount"}]
			add_party_name_column(
				columns,
				party_type="Customer",
				fieldname="customer_name",
				index=1,
				column_overrides={"sticky": True},
			)
			self.assertEqual(columns[1]["fieldname"], "customer_name")
			self.assertTrue(columns[1]["sticky"])

	def test_add_party_name_column_noop_when_hidden(self):
		with self.change_settings("Selling Settings", show_customer_name_in_reports=0):
			columns = [{"fieldname": "party"}]
			add_party_name_column(columns, party_type="Customer")
			self.assertEqual(len(columns), 1)

	def test_enrich_with_party_names_skips_when_hidden(self):
		with self.change_settings("Selling Settings", show_customer_name_in_reports=0):
			entries = [frappe._dict(party_type="Customer", party="_Test Customer")]
			enrich_with_party_names(entries, party_type="Customer")
			self.assertNotIn("party_name", entries[0])

	def test_enrich_with_party_names_populates_from_master(self):
		customer = frappe.db.get_value("Customer", {"customer_name": "_Test Customer"}, "name")
		if not customer:
			self.skipTest("_Test Customer record not available")

		with self.change_settings("Selling Settings", show_customer_name_in_reports=1):
			entries = [frappe._dict(party_type="Customer", party=customer)]
			enrich_with_party_names(entries, party_type="Customer")
			self.assertEqual(entries[0]["party_name"], "_Test Customer")
