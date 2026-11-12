# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
import json
from unittest.mock import patch

import frappe
from frappe import _
from frappe.utils import random_string
from frappe.utils.nestedset import get_root_of

from erpnext.accounts.doctype.account.chart_of_accounts.chart_of_accounts import (
	get_charts_for_country,
)
from erpnext.setup.doctype.company.company import get_default_company_address
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
		max_rgt = frappe.db.sql("select max(rgt) from `tabCompany`")[0][0]

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
			self.assertTrue(lft < rgt)
			self.assertTrue(parent_lft < parent_rgt)
			self.assertTrue(lft > parent_lft)
			self.assertTrue(rgt < parent_rgt)
			self.assertTrue(lft >= min_lft)
			self.assertTrue(rgt <= max_rgt)

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
				children += frappe.db.sql_list(
					"""select name from `tabCompany`
				where ifnull(parent_company, '')=%s""",
					company or "",
				)

			if len(children):
				return get_no_of_children(children, no_of_children + len(children))
			else:
				return no_of_children

		return get_no_of_children([company], 0)

	def test_default_departments_ignore_session_translations(self):
		self.assertEqual(get_root_of("Department"), "All Departments")

		translations = {"All Departments": "Alle Abteilungen", "Accounts": "Buchhaltung"}
		with patch("frappe.translate.get_all_translations", return_value=translations):
			company = frappe.new_doc("Company")
			company.company_name = "Dept Translation Test Co"
			company.abbr = "DTTC"
			company.default_currency = "INR"
			company.country = "India"
			company.insert()

		self.assertFalse(frappe.db.exists("Department", "Alle Abteilungen"))
		self.assertEqual(
			frappe.get_all("Department", filters={"parent_department": ("is", "not set")}, pluck="name"),
			["All Departments"],
		)

		departments = frappe.get_all(
			"Department", filters={"company": company.name}, fields=["name", "parent_department"]
		)
		self.assertTrue(departments)
		self.assertEqual({d.parent_department for d in departments}, {"All Departments"})
		self.assertIn("Buchhaltung - DTTC", [d.name for d in departments])

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

	def test_invalid_default_accounts_and_cost_centers(self):
		company = frappe.get_doc("Company", "_Test Company")
		original_inventory = company.default_inventory_account
		company.default_inventory_account = frappe.db.get_value(
			"Account", {"company": company.name, "root_type": "Expense", "is_group": 0}
		)
		with self.assertRaises(frappe.ValidationError):
			company.save()

		company.default_inventory_account = original_inventory
		company.default_operating_cost_account = frappe.db.get_value(
			"Account", {"company": company.name, "root_type": "Asset", "is_group": 0}
		)
		with self.assertRaises(frappe.ValidationError):
			company.save()

		company.default_operating_cost_account = None
		company.cost_center = frappe.db.get_value("Cost Center", {"company": company.name, "is_group": 1})
		with self.assertRaises(frappe.ValidationError):
			company.save()

	def test_cannot_disable_perpetual_inventory_with_stock(self):
		company = get_test_company()
		create_stock_item_with_inventory(company)
		company.enable_perpetual_inventory = 0
		with self.assertRaisesRegex(frappe.ValidationError, "Cannot disable perpetual inventory"):
			company.save()

	def test_company_deletion_clears_item_reorder_rows(self):
		company = frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": "Reorder Cleanup Test",
				"abbr": "RCT",
				"country": "Nepal",
				"default_currency": "INR",
			}
		).insert()
		item = make_item("Reorder Cleanup Item")
		item.append(
			"reorder_levels",
			{
				"warehouse": company.default_warehouse,
				"warehouse_reorder_level": 10,
				"warehouse_reorder_qty": 10,
				"material_request_type": "Purchase",
			},
		)
		item.save()
		frappe.delete_doc("Company", company.name)
		self.assertFalse(frappe.db.exists("Item Reorder", {"warehouse": company.default_warehouse}))

	def test_cannot_delete_company_with_bom(self):
		company = get_test_company()
		exists = frappe.db.exists
		with patch(
			"frappe.db.exists",
			side_effect=lambda doctype, *args, **kwargs: (
				"BOM-1" if doctype == "BOM" else exists(doctype, *args, **kwargs)
			),
		):
			with self.assertRaisesRegex(frappe.ValidationError, "BOM"):
				company.on_trash()

	def test_tax_setup_requires_manager_role(self):
		company = frappe.get_doc("Company", "_Test Company")
		with patch("frappe.only_for", side_effect=frappe.PermissionError):
			with patch("erpnext.setup.doctype.company.company.setup_taxes_and_charges") as setup:
				with self.assertRaises(frappe.PermissionError):
					company.create_default_tax_template()
				setup.assert_not_called()

	def test_currency_change_checks_ledger_entries(self):
		company = get_test_company()
		create_stock_item_with_inventory(company)
		self.assertTrue(company.check_if_transactions_exist())
		company.default_currency = "USD"
		with self.assertRaisesRegex(frappe.ValidationError, "existing transactions"):
			company.save()

	def test_currency_change_without_transactions_updates_chart(self):
		company = frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": "Currency Change Test",
				"abbr": "CCT",
				"country": "Nepal",
				"default_currency": "INR",
			}
		).insert()
		from erpnext.accounts.doctype.account.account import get_account_currency

		self.assertTrue(company.default_cash_account)
		self.assertEqual(get_account_currency(company.default_cash_account), "INR")
		company.default_currency = "USD"
		company.save()
		self.assertEqual(
			frappe.db.get_value("Account", company.default_cash_account, "account_currency"), "USD"
		)
		self.assertEqual(get_account_currency(company.default_cash_account), "USD")

	def test_provisional_field_stays_visible_if_another_company_uses_it(self):
		company = get_test_company()
		with (
			patch("erpnext.setup.doctype.company.company.make_property_setter") as setter,
			patch("frappe.db.exists", return_value="Other Company"),
		):
			company.enable_provisional_accounting_for_non_stock_items = 0
			company.validate_provisional_account_for_non_stock_items()
			self.assertFalse(setter.call_args.args[3])

		with (
			patch("erpnext.setup.doctype.company.company.make_property_setter") as setter,
			patch("frappe.db.exists", return_value=None),
		):
			company.set_provisional_expense_visibility(False)
			self.assertTrue(setter.call_args.args[3])

	def test_opening_invoice_does_not_count_as_monthly_sales(self):
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
		from erpnext.setup.doctype.company.company import (
			update_company_current_month_sales,
			update_company_monthly_sales,
		)

		invoice = create_sales_invoice()
		update_company_current_month_sales(invoice.company)
		update_company_monthly_sales(invoice.company)
		before = frappe.db.get_value(
			"Company", invoice.company, ["total_monthly_sales", "sales_monthly_history"], as_dict=True
		)
		opening_invoice = create_sales_invoice(do_not_save=True)
		opening_invoice.is_opening = "Yes"
		opening_invoice.items[0].income_account = "Temporary Opening - _TC"
		opening_invoice.insert().submit()
		update_company_current_month_sales(invoice.company)
		update_company_monthly_sales(invoice.company)
		after = frappe.db.get_value(
			"Company", invoice.company, ["total_monthly_sales", "sales_monthly_history"], as_dict=True
		)
		self.assertGreaterEqual(before.total_monthly_sales, invoice.base_grand_total)
		self.assertEqual(before.total_monthly_sales, after.total_monthly_sales)
		self.assertEqual(json.loads(before.sales_monthly_history), json.loads(after.sales_monthly_history))

	def test_invalid_default_warehouses(self):
		company = frappe.get_doc("Company", "_Test Company")
		company.default_in_transit_warehouse = company.default_warehouse
		with self.assertRaises(frappe.ValidationError):
			company.save()

		company.default_in_transit_warehouse = None
		disabled_warehouse = frappe.db.get_value(
			"Warehouse",
			{"company": company.name, "is_group": 0, "name": ["!=", company.default_warehouse]},
		)
		frappe.db.set_value("Warehouse", disabled_warehouse, "disabled", 1)
		company.default_warehouse = disabled_warehouse
		with self.assertRaises(frappe.ValidationError):
			company.save()

	def test_existing_invalid_defaults_do_not_block_unrelated_saves(self):
		company = frappe.get_doc("Company", "_Test Company")
		expense_accounts = frappe.get_all(
			"Account",
			filters={"company": company.name, "root_type": "Expense", "is_group": 0},
			pluck="name",
			limit=2,
		)
		frappe.db.set_value("Company", company.name, "unrealized_profit_loss_account", expense_accounts[0])
		frappe.db.set_value("Warehouse", company.default_warehouse, "disabled", 1)

		company.reload()
		company.monthly_sales_target = 100
		company.save()

		company.unrealized_profit_loss_account = expense_accounts[1]
		with self.assertRaises(frappe.ValidationError):
			company.save()

	def test_clear_demo_data(self):
		from erpnext.setup.demo import clear_demo_data, read_data_file_using_hooks

		company = frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": "_Test Company (Demo)",
				"abbr": "_TCD",
				"default_currency": "INR",
				"country": "India",
			}
		).insert()
		frappe.db.set_single_value("Global Defaults", "demo_company", company.name)
		for doctype in frappe.get_hooks("demo_master_doctypes"):
			for record in json.loads(read_data_file_using_hooks(doctype)):
				frappe.get_doc(record).insert(ignore_if_duplicate=True)

		clear_demo_data()

		self.assertFalse(frappe.db.exists("Company", company.name))
		self.assertFalse(frappe.db.get_single_value("Global Defaults", "demo_company"))
		self.assertFalse(frappe.db.exists("Customer", {"customer_name": "Grant Plastics Ltd."}))
		self.assertFalse(frappe.db.exists("Item", "SKU001"))


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
	abbr = random_string(6)
	return frappe.get_doc(
		{
			"doctype": "Company",
			"company_name": f"_Test Company {abbr}",
			"abbr": abbr,
			"country": "India",
			"default_currency": "INR",
			"enable_perpetual_inventory": 1,
		}
	).insert()


def create_stock_item_with_inventory(company):
	item_code = make_item("Company Test Stock Item", properties={"is_stock_item": 1}).name

	make_stock_entry(
		item_code=item_code,
		target=f"Stores - {company.abbr}",
		qty=10,
		basic_rate=100,
		company=company.name,
		expense_account=company.stock_adjustment_account,
	)

	return item_code
