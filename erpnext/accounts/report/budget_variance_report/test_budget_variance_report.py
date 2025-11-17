import datetime
import frappe
from frappe.tests.utils import FrappeTestCase
from unittest.mock import patch
from frappe import _dict
from erpnext.accounts.report.budget_variance_report.budget_variance_report import execute


class TestBudgetVarianceReport(FrappeTestCase):
    def test_execute_full_flow_TC_ACC_451(self):
        filters = _dict({
            "company": "Test Co",
            "budget_against": "Cost Center",
            "from_fiscal_year": "2023",
            "to_fiscal_year": "2023",
            "period": "Monthly",
        })

        # Fake data for DB calls
        fake_fiscal_year = [("2023",)]
        fake_budget_detail = [
            _dict(
                budget_against="CC1",
                monthly_distribution=None,
                account="Expense - TC",
                budget_amount=1200,
                fiscal_year="2023",
            )
        ]
        fake_target_dist = [
            _dict(name="Dist1", month="January", percentage_allocation=100)
        ]
        fake_actual = [
            _dict(
                account="Expense - TC",
                debit=100,
                credit=0,
                fiscal_year="2023",
                month_name="January",
                budget_against="CC1",
            )
        ]

        with patch("erpnext.accounts.report.budget_variance_report.budget_variance_report.frappe.db.sql_list") as mock_sql_list, \
             patch("erpnext.accounts.report.budget_variance_report.budget_variance_report.frappe.db.sql") as mock_sql, \
             patch("erpnext.accounts.report.budget_variance_report.budget_variance_report.frappe.db.get_value", return_value=(1, 2)), \
             patch("erpnext.accounts.report.budget_variance_report.budget_variance_report.frappe.get_cached_value",
                   return_value=(datetime.date(2023, 1, 1), datetime.date(2023, 12, 31))):

            # sql_list for cost centers
            mock_sql_list.return_value = ["CC1"]

            # sql side_effect for different queries
            def sql_side_effect(query, *args, **kwargs):
                if "tabFiscal Year" in query:
                    return fake_fiscal_year
                if "tabBudget" in query:
                    return fake_budget_detail
                if "tabMonthly Distribution Percentage" in query:
                    return fake_target_dist
                if "tabGL Entry" in query:   # relaxed match
                    return fake_actual
                return []

            mock_sql.side_effect = sql_side_effect

            # ---- Run the report ----
            cols, data, _, chart = execute(filters)

            # Columns contain expected labels
            labels = [c["label"] for c in cols]
            self.assertTrue(any("Budget" in l for l in labels))
            self.assertTrue(any("Actual" in l for l in labels))
            self.assertTrue(any("Variance" in l for l in labels))
            
            # Data should not be empty
            self.assertTrue(len(data) > 0)

            # Check cost center and account in row contents
            flat_rows = [str(r) for r in data]
            self.assertTrue(any("CC1" in r for r in flat_rows))
            self.assertTrue(any("Expense - TC" in r for r in flat_rows))

            # Variance check: budget - actual == variance
            for row in data:
                if "Expense - TC" in row:
                    budget, actual, variance = row[2], row[3], row[4]
                    self.assertEqual(budget - actual, variance)


            # Chart should be returned with datasets
            self.assertIsNotNone(chart)
            self.assertIn("datasets", chart["data"])
