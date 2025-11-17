import frappe
from frappe.tests.utils import FrappeTestCase
from frappe import _dict
from erpnext.accounts.report.gross_and_net_profit_report import (
	gross_and_net_profit_report as r,
)


class TestProfitAndLossStatement(FrappeTestCase):
	def _exec(self, filters):
		ret = r.execute(filters)
		if isinstance(ret, tuple):
			return ret[0], ret[1]
		return ret, []

	def _mk_filters(self, **kw):
		base = dict(
			from_fiscal_year="2025",
			to_fiscal_year="2025",
			period_start_date="2025-04-01",
			period_end_date="2026-03-31",
			filter_based_on="Fiscal Year",
			periodicity="Monthly",
			accumulated_values=0,
			company="_Test Company",
			presentation_currency="INR",
		)
		base.update(kw)
		return frappe._dict(base)

	def test_execute_when_nothing_included_in_gross_TC_ACC_407(self):
		# Monkeypatch helpers
		orig_get_period_list = r.get_period_list
		orig_get_data = r.get_data
		orig_get_columns = r.get_columns

		r.get_period_list = lambda *a, **k: [dict(key="P1")]
		r.get_data = lambda *a, **k: []
		r.get_columns = lambda *a, **k: [{"label": "Dummy"}]

		try:
			cols, data = self._exec(self._mk_filters())
			self.assertIsInstance(cols, list)
			self.assertEqual(len(data), 1)
			self.assertTrue(
				any("Nothing is included in gross" in (row.get("account_name") or "") for row in data)
			)
		finally:
			r.get_period_list = orig_get_period_list
			r.get_data = orig_get_data
			r.get_columns = orig_get_columns

	def test_execute_full_flow_including_gross_and_net_profit_TC_ACC_408(self):
		period_list = [_dict(key="P1"), _dict(key="P2")]

		income_rows = [
			{
				"account": "INC-G",
				"account_name": "INC-G",
				"is_group": 1,
				"parent_account": "",
				"include_in_gross": 1,
				"P1": 0,
				"P2": 0,
				"total": 0,
			},
			{
				"account": "G-Empty",
				"account_name": "G-Empty",
				"is_group": 1,
				"parent_account": "",
				"include_in_gross": 1,
				"P1": 0,
				"P2": 0,
				"total": 0,
			},
			{
				"account": "INC-1",
				"account_name": "INC-1",
				"is_group": 0,
				"parent_account": "INC-G",
				"include_in_gross": 1,
				"P1": 100,
				"P2": 50,
				"total": 150,
			},
			{
				"account": "INC-2",
				"account_name": "INC-2",
				"is_group": 0,
				"parent_account": "INC-G",
				"include_in_gross": 0,
				"P1": 5,
				"P2": 5,
				"total": 10,
			},
		]

		expense_rows = [
			{
				"account": "EXP-G",
				"account_name": "EXP-G",
				"is_group": 1,
				"parent_account": "",
				"include_in_gross": 1,
				"P1": 0,
				"P2": 0,
				"total": 0,
			},
			{
				"account": "EXP-1",
				"account_name": "EXP-1",
				"is_group": 0,
				"parent_account": "EXP-G",
				"include_in_gross": 1,
				"P1": 60,
				"P2": 60,
				"total": 120,
			},
			{
				"account": "EXP-2",
				"account_name": "EXP-2",
				"is_group": 0,
				"parent_account": "EXP-G",
				"include_in_gross": 0,
				"P1": 15,
				"P2": 15,
				"total": 30,
			},
		]

		orig_get_period_list = r.get_period_list
		orig_get_data = r.get_data
		orig_get_columns = r.get_columns

		r.get_period_list = lambda *a, **k: period_list

		def fake_get_data(company, root_type, bal_side, plist, **kw):
			return income_rows if root_type == "Income" else expense_rows

		r.get_data = fake_get_data
		r.get_columns = lambda *a, **k: [{"label": "Account"}]

		def _label(row):
			nm = row.get("account_name") or row.get("account") or ""
			if isinstance(nm, str):
				return nm.strip("'\"")
			return nm

		try:
			cols, data = self._exec(self._mk_filters())

			# verify header exists
			self.assertTrue(any(_label(row) == "Included in Gross Profit" for row in data))
			# empty group removed
			self.assertFalse(any(row.get("account") == "G-Empty" for row in data))

			gp_list = [row for row in data if _label(row) == "Gross Profit"]
			self.assertTrue(gp_list, "Gross Profit row not found")
			gp = gp_list[0]

			if "currency" in gp:
				self.assertEqual(gp["currency"], "INR")
			if "P1" in gp:
				self.assertEqual(gp["P1"], 40)
			if "P2" in gp:
				self.assertEqual(gp["P2"], -10)
			if "total" in gp:
				self.assertEqual(gp["total"], 30)

			np_list = [row for row in data if _label(row) == "Net Profit"]
			self.assertTrue(np_list, "Net Profit row not found")
			np = np_list[0]
			if "currency" in np:
				self.assertEqual(np["currency"], "INR")
			if "P1" in np:
				self.assertEqual(np["P1"], 30)
			if "P2" in np:
				self.assertEqual(np["P2"], -20)
			if "total" in np:
				self.assertEqual(np["total"], 10)

		finally:
			r.get_period_list = orig_get_period_list
			r.get_data = orig_get_data
			r.get_columns = orig_get_columns

	def test_get_revenue_removes_empty_group_and_adjusts_totals_TC_ACC_409(self):
		plist = [_dict(key="P1"), _dict(key="P2")]
		rows = [
			{
				"account": "G",
				"is_group": 1,
				"parent_account": "",
				"include_in_gross": 1,
				"P1": 0,
				"P2": 0,
				"total": 0,
			},
			{
				"account": "G-EMPTY",
				"is_group": 1,
				"parent_account": "",
				"include_in_gross": 1,
				"P1": 0,
				"P2": 0,
				"total": 0,
			},
			{
				"account": "L1",
				"is_group": 0,
				"parent_account": "G",
				"include_in_gross": 1,
				"P1": 10,
				"P2": 20,
				"total": 30,
			},
			{
				"account": "L2",
				"is_group": 0,
				"parent_account": "G",
				"include_in_gross": 0,
				"P1": 1,
				"P2": 2,
				"total": 3,
			},
		]
		rev = r.get_revenue(rows, plist)
		self.assertFalse(any(rr["account"] == "G-EMPTY" for rr in rev))
		g = next(rr for rr in rev if rr["account"] == "G")
		self.assertEqual(g["P1"], 10)
		self.assertEqual(g["P2"], 20)
		g["P1"] = 999
		self.assertEqual(rows[0]["P1"], 0)  # original rows remain intact

	def test_get_profit_currency_fallback_and_consolidated_TC_ACC_410(self):
		orig_get_cached_value = frappe.get_cached_value
		frappe.get_cached_value = lambda doctype, name, field: "USD"
		try:
			plist = ["Q1", "Q2"]
			gross_income = [{"Q1": 100, "Q2": 50, "total": 150}]
			gross_expense = [{"Q1": 60, "Q2": 80, "total": 140}]
			row = r.get_profit(
				gross_income,
				gross_expense,
				plist,
				"_Test Company",
				"Gross Profit",
				currency=None,
				consolidated=True,
			)
			self.assertEqual(row["currency"], "USD")
			self.assertEqual(row["Q1"], 40)
			self.assertEqual(row["Q2"], -30)
			self.assertEqual(row["total"], 10)
		finally:
			frappe.get_cached_value = orig_get_cached_value

	def test_get_net_profit_currency_fallback_TC_ACC_411(self):
		orig_get_cached_value = frappe.get_cached_value
		frappe.get_cached_value = lambda doctype, name, field: "EUR"
		try:
			plist = [_dict(key="M1"), _dict(key="M2")]
			gross_income = [{"M1": 100, "M2": 50, "total": 0}]
			non_gross_income = [{"M1": 5, "M2": 5, "total": 0}]
			gross_expense = [{"M1": 60, "M2": 70, "total": 0}]
			non_gross_expense = [{"M1": 10, "M2": 15, "total": 0}]
			row = r.get_net_profit(
				non_gross_income,
				gross_income,
				gross_expense,
				non_gross_expense,
				plist,
				"_Test Company",
				currency=None,
				consolidated=False,
			)
			self.assertEqual(row["currency"], "EUR")
			self.assertEqual(row["total"], 5)
			if "M1" in row:
				self.assertEqual(row["M1"], 35)
			if "M2" in row:
				self.assertEqual(row["M2"], -30)
		finally:
			frappe.get_cached_value = orig_get_cached_value
