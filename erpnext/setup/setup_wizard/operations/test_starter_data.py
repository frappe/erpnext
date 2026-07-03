# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import json
import unittest
from unittest.mock import MagicMock, patch

import frappe

from erpnext.setup.setup_wizard import setup_wizard
from erpnext.setup.setup_wizard.operations import starter_data


class TestStarterData(unittest.TestCase):
	def test_has_starter_data_detects_non_empty_rows(self):
		self.assertFalse(starter_data.has_starter_data({}))
		self.assertFalse(starter_data.has_starter_data({"starter_customers": "[]"}))
		self.assertTrue(
			starter_data.has_starter_data(
				{"starter_customers": json.dumps([{"customer_name": "Starter Customer"}])}
			)
		)
		self.assertTrue(starter_data.has_starter_data({"starter_items": [{"item_name": "Starter Item"}]}))

	def test_create_customers_uses_defaults(self):
		inserted_customer = MagicMock(name="Starter Customer")
		inserted_customer.name = "Starter Customer"

		with (
			patch.object(starter_data, "_first_existing", side_effect=["Commercial", "India"]),
			patch.object(starter_data.frappe.db, "exists", return_value=None),
			patch.object(starter_data.frappe, "get_doc", return_value=inserted_customer) as get_doc,
		):
			created = starter_data.create_customers(
				frappe._dict(
					{
						"country": "India",
						"starter_customers": json.dumps([{"customer_name": "Starter Customer"}]),
					}
				)
			)

		self.assertEqual(created, ["Starter Customer"])
		get_doc.assert_called_once_with(
			{
				"doctype": "Customer",
				"customer_name": "Starter Customer",
				"customer_group": "Commercial",
				"territory": "India",
				"customer_type": "Company",
			}
		)
		inserted_customer.insert.assert_called_once_with(ignore_permissions=True)

	def test_create_items_uses_stock_and_sale_purchase_flags(self):
		item_doc = MagicMock(name="Starter Item")
		item_doc.name = "Starter Item"

		with (
			patch.object(starter_data.frappe.db, "exists", return_value=None),
			patch.object(starter_data.frappe, "get_doc", return_value=item_doc) as get_doc,
		):
			created = starter_data.create_items(
				frappe._dict(
					{
						"starter_items": json.dumps(
							[
								{
									"item_name": "Starter Item",
									"is_stock_item": 1,
									"is_sales_item": 1,
									"is_purchase_item": 0,
								}
							]
						)
					}
				)
			)

		self.assertEqual(created, ["Starter Item"])
		get_doc.assert_called_once_with(
			{
				"doctype": "Item",
				"item_code": "Starter Item",
				"item_name": "Starter Item",
				"item_group": "Products",
				"stock_uom": "Nos",
				"is_stock_item": 1,
				"is_sales_item": 1,
				"is_purchase_item": 0,
			}
		)
		item_doc.insert.assert_called_once_with(ignore_permissions=True)

	def test_create_opening_stock_uses_item_opening_qty_and_temporary_account(self):
		stock_entry = MagicMock()
		stock_entry.name = "SE-starter-item-test-warehouse-tc"

		with (
			patch.object(starter_data, "_get_default_warehouse", return_value="_Test Warehouse - _TC"),
			patch.object(
				starter_data, "_get_temporary_opening_account", return_value="Temporary Opening - _TC"
			),
			patch.object(starter_data, "_get_item", return_value="Starter Item"),
			patch.object(starter_data.frappe.db, "exists", return_value=None),
			patch.object(starter_data.frappe, "get_doc", return_value=stock_entry) as get_doc,
		):
			created = starter_data.create_opening_stock(
				frappe._dict(
					{
						"company_name": "_Test Company",
						"starter_items": json.dumps(
							[
								{
									"item_name": "Starter Item",
									"is_stock_item": 1,
									"opening_qty": 7,
								},
								{
									"item_name": "Ignored Service",
									"is_stock_item": 0,
									"opening_qty": 5,
								},
							]
						),
					}
				)
			)

		self.assertEqual(created, ["SE-starter-item-test-warehouse-tc"])
		stock_entry_payload = get_doc.call_args.args[0]
		self.assertEqual(stock_entry_payload["name"], "SE-starter-item--test-warehouse----tc")
		self.assertEqual(stock_entry_payload["doctype"], "Stock Entry")
		self.assertEqual(stock_entry_payload["company"], "_Test Company")
		self.assertEqual(stock_entry_payload["is_opening"], "Yes")
		self.assertEqual(stock_entry_payload["items"][0]["item_code"], "Starter Item")
		self.assertEqual(stock_entry_payload["items"][0]["qty"], 7)
		self.assertEqual(stock_entry_payload["items"][0]["t_warehouse"], "_Test Warehouse - _TC")
		self.assertEqual(stock_entry_payload["items"][0]["expense_account"], "Temporary Opening - _TC")
		stock_entry.insert.assert_called_once_with(
			ignore_permissions=True, set_name="SE-starter-item--test-warehouse----tc"
		)
		stock_entry.submit.assert_called_once()

	def test_create_opening_invoices_from_customer_rows(self):
		tool = MagicMock()
		tool.get_invoice_dict.side_effect = lambda row: frappe._dict(
			{"party": row.party, "outstanding_amount": row.outstanding_amount}
		)

		def exists(doctype, name_or_filters=None):
			if doctype == "Sales Invoice":
				return None
			if doctype == "Customer":
				return name_or_filters
			return None

		with (
			patch.object(
				starter_data, "_get_temporary_opening_account", return_value="Temporary Opening - _TC"
			),
			patch.object(starter_data, "_get_party", side_effect=lambda _party_type, party: party),
			patch.object(starter_data.frappe.db, "exists", side_effect=exists),
			patch.object(starter_data.frappe, "new_doc", return_value=tool),
			patch(
				"erpnext.accounts.doctype.opening_invoice_creation_tool.opening_invoice_creation_tool.start_import",
				return_value=["SI-starter-customer"],
			) as start_import,
		):
			created = starter_data.create_opening_invoices(
				frappe._dict(
					{
						"company_name": "_Test Company",
						"starter_customers": json.dumps(
							[
								{"customer_name": "Starter Customer", "opening_amount": 1250},
								{"customer_name": "Ignored Customer", "opening_amount": 0},
							]
						),
					}
				),
				"Sales",
			)

		self.assertEqual(created, ["SI-starter-customer"])
		start_import.assert_called_once()
		invoices = start_import.call_args.args[0]
		self.assertEqual(len(invoices), 1)
		self.assertEqual(invoices[0].party, "Starter Customer")
		self.assertEqual(invoices[0].outstanding_amount, 1250)
		self.assertEqual(tool.company, "_Test Company")
		self.assertEqual(tool.invoice_type, "Sales")

	def test_create_bank_balance_creates_opening_journal_entry(self):
		journal_entry = MagicMock()
		journal_entry.name = "JE-BANK-starter-bank----tc"

		with (
			patch.object(starter_data, "_get_account", return_value="Opening Equity - _TC"),
			patch.object(starter_data, "_get_or_create_bank_account", return_value="Starter Bank - _TC"),
			patch.object(starter_data.frappe, "defaults") as defaults,
			patch.object(starter_data.frappe, "get_cached_value", return_value="_TC"),
			patch.object(starter_data.frappe.db, "exists", return_value=None),
			patch.object(starter_data.frappe, "get_doc", return_value=journal_entry) as get_doc,
			patch.object(starter_data, "nowdate", return_value="2026-07-03"),
		):
			defaults.get_global_default.return_value = "_Test Company"
			created = starter_data.create_bank_balance(
				frappe._dict(
					{
						"company_name": "_Test Company",
						"starter_bank_balance": json.dumps(
							[{"account_name": "Starter Bank", "amount": 3000}]
						),
					}
				)
			)

		self.assertEqual(created, ["JE-BANK-starter-bank----tc"])
		journal_entry_payload = get_doc.call_args.args[0]
		self.assertEqual(journal_entry_payload["name"], "JE-BANK-starter-bank----tc")
		self.assertEqual(journal_entry_payload["doctype"], "Journal Entry")
		self.assertEqual(journal_entry_payload["voucher_type"], "Opening Entry")
		self.assertEqual(journal_entry_payload["is_opening"], "Yes")
		self.assertEqual(
			journal_entry_payload["accounts"],
			[
				{"account": "Starter Bank - _TC", "debit_in_account_currency": 3000},
				{"account": "Opening Equity - _TC", "credit_in_account_currency": 3000},
			],
		)
		journal_entry.insert.assert_called_once_with(
			ignore_permissions=True, set_name="JE-BANK-starter-bank----tc"
		)
		journal_entry.submit.assert_called_once()


