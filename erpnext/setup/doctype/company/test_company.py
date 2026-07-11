# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
import json

import frappe
from frappe import _
from frappe.query_builder.functions import IfNull
from frappe.utils import random_string

from erpnext.accounts.doctype.account.chart_of_accounts.chart_of_accounts import (
	get_charts_for_country,
)
from erpnext.accounts.doctype.account.test_account import create_account
from erpnext.setup.doctype.company.company import get_default_company_address
from erpnext.stock.doctype.delivery_note.test_delivery_note import create_delivery_note
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
from erpnext.tests.utils import ERPNextTestSuite


class TestCompany(ERPNextTestSuite):
	def test_coa_based_on_existing_company(self):
		company = frappe.new_doc("Company")
		company.company_name = "COA from Existing Company"
		company.abbr = "CFEC"
		company.default_currency = "INR"
		company.create_chart_of_accounts_based_on = "Existing Company"
		company.existing_company = "_Test Company"
		company.country = "India"
		company.save()

		expected_results = {
			"Debtors - CFEC": {
				"account_type": "Receivable",
				"is_group": 0,
				"root_type": "Asset",
				"parent_account": "Accounts Receivable - CFEC",
			},
			"Cash - CFEC": {
				"account_type": "Cash",
				"is_group": 0,
				"root_type": "Asset",
				"parent_account": "Cash In Hand - CFEC",
			},
		}

		for account, acc_property in expected_results.items():
			acc = frappe.get_doc("Account", account)
			for prop, val in acc_property.items():
				self.assertEqual(acc.get(prop), val)

		frappe.delete_doc("Company", "COA from Existing Company")

	def test_coa_based_on_country_template(self):
		countries = ["Canada", "Germany", "France"]

		for country in countries:
			templates = get_charts_for_country(country)
			if len(templates) != 1 and "Standard" in templates:
				templates.remove("Standard")

			self.assertTrue(templates)

			for company in frappe.db.get_all("Company", {"company_name": ["in", templates]}):
				frappe.delete_doc("Company", company.name)

			for template in templates:
				try:
					company = frappe.new_doc("Company")
					company.company_name = template
					# a short random abbr collides with existing test companies often enough
					# to flake, so pick one that is verified unique
					abbr = random_string(3)
					while frappe.db.exists("Company", {"abbr": abbr}):
						abbr = random_string(3)
					company.abbr = abbr
					company.default_currency = "USD"
					company.create_chart_of_accounts_based_on = "Standard Template"
					company.chart_of_accounts = template
					company.country = country
					company.save()

					account_types = [
						"Cost of Goods Sold",
						"Depreciation",
						"Expenses Included In Valuation",
						"Fixed Asset",
						"Payable",
						"Receivable",
						"Stock Adjustment",
						"Stock Received But Not Billed",
						"Stock Delivered But Not Billed",
						"Bank",
						"Cash",
						"Stock",
					]

					for account_type in account_types:
						filters = {"company": template, "account_type": account_type}
						if account_type in ["Bank", "Cash"]:
							filters["is_group"] = 1

						has_matching_accounts = frappe.get_all("Account", filters)
						error_message = _("No Account matched these filters: {}").format(json.dumps(filters))

						self.assertTrue(has_matching_accounts, msg=error_message)
				finally:
					frappe.delete_doc("Company", template)

	def test_basic_tree(self, records=None):
		self.load_test_records("Company")
		min_lft = 1
		max_rgt = frappe.get_all("Company", fields=[{"MAX": "rgt", "as": "max_rgt"}])[0].max_rgt

		if not records:
			records = self.globalTestRecords["Company"][2:]

		for company in records:
			lft, rgt, parent_company = frappe.db.get_value(
				"Company", company.get("company_name"), ["lft", "rgt", "parent_company"]
			)

			if parent_company:
				parent_lft, parent_rgt = frappe.db.get_value("Company", parent_company, ["lft", "rgt"])
			else:
				# root
				parent_lft = min_lft - 1
				parent_rgt = max_rgt + 1

			self.assertTrue(lft)
			self.assertTrue(rgt)
			self.assertLess(lft, rgt)
			self.assertLess(parent_lft, parent_rgt)
			self.assertGreater(lft, parent_lft)
			self.assertLess(rgt, parent_rgt)
			self.assertGreaterEqual(lft, min_lft)
			self.assertLessEqual(rgt, max_rgt)

	def test_primary_address(self):
		company = "_Test Company"

		secondary = frappe.get_doc(
			{
				"address_title": "Non Primary",
				"doctype": "Address",
				"address_type": "Billing",
				"address_line1": "Something",
				"city": "Mumbai",
				"state": "Maharashtra",
				"country": "India",
				"is_primary_address": 1,
				"pincode": "400098",
				"links": [
					{
						"link_doctype": "Company",
						"link_name": company,
					}
				],
			}
		)
		secondary.insert()
		self.addCleanup(secondary.delete)

		primary = frappe.copy_doc(secondary)
		primary.is_primary_address = 1
		primary.insert()
		self.addCleanup(primary.delete)

		self.assertEqual(get_default_company_address(company), primary.name)

	def get_no_of_children(self, company):
		def get_no_of_children(companies, no_of_children):
			children = []
			for company in companies:
				company_dt = frappe.qb.DocType("Company")
				children += (
					frappe.qb.from_(company_dt)
					.select(company_dt.name)
					.where(IfNull(company_dt.parent_company, "") == (company or ""))
					.run(pluck=True)
				)

			if len(children):
				return get_no_of_children(children, no_of_children + len(children))
			else:
				return no_of_children

		return get_no_of_children([company], 0)

	def test_change_parent_company(self):
		child_company = frappe.get_doc("Company", "_Test Company 5")

		# changing parent of company
		child_company.parent_company = "_Test Company 3"
		child_company.save()
		self.test_basic_tree()

		# move it back
		child_company.parent_company = "_Test Company 4"
		child_company.save()
		self.test_basic_tree()

	def test_get_children_root_includes_empty_string_parent(self):
		"""get_children at the root mirrors the original ifnull(parent_company,"")="": the converted
		`["is", "not set"]` filter expands to `parent_company IS NULL OR parent_company = ''`, so a
		company whose parent_company is '' (MariaDB keeps '') is still listed as a root. Guards against
		narrowing this to an IS NULL-only check."""
		from erpnext.setup.doctype.company.company import get_children

		company = "_Test Company"
		cd = frappe.qb.DocType("Company")
		original = frappe.db.get_value("Company", company, "parent_company")
		# force '' (not NULL) at the SQL layer, bypassing frappe's empty -> NULL doc coercion
		frappe.qb.update(cd).set(cd.parent_company, "").where(cd.name == company).run()
		self.addCleanup(
			lambda: frappe.qb.update(cd).set(cd.parent_company, original).where(cd.name == company).run()
		)

		roots = {row.value for row in get_children("Company", parent="")}
		self.assertIn(company, roots)

	def test_annual_transaction_history_merges_dates_across_doctypes(self):
		"""get_all_transactions_annual_history aggregates each DocType separately, then merges the
		per-date counts. Two transactions of different DocTypes sharing a transaction_date must land
		in one date bucket with the summed count (the UNION GROUP BY -> Counter-merge conversion)."""
		from frappe.utils import add_days, get_timestamp, nowdate

		from erpnext.selling.doctype.quotation.test_quotation import make_quotation
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
		from erpnext.setup.doctype.company.company import get_all_transactions_annual_history

		company = "_Test Company"
		txn_date = add_days(nowdate(), -30)
		key = get_timestamp(txn_date)

		before = get_all_transactions_annual_history(company).get(key, 0)

		quotation = make_quotation(company=company, transaction_date=txn_date, do_not_submit=True)
		self.addCleanup(frappe.delete_doc, "Quotation", quotation.name, force=True)
		sales_order = make_sales_order(company=company, transaction_date=txn_date, do_not_submit=True)
		self.addCleanup(frappe.delete_doc, "Sales Order", sales_order.name, force=True)

		after = get_all_transactions_annual_history(company).get(key, 0)
		self.assertEqual(after - before, 2)

	def test_sdbnb_validation_requires_account_when_enabled(self):
		company = get_test_company()

		company.enable_stock_delivered_but_not_billed = 1
		company.stock_delivered_but_not_billed = None

		with self.assertRaises(frappe.ValidationError):
			company.save()

	def test_disable_sdbnb_with_outstanding_delivery_note_fails(self):
		company = get_test_company()

		item_code = create_stock_item_with_inventory()
		create_outstanding_delivery_note(item_code)

		company.enable_stock_delivered_but_not_billed = 0

		with self.assertRaises(frappe.ValidationError):
			company.save()

	def test_cannot_change_sdbnb_account_with_outstanding_delivery_note(self):
		company = get_test_company()

		item_code = create_stock_item_with_inventory()
		create_outstanding_delivery_note(item_code)

		new_account = create_account(
			account_name="Stock Delivered But Not Billed - New",
			account_type="Stock Delivered But Not Billed",
			parent_account="Stock Assets - _TSDBNB",
			company=company.name,
		)

		company.stock_delivered_but_not_billed = new_account

		with self.assertRaises(frappe.ValidationError):
			company.save()

	def test_demo_data(self):
		from erpnext.setup.demo import clear_demo_data, setup_demo_data

		self.load_test_records("Company")

		setup_demo_data(self.globalTestRecords["Company"][0]["company_name"])
		company_name = frappe.db.get_value("Company", {"name": ("like", "%(Demo)")})
		self.assertTrue(company_name)

		for transaction in frappe.get_hooks("demo_transaction_doctypes"):
			self.assertTrue(frappe.db.exists(frappe.unscrub(transaction), {"company": company_name}))

		clear_demo_data()
		company_name = frappe.db.get_value("Company", {"name": ("like", "%(Demo)")})
		self.assertFalse(company_name)
		for transaction in frappe.get_hooks("demo_transaction_doctypes"):
			self.assertFalse(frappe.db.exists(frappe.unscrub(transaction), {"company": company_name}))


