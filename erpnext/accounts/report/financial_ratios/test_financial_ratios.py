from datetime import date
from unittest.mock import patch
import frappe
from frappe.tests.utils import FrappeTestCase
from erpnext.accounts.report.financial_ratios import financial_ratios as fr

def _period(key, label, f, t):
    return frappe._dict({"key": key, "label": label, "from_date": f, "to_date": t})

class TestFinancialRatios(FrappeTestCase):
    def _make_fake_periods(self):
        # Two fiscal-year periods (keys are what the report uses to place values)
        return [
            _period("FY24", "FY 2023-24", date(2024, 4, 1), date(2025, 3, 31)),
            _period("FY25", "FY 2024-25", date(2025, 4, 1), date(2026, 3, 31)),
        ]

    def _fake_get_data(self, company, root_type, drcr, period_list, only_current_fiscal_year=False, filters=None):
        if root_type == "Asset":
            return [
                {"is_group": 1, "parent_account": None, "account_type": "", "FY24": 1000, "FY25": 1200},
                {"is_group": 1, "parent_account": "Assets", "account_type": "Current Asset", "FY24": 100, "FY25": 110},
                {"is_group": 0, "parent_account": "Current Assets", "account_type": "Bank", "FY24": 30, "FY25": 33},
                {"is_group": 0, "parent_account": "Current Assets", "account_type": "Cash", "FY24": 20, "FY25": 22},
                {"is_group": 0, "parent_account": "Current Assets", "account_type": "Receivable", "FY24": 10, "FY25": 11},
            ]
        if root_type == "Liability":
            return [
                {"is_group": 1, "parent_account": None, "account_type": "", "FY24": 400, "FY25": 480},
                {"is_group": 1, "parent_account": "Liabilities", "account_type": "Current Liability", "FY24": 50, "FY25": 55},
            ]
        if root_type == "Income":
            return [
                {"is_group": 1, "parent_account": None, "account_type": "", "FY24": 250, "FY25": 270},
                {"is_group": 1, "parent_account": "Income", "account_type": "Direct Income", "FY24": 200, "FY25": 220},
            ]
        if root_type == "Expense":
            return [
                {"is_group": 1, "parent_account": None, "account_type": "", "FY24": -50, "FY25": -60},
                {"is_group": 0, "parent_account": "Expense", "account_type": "Cost of Goods Sold", "FY24": 40, "FY25": 44},
                {"is_group": 0, "parent_account": "Expense", "account_type": "Cost of Goods Sold", "FY24": 40, "FY25": 44},
                {"is_group": 1, "parent_account": "Expense", "account_type": "Direct Expense", "FY24": 10, "FY25": 10},
            ]
        return []

    def _fake_get_fiscal_year(self, fiscal_year=None, *args, **kwargs):
        if str(fiscal_year).startswith("2024"):
            return (fiscal_year, date(2024, 4, 1), date(2025, 3, 31))
        return (fiscal_year, date(2025, 4, 1), date(2026, 3, 31))

    def _fake_get_balance_on(self, date=None, company=None, account=None, account_type=None):
        return 90

    def test_execute_happy_path_TC_ACC_369(self):
        periods = self._make_fake_periods()
        filters = frappe._dict(
            {
                "company": "_Test Company",
                "from_fiscal_year": "2024-2025",
                "to_fiscal_year": "2025-2026",
                "periodicity": "Yearly",
            }
        )

        with patch.object(fr, "get_period_list", return_value=periods), \
             patch.object(fr, "get_data", side_effect=self._fake_get_data), \
             patch.object(fr, "get_fiscal_year", side_effect=self._fake_get_fiscal_year), \
             patch.object(fr, "get_balance_on", side_effect=self._fake_get_balance_on), \
             patch.object(fr.frappe.db, "get_single_value", return_value=2):

            columns, data = fr.execute(filters)

        fieldnames = [c.get("fieldname") for c in columns]
        self.assertEqual(fieldnames[0], "ratio")
        self.assertIn("FY24", fieldnames)
        self.assertIn("FY25", fieldnames)

        def row(named):
            for r in data:
                if r.get("ratio") == named:
                    return r
            return None

        
        current_ratio = row("Current Ratio")
        quick_ratio = row("Quick Ratio")
        self.assertIsNotNone(current_ratio)
        self.assertIsNotNone(quick_ratio)

        self.assertAlmostEqual(current_ratio["FY24"], 2.00, places=2)
        self.assertAlmostEqual(quick_ratio["FY24"], 1.20, places=2)
        self.assertAlmostEqual(current_ratio["FY25"], 2.00, places=2)
        self.assertAlmostEqual(quick_ratio["FY25"], 1.20, places=2)

        debt_equity = row("Debt Equity Ratio")
        gross_profit = row("Gross Profit Ratio")
        net_profit = row("Net Profit Ratio")
        roa = row("Return on Asset Ratio")
        roe = row("Return on Equity Ratio")

        self.assertAlmostEqual(debt_equity["FY24"], 0.67, places=2)
        self.assertAlmostEqual(gross_profit["FY24"], 0.60, places=2)
        self.assertAlmostEqual(net_profit["FY24"], 1.00, places=2)
        self.assertAlmostEqual(roa["FY24"], 0.20, places=2)
        self.assertAlmostEqual(roe["FY24"], 0.33, places=2)

        
        self.assertAlmostEqual(debt_equity["FY25"], 0.67, places=2) 
        self.assertAlmostEqual(gross_profit["FY25"], 0.60, places=2)
        self.assertAlmostEqual(net_profit["FY25"], 0.95, places=2)  
        self.assertAlmostEqual(roa["FY25"], 0.18, places=2)         
        self.assertAlmostEqual(roe["FY25"], 0.29, places=2)         

        
        fat = row("Fixed Asset Turnover Ratio")
        dtr = row("Debtor Turnover Ratio")
        ctr = row("Creditor Turnover Ratio")
        itr = row("Inventory Turnover Ratio")

        
        self.assertAlmostEqual(fat["FY24"], 0.20, places=2)
        self.assertAlmostEqual(dtr["FY24"], 2.22, places=2)
        self.assertAlmostEqual(ctr["FY24"], 0.11, places=2)
        self.assertAlmostEqual(itr["FY24"], 0.89, places=2)
        self.assertAlmostEqual(fat["FY25"], 0.18, places=2)
        self.assertAlmostEqual(dtr["FY25"], 2.44, places=2)
        self.assertAlmostEqual(ctr["FY25"], 0.11, places=2)
        self.assertAlmostEqual(itr["FY25"], 0.98, places=2)
        self.assertTrue(any(r.get("ratio") == "Liquidity Ratios" for r in data))
        self.assertTrue(any(r.get("ratio") == "Solvency Ratios" for r in data))
        self.assertTrue(any(r.get("ratio") == "Turnover Ratios" for r in data))

        self.assertIn("period_start_date", filters)
        self.assertIn("period_end_date", filters)
        self.assertEqual(filters["filter_based_on"], "Fiscal Year")

    def test_calculate_ratio_and_zero_guard_TC_ACC_388(self):
        with patch.object(fr.frappe.db, "get_single_value", return_value=2):
            self.assertEqual(fr.calculate_ratio(10, 4, 2), 2.5)
            self.assertEqual(fr.calculate_ratio(10, 0, 2), 0)

    def test_setup_filters_sets_dates_from_fiscal_year_TC_ACC_389(self):
        filters = frappe._dict({"from_fiscal_year": "2024-2025", "to_fiscal_year": "2025-2026"})
        with patch.object(fr, "get_fiscal_year", side_effect=self._fake_get_fiscal_year):
            fr.setup_filters(filters)
        self.assertEqual(filters["period_start_date"], date(2024, 4, 1))
        self.assertEqual(filters["period_end_date"], date(2026, 3, 31))