class TestSetupWizardStarterData(unittest.TestCase):
	def test_setup_stages_include_starter_data_stage_only_when_needed(self):
		stages_without_starter_data = setup_wizard.get_setup_stages({"country": "India"})
		self.assertNotIn(
			"Creating starter records", [stage.get("status") for stage in stages_without_starter_data]
		)

		starter_args = {"starter_customers": json.dumps([{"customer_name": "Starter Customer"}])}
		stages = setup_wizard.get_setup_stages(starter_args)
		stage_statuses = [stage.get("status") for stage in stages]

		self.assertEqual(
			stage_statuses,
			[
				"Installing presets",
				"Setting up company",
				"Setting defaults",
				"Creating starter records",
				"Personalizing your setup",
			],
		)
		starter_stage = stages[3]
		self.assertEqual(starter_stage["tasks"][0]["fn"], setup_wizard.setup_starter_data)
		self.assertEqual(
			starter_stage["tasks"][0]["args"].starter_customers, starter_args["starter_customers"]
		)

	def test_setup_complete_runs_starter_data_after_defaults(self):
		call_order = []
		args = {"starter_customers": json.dumps([{"customer_name": "Starter Customer"}])}

		with (
			patch.object(
				setup_wizard, "stage_fixtures", side_effect=lambda _args: call_order.append("fixtures")
			) as stage_fixtures,
			patch.object(
				setup_wizard, "setup_company", side_effect=lambda _args: call_order.append("company")
			) as setup_company,
			patch.object(
				setup_wizard, "setup_defaults", side_effect=lambda _args: call_order.append("defaults")
			) as setup_defaults,
			patch.object(
				setup_wizard, "setup_starter_data", side_effect=lambda _args: call_order.append("starter")
			) as setup_starter_data,
		):
			setup_wizard.setup_complete(args)

		self.assertEqual(call_order, ["fixtures", "company", "defaults", "starter"])
		stage_fixtures.assert_called_once()
		setup_company.assert_called_once()
		setup_defaults.assert_called_once()
		setup_starter_data.assert_called_once()
		self.assertEqual(setup_starter_data.call_args.args[0].starter_customers, args["starter_customers"])

	def test_setup_complete_skips_starter_data_when_empty(self):
		call_order = []

		with (
			patch.object(
				setup_wizard, "stage_fixtures", side_effect=lambda _args: call_order.append("fixtures")
			),
			patch.object(
				setup_wizard, "setup_company", side_effect=lambda _args: call_order.append("company")
			),
			patch.object(
				setup_wizard, "setup_defaults", side_effect=lambda _args: call_order.append("defaults")
			),
			patch.object(setup_wizard, "setup_starter_data") as setup_starter_data,
		):
			setup_wizard.setup_complete({"country": "India"})

		self.assertEqual(call_order, ["fixtures", "company", "defaults"])
		setup_starter_data.assert_not_called()
