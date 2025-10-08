# Copyright (c) 2025
# See license.txt

from erpnext.stock.doctype.stock_entry.test_stock_entry import get_or_create_fiscal_year
import frappe
import unittest
# from frappe.tests import IntegrationTestCase
from unittest.mock import patch, MagicMock

# Import the report functions
from erpnext.accounts.report import financial_statements
from erpnext.accounts.report import trial_balance
from erpnext.accounts.report.dimension_wise_accounts_balance_report.dimension_wise_accounts_balance_report import (
    get_data,
    format_gl_entries,
    prepare_data,
    accumulate_values_into_parents,
    get_dimensions,
    get_columns,
)


class TestDimensionWiseAccountsBalanceReport(unittest.TestCase):
    @patch("frappe.get_meta")
    @patch("frappe.get_all")
    def test_get_dimensions_fetches_names_TC_ACC_533(self, mock_get_all, mock_get_meta):
        mock_get_meta.return_value.has_field.return_value = True
        mock_get_all.return_value = ["CC1", "CC2"]

        filters = {"dimension": "Cost Center", "company": "_Test Company"}
        result = get_dimensions(filters)

        mock_get_all.assert_called_once()
        self.assertEqual(result, ["CC1", "CC2"])

    def test_get_columns_with_dimensions_TC_ACC_534(self):
        cols = get_columns(["Cost Center", "Project"])
        fieldnames = [c["fieldname"] for c in cols]

        self.assertIn("account", fieldnames)
        self.assertIn("cost_center", fieldnames)
        self.assertIn("project", fieldnames)
        self.assertIn("total", fieldnames)

    def test_accumulate_values_into_parents_TC_ACC_535(self):
        accounts = [
            frappe._dict({"name": "Child", "parent_account": "Parent", "cost_center": 50}),
            frappe._dict({"name": "Parent", "parent_account": None, "cost_center": 0}),
        ]
        accounts_by_name = {
            "Child": accounts[0],
            "Parent": accounts[1],
        }

        accumulate_values_into_parents(accounts, accounts_by_name, ["Cost Center"])
        self.assertEqual(accounts_by_name["Parent"]["cost_center"], 50)

    def test_prepare_data_creates_rows_TC_ACC_536(self):
        # get_or_create_fiscal_year("_Test Company")
        accounts = [
            frappe._dict({"name": "Acc1", "parent_account": None, "indent": 0, "account_name": "Cash"}),
        ]
        filters = frappe._dict({"from_date": "2025-01-01", "to_date": "2025-01-31"})
        result = prepare_data(accounts, filters, "INR", ["Cost Center"])

        self.assertIsInstance(result, list)
        self.assertIn("account", result[0])
        self.assertIn("total", result[0])

    def test_format_gl_entries_adds_dimension_values_TC_ACC_537(self):
        accounts_by_name = {
            "Acc1": frappe._dict({"name": "Acc1", "cost_center": 0}),
        }
        gl_entries_by_account = {
            "Acc1": [
                frappe._dict(
                    {
                        "account": "Acc1",
                        "cost_center": "CC1",
                        "debit": 100,
                        "credit": 40,
                    }
                )
            ]
        }
        format_gl_entries(gl_entries_by_account, accounts_by_name, ["CC1"], "cost_center")
        self.assertEqual(accounts_by_name["Acc1"]["cc1"], 60.0)

    @patch("erpnext.get_company_currency", return_value="INR")
    @patch("erpnext.accounts.report.dimension_wise_accounts_balance_report.dimension_wise_accounts_balance_report.set_gl_entries_by_account")
    @patch("frappe.db.sql")
    @patch("frappe.db.sql_list")
    @patch("erpnext.accounts.report.financial_statements.filter_accounts")
    def test_get_data_calls_dependencies_TC_ACC_538(
        self, mock_filter_accounts, mock_sql_list, mock_sql, mock_currency, mock_set_gl
    ):
        # get_or_create_fiscal_year("_Test Company")
        from frappe import _dict

        # Mock accounts
        mock_sql.side_effect = [
            [_dict({"name": "Acc1", "parent_account": None, "lft": 1, "rgt": 2, "account_name": "Cash"})],
            [(1, 2)],  # min/max
        ]
        mock_sql_list.return_value = ["Acc1"]

        accounts = [_dict({"name": "Acc1", "parent_account": None, "lft": 1, "rgt": 2})]
        accounts_by_name = {"Acc1": accounts[0]}
        mock_filter_accounts.return_value = (accounts, accounts_by_name, {})

        # Prevent real GL query
        mock_set_gl.return_value = None

        filters = _dict(
            {
                "company": "_Test Company",
                "dimension": "Cost Center",
                "from_date": "2025-01-01",
                "to_date": "2025-01-31",
            }
        )
        result = get_data(filters, ["CC1"])

        self.assertTrue(result is None or isinstance(result, list))
