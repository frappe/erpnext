# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.patches.v16_0.set_not_applicable_on_german_item_tax_templates import (
	execute as backfill_not_applicable,
)


class TestItemTaxTemplate(unittest.TestCase):
	pass


class TestGermanNotApplicableBackfill(FrappeTestCase):
	"""Run the `not_applicable` backfill patch against a seeded German company.

	The company is created from the shipped German defaults, so the templates the
	patch has to recognise are the ones a real site got. Each test resets the flag
	to its pre-patch state (`not_applicable = 0`) and runs the patch.
	"""

	TITLES = ("19 %", "7 %", "0%")

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.company = "_Test German Item Tax Templates"
		if not frappe.db.exists("Company", cls.company):
			frappe.get_doc(
				{
					"doctype": "Company",
					"company_name": cls.company,
					"abbr": "_TGITT",
					"country": "Germany",
					"default_currency": "EUR",
					"create_chart_of_accounts_based_on": "Standard Template",
					"chart_of_accounts": "Standard",
				}
			).insert()

		cls.templates = {
			title: frappe.db.get_value("Item Tax Template", {"company": cls.company, "title": title}, "name")
			for title in cls.TITLES
		}
		assert all(cls.templates.values()), f"German defaults not seeded: {cls.templates}"

	def setUp(self):
		frappe.db.savepoint("before_backfill_test")
		self.addCleanup(frappe.db.rollback, save_point="before_backfill_test")
		self.seeded_flags = self.flagged_rows()
		# every default template ships not-applicable rows, otherwise the patch
		# would be tested against effectively empty data
		for title in self.TITLES:
			self.assertTrue(self.seeded_flags[title], f"no not-applicable rows seeded in {title}")

	def flagged_rows(self, title=None) -> dict[str, set]:
		"""Detail rows currently marked as not applicable, per template title."""
		return {
			t: {
				d.name
				for d in frappe.get_all(
					"Item Tax Template Detail",
					filters={"parent": name, "not_applicable": 1},
					fields=["name"],
				)
			}
			for t, name in self.templates.items()
			if title in (None, t)
		}

	def clear_flags(self):
		"""Restore the pre-patch state: zero rate, no flag."""
		for name in self.templates.values():
			frappe.db.set_value(
				"Item Tax Template Detail",
				{"parent": name},
				"not_applicable",
				0,
				update_modified=False,
			)
		self.assertEqual(self.flagged_rows(), {t: set() for t in self.TITLES})

	def add_zero_rate_row(self, title, account_name, account_number):
		"""Add a user-defined zero-rate row, as a customised site would have."""
		like_account = frappe.db.get_value(
			"Account", {"company": self.company, "account_name": "Umsatzsteuer 19 %"}, "name"
		)
		account = frappe.get_doc(
			{
				"doctype": "Account",
				"company": self.company,
				"account_name": account_name,
				"account_number": account_number,
				"account_type": "Tax",
				"parent_account": frappe.db.get_value("Account", like_account, "parent_account"),
			}
		).insert()

		template = frappe.get_doc("Item Tax Template", self.templates[title])
		template.append("taxes", {"tax_type": account.name, "tax_rate": 0})
		template.save()

	def test_backfills_unmodified_defaults(self):
		self.clear_flags()
		backfill_not_applicable()
		self.assertEqual(self.flagged_rows(), self.seeded_flags)

	def test_keeps_customised_template_untouched(self):
		self.clear_flags()
		self.add_zero_rate_row("19 %", "Sonstige Umsatzsteuer", "9998")
		backfill_not_applicable()

		self.assertEqual(self.flagged_rows("19 %"), {"19 %": set()})
		self.assertEqual(self.flagged_rows("7 %"), {"7 %": self.seeded_flags["7 %"]})

	def test_keeps_duplicate_account_name_untouched(self):
		"""A numbered account can share `account_name` with a default one.

		Its identifier collapses onto the default's, so only the row count tells
		the customised template apart from an untouched one.
		"""
		self.clear_flags()
		self.add_zero_rate_row("7 %", "Umsatzsteuer 19 %", "9999")
		backfill_not_applicable()

		self.assertEqual(self.flagged_rows("7 %"), {"7 %": set()})
		self.assertEqual(self.flagged_rows("19 %"), {"19 %": self.seeded_flags["19 %"]})

	def test_rerun_changes_nothing(self):
		def snapshot():
			return frappe.get_all(
				"Item Tax Template Detail",
				filters={"parent": ("in", tuple(self.templates.values()))},
				fields=["name", "not_applicable", "tax_rate", "modified"],
				order_by="name",
			)

		before = snapshot()
		backfill_not_applicable()
		self.assertEqual(snapshot(), before)