def create_company_communication(doctype, docname):
	comm = frappe.get_doc(
		{
			"doctype": "Communication",
			"communication_type": "Communication",
			"content": "Deduplication of Links",
			"communication_medium": "Email",
			"reference_doctype": doctype,
			"reference_name": docname,
		}
	)
	comm.insert()


def create_child_company():
	child_company = frappe.db.exists("Company", "Test Company")
	if not child_company:
		child_company = frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": "Test Company",
				"abbr": "test_company",
				"default_currency": "INR",
			}
		)
		child_company.insert()
	else:
		child_company = frappe.get_doc("Company", child_company)

	return child_company.name


def create_test_lead_in_company(company):
	lead = frappe.db.exists("Lead", "Test Lead in new company")
	if not lead:
		lead = frappe.get_doc(
			{"doctype": "Lead", "lead_name": "Test Lead in new company", "scompany": company}
		)
		lead.insert()
	else:
		lead = frappe.get_doc("Lead", lead)
		lead.company = company
		lead.save()
	return lead.name


def get_test_company():
	if frappe.db.exists("Company", "_Test SDBNB Company"):
		return frappe.get_doc("Company", "_Test SDBNB Company")

	return frappe.get_doc(
		{
			"doctype": "Company",
			"company_name": "_Test SDBNB Company",
			"abbr": "_TSDBNB",
			"country": "India",
			"default_currency": "INR",
			"enable_perpetual_inventory": 1,
			"enable_stock_delivered_but_not_billed": 1,
		}
	).insert()


def create_stock_item_with_inventory():
	item_code = make_item(
		"SDBNB Test Item",
		properties={"is_stock_item": 1},
	).name

	make_stock_entry(
		item_code=item_code,
		target="Stores - _TSDBNB",
		qty=10,
		basic_rate=100,
		company="_Test SDBNB Company",
	)

	return item_code


def create_outstanding_delivery_note(item_code):
	return create_delivery_note(
		item_code=item_code,
		qty=5,
		rate=150,
		company="_Test SDBNB Company",
		warehouse="Stores - _TSDBNB",
		cost_center="Main - _TSDBNB",
		expense_account="Stock Delivered But Not Billed - _TSDBNB",
	)
