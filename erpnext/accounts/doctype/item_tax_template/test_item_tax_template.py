# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.patches.v16_0.set_not_applicable_on_german_item_tax_templates import (
	execute as backfill_not_applicable,
)
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.get_item_details import get_item_tax_template

COMPANY = "_Test Company"
TAX_ACCOUNT = "_Test Account VAT - _TC"


class TestItemTaxTemplate(FrappeTestCase):
	def make_template(self, rows, title="_Test ITT"):
		doc = frappe.new_doc("Item Tax Template")
		doc.title = f"{title} {frappe.generate_hash(length=6)}"
		doc.company = COMPANY
		for account, rate, not_applicable in rows:
			doc.append(
				"taxes",
				{"tax_type": account, "tax_rate": rate, "not_applicable": not_applicable},
			)
		return doc

	def make_tax_template(self, rate):
		return self.make_template([(TAX_ACCOUNT, rate, 0)]).insert().name

	def make_item_with_taxes(self, taxes):
		return make_item(properties={"taxes": taxes}).name

	def get_template_for(self, item_code, **kwargs):
		ctx = {"item_code": item_code, "company": COMPANY, "posting_date": today(), "tax_category": None}
		ctx.update(kwargs)
		return get_item_tax_template(ctx)

	def make_tax_category(self, title):
		if not frappe.db.exists("Tax Category", title):
			frappe.get_doc({"doctype": "Tax Category", "title": title}).insert()
		return title

	def test_dated_and_rate_band_rows_together(self):
		template_18 = self.make_tax_template(18)
		template_5 = self.make_tax_template(5)
		item_code = self.make_item_with_taxes(
			[
				{"item_tax_template": template_18, "valid_from": add_days(today(), -10)},
				{"item_tax_template": template_5, "minimum_net_rate": 0, "maximum_net_rate": 1000},
			]
		)

		self.assertEqual(self.get_template_for(item_code, base_net_rate=500), template_18)

	def test_rate_band_without_valid_from_on_backdated_transaction(self):
		template_5 = self.make_tax_template(5)
		template_12 = self.make_tax_template(12)
		item_code = self.make_item_with_taxes(
			[
				{"item_tax_template": template_5, "minimum_net_rate": 0, "maximum_net_rate": 1000},
				{"item_tax_template": template_12, "minimum_net_rate": 1000.01, "maximum_net_rate": 1000000},
			]
		)

		yesterday = add_days(today(), -1)
		self.assertEqual(
			self.get_template_for(item_code, posting_date=yesterday, base_net_rate=500), template_5
		)
		self.assertEqual(
			self.get_template_for(item_code, posting_date=yesterday, base_net_rate=5000), template_12
		)

	def test_undated_row_is_kept_for_its_tax_category(self):
		in_state = self.make_tax_category("_Test In-State")
		out_state = self.make_tax_category("_Test Out-State")
		template_in_state = self.make_tax_template(5)
		template_out_state = self.make_tax_template(18)
		item_code = self.make_item_with_taxes(
			[
				{"item_tax_template": template_in_state, "tax_category": in_state},
				{
					"item_tax_template": template_out_state,
					"tax_category": out_state,
					"valid_from": add_days(today(), -10),
				},
			]
		)

		self.assertEqual(self.get_template_for(item_code, tax_category=in_state), template_in_state)
		self.assertEqual(self.get_template_for(item_code, tax_category=out_state), template_out_state)

	def test_template_of_old_tax_category_is_replaced(self):
		in_state = self.make_tax_category("_Test In-State")
		out_state = self.make_tax_category("_Test Out-State")
		template_in_state = self.make_tax_template(5)
		template_out_state = self.make_tax_template(18)
		item_code = self.make_item_with_taxes(
			[
				{"item_tax_template": template_in_state, "tax_category": in_state},
				{
					"item_tax_template": template_out_state,
					"tax_category": out_state,
					"valid_from": add_days(today(), -10),
				},
			]
		)

		self.assertEqual(
			self.get_template_for(item_code, tax_category=out_state, item_tax_template=template_in_state),
			template_out_state,
		)
		self.assertEqual(
			self.get_template_for(item_code, tax_category=None, item_tax_template=template_in_state),
			template_in_state,
		)

	def test_superseded_template_is_replaced_on_transaction(self):
		template_12 = self.make_tax_template(12)
		template_18 = self.make_tax_template(18)
		item_code = self.make_item_with_taxes(
			[
				{"item_tax_template": template_12, "valid_from": add_days(today(), -60)},
				{"item_tax_template": template_18, "valid_from": add_days(today(), -10)},
			]
		)

		self.assertEqual(self.get_template_for(item_code, item_tax_template=template_12), template_18)

		si = create_sales_invoice(item_code=item_code, rate=1000, do_not_save=True)
		si.items[0].item_tax_template = template_12
		si.append(
			"taxes",
			{
				"charge_type": "On Net Total",
				"account_head": TAX_ACCOUNT,
				"description": "VAT",
				"rate": 0,
			},
		)
		si.insert()

		self.assertEqual(si.items[0].item_tax_template, template_18)
		self.assertEqual(si.taxes[0].tax_amount, 180)

	def make_item_group_with_taxes(self, taxes):
		item_group = frappe.get_doc(
			{
				"doctype": "Item Group",
				"item_group_name": f"_Test ITT Group {frappe.generate_hash(length=6)}",
				"parent_item_group": "All Item Groups",
				"taxes": taxes,
			}
		)
		return item_group.insert().name

	def test_superseded_template_is_replaced_with_item_row_before_item_group_row(self):
		template_5 = self.make_tax_template(5)
		template_12 = self.make_tax_template(12)
		template_18 = self.make_tax_template(18)
		item_group = self.make_item_group_with_taxes(
			[
				{"item_tax_template": template_12, "valid_from": add_days(today(), -60)},
				{"item_tax_template": template_18, "valid_from": add_days(today(), -10)},
			]
		)
		item_code = make_item(
			properties={
				"item_group": item_group,
				"taxes": [{"item_tax_template": template_5, "valid_from": add_days(today(), -20)}],
			}
		).name

		si = create_sales_invoice(item_code=item_code, rate=1000, do_not_save=True)
		si.items[0].item_tax_template = template_12
		si.insert()

		self.assertEqual(self.get_template_for(item_code), template_5)
		self.assertEqual(si.items[0].item_tax_template, template_5)

	def test_group_account_throws(self):
		doc = self.make_template([("Duties and Taxes - _TC", 7, 0)])
		self.assertRaisesRegex(frappe.ValidationError, "is a group account", doc.insert)

	def test_disabled_template_on_transaction_throws(self):
		template = self.make_template([(TAX_ACCOUNT, 28, 0)])
		template.disabled = 1
		template.insert()

		si = create_sales_invoice(rate=1000, do_not_save=True)
		si.items[0].item_tax_template = template.name
		self.assertRaisesRegex(frappe.ValidationError, "is disabled", si.insert)

	def test_draft_submits_after_its_template_is_disabled(self):
		template = self.make_tax_template(28)
		si = create_sales_invoice(rate=1000, do_not_save=True)
		si.items[0].item_tax_template = template
		si.insert()

		frappe.db.set_value("Item Tax Template", template, "disabled", 1)
		si.reload()
		si.submit()
		self.assertEqual(si.docstatus, 1)

		draft = create_sales_invoice(rate=1000, do_not_submit=True)
		draft.append(
			"items", {"item_code": "_Test Item", "qty": 1, "rate": 1000, "item_tax_template": template}
		)
		self.assertRaisesRegex(frappe.ValidationError, "is disabled", draft.save)

	def test_template_of_other_company_on_transaction_throws(self):
		other_company_template = frappe.db.get_value("Item Tax Template", {"company": "_Test Company 1"})
		si = create_sales_invoice(rate=1000, do_not_save=True)
		si.items[0].item_tax_template = other_company_template
		self.assertRaisesRegex(frappe.ValidationError, "does not belong to Company", si.insert)

	def test_inter_company_purchase_invoice_drops_seller_template(self):
		from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_inter_company_transaction
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_internal_parties

		create_internal_parties()
		seller_template = frappe.new_doc("Item Tax Template")
		seller_template.title = f"_Test ITT {frappe.generate_hash(length=6)}"
		seller_template.company = "Wind Power LLC"
		seller_template.append("taxes", {"tax_type": "ST 6% - WP", "tax_rate": 6})
		seller_template.insert()

		si = create_sales_invoice(
			company="Wind Power LLC",
			customer="_Test Internal Customer",
			debit_to="Debtors - WP",
			warehouse="Stores - WP",
			income_account="Sales - WP",
			expense_account="Cost of Goods Sold - WP",
			cost_center="Main - WP",
			currency="USD",
			do_not_save=1,
		)
		si.selling_price_list = "_Test Price List Rest of the World"
		si.items[0].item_tax_template = seller_template.name
		si.submit()

		pi = make_inter_company_transaction("Sales Invoice", si.name)
		pi.items[0].update(
			{
				"expense_account": "Cost of Goods Sold - _TC1",
				"cost_center": "Main - _TC1",
				"warehouse": "Stores - _TC1",
			}
		)
		pi.submit()

		self.assertEqual(pi.company, "_Test Company 1")
		self.assertNotEqual(pi.items[0].item_tax_template, seller_template.name)


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
