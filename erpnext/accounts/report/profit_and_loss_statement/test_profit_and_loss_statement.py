# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

import frappe
from frappe.desk.query_report import export_query
from frappe.utils import add_days, getdate, today

from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.report.financial_statements import get_period_list
from erpnext.accounts.report.profit_and_loss_statement.profit_and_loss_statement import execute
from erpnext.accounts.test.accounts_mixin import AccountsTestMixin
from erpnext.tests.utils import ERPNextTestSuite


class TestProfitAndLossStatement(ERPNextTestSuite, AccountsTestMixin):
	def setUp(self):
		self.create_company()
		self.create_customer()
		self.create_item()

	def create_sales_invoice(self, qty=1, rate=150, no_payment_schedule=False, do_not_submit=False):
		frappe.set_user("Administrator")
		si = create_sales_invoice(
			item=self.item,
			company=self.company,
			customer=self.customer,
			debit_to=self.debit_to,
			posting_date=today(),
			parent_cost_center=self.cost_center,
			cost_center=self.cost_center,
			rate=rate,
			price_list_rate=rate,
			qty=qty,
			do_not_save=1,
		)
		si = si.save()
		if not do_not_submit:
			si = si.submit()
		return si

	def get_fiscal_year(self):
		active_fy = frappe.db.get_all(
			"Fiscal Year",
			filters={"disabled": 0, "year_start_date": ("<=", today()), "year_end_date": (">=", today())},
		)[0]
		return frappe.get_doc("Fiscal Year", active_fy.name)

	def get_report_filters(self):
		fy = self.get_fiscal_year()
		return frappe._dict(
			company=self.company,
			from_fiscal_year=fy.name,
			to_fiscal_year=fy.name,
			period_start_date=fy.year_start_date,
			period_end_date=fy.year_end_date,
			filter_based_on="Fiscal Year",
			periodicity="Monthly",
			accumulated_values=False,
		)

	def test_profit_and_loss_output_and_summary(self):
		self.create_sales_invoice(qty=1, rate=150)

		filters = self.get_report_filters()
		period_list = get_period_list(
			filters.from_fiscal_year,
			filters.to_fiscal_year,
			filters.period_start_date,
			filters.period_end_date,
			filters.filter_based_on,
			filters.periodicity,
			company=filters.company,
		)

		result = execute(filters)[1]
		current_period = next(x for x in period_list if x.from_date <= getdate() and x.to_date >= getdate())
		current_period_key = current_period.key
		without_current_period = [x for x in period_list if x.key != current_period.key]
		# all period except current period(whence invoice was posted), should be '0'
		for acc in result:
			if acc:
				with self.subTest(acc=acc):
					for period in without_current_period:
						self.assertEqual(acc[period.key], 0)

		for acc in result:
			if acc:
				with self.subTest(current_period_key=current_period_key):
					self.assertEqual(acc[current_period_key], 150)
					self.assertEqual(acc["total"], 150)

	def test_p_and_l_export(self):
		self.create_sales_invoice(qty=1, rate=150)

		filters = self.get_report_filters()
		frappe.local.form_dict = frappe._dict(
			{
				"report_name": "Profit and Loss Statement",
				"file_format_type": "CSV",
				"filters": filters,
				"visible_idx": [0, 1, 2, 3, 4, 5, 6],
			}
		)
		export_query()
		contents = frappe.response["filecontent"].decode()
		sales_account = frappe.db.get_value("Company", self.company, "default_income_account")

		self.assertIn(sales_account, contents)

	def test_accumulate_filter(self):
		# ensure 2 fiscal years
		cur_fy = self.get_fiscal_year()
		find_for = add_days(cur_fy.year_start_date, -1)
		_x = frappe.db.get_all(
			"Fiscal Year",
			filters={"disabled": 0, "year_start_date": ("<=", find_for), "year_end_date": (">=", find_for)},
		)[0]
		prev_fy = frappe.get_doc("Fiscal Year", _x.name)
		prev_fy.append("companies", {"company": self.company})
		prev_fy.save()

		# make SI on both of them
		prev_fy_si = self.create_sales_invoice(qty=1, rate=450, do_not_submit=True)
		prev_fy_si.posting_date = add_days(prev_fy.year_end_date, -1)
		prev_fy_si.save().submit()
		income_acc = prev_fy_si.items[0].income_account

		self.create_sales_invoice(qty=1, rate=120)

		# Unaccumualted
		filters = frappe._dict(
			company=self.company,
			from_fiscal_year=prev_fy.name,
			to_fiscal_year=cur_fy.name,
			period_start_date=prev_fy.year_start_date,
			period_end_date=cur_fy.year_end_date,
			filter_based_on="Date Range",
			periodicity="Yearly",
			accumulated_values=False,
		)
		result = execute(filters)
		columns = [result[0][4], result[0][5]]
		expected = {
			"account": income_acc,
			columns[0].get("fieldname"): 450.0,
			columns[1].get("fieldname"): 120.0,
		}
		actual = [x for x in result[1] if x.get("account") == income_acc]
		self.assertEqual(len(actual), 1)
		actual = actual[0]
		for key in expected.keys():
			with self.subTest(key=key):
				self.assertEqual(expected.get(key), actual.get(key))

		# accumualted
		filters.update({"accumulated_values": True})
		expected = {
			"account": income_acc,
			columns[0].get("fieldname"): 450.0,
			columns[1].get("fieldname"): 570.0,
		}
		result = execute(filters)
		columns = [result[0][4], result[0][5]]
		actual = [x for x in result[1] if x.get("account") == income_acc]
		self.assertEqual(len(actual), 1)
		actual = actual[0]
		for key in expected.keys():
			with self.subTest(key=key):
				self.assertEqual(expected.get(key), actual.get(key))


class TestProfitAndLossDimensionWise(ERPNextTestSuite, AccountsTestMixin):
	def setUp(self):
		self.create_company()
		self.create_customer()
		self.create_item()

	def get_fiscal_year(self):
		active_fy = frappe.db.get_all(
			"Fiscal Year",
			filters={"disabled": 0, "year_start_date": ("<=", today()), "year_end_date": (">=", today())},
		)[0]
		return frappe.get_doc("Fiscal Year", active_fy.name)

	def _make_si(self, cost_center, rate):
		frappe.set_user("Administrator")
		si = create_sales_invoice(
			item=self.item,
			company=self.company,
			customer=self.customer,
			debit_to=self.debit_to,
			posting_date=today(),
			parent_cost_center=self.cost_center,
			cost_center=cost_center,
			rate=rate,
			price_list_rate=rate,
			qty=1,
			do_not_save=1,
		)
		return si.save().submit()

	def _dim_filters(self, accumulated_values=False, periodicity="Yearly"):
		fy = self.get_fiscal_year()
		return frappe._dict(
			company=self.company,
			from_fiscal_year=fy.name,
			to_fiscal_year=fy.name,
			period_start_date=fy.year_start_date,
			period_end_date=fy.year_end_date,
			filter_based_on="Fiscal Year",
			periodicity=periodicity,
			accumulated_values=accumulated_values,
			group_by_dimension="Cost Center",
			show_zero_values=0,
			finance_book=None,
			presentation_currency=None,
		)

	def _income_row(self, result):
		return next(
			(r for r in result[1] if r and r.get("account") == self.income_account),
			None,
		)

	def test_dim_yearly_not_accumulated(self):
		"""Two cost centers → each gets its own column; Total = sum of both."""
		cc2_full = f"_Test Dim PL CC1 - {self.company_abbr}"
		create_cost_center(cost_center_name="_Test Dim PL CC1", company=self.company)

		self._make_si(self.cost_center, rate=300)
		self._make_si(cc2_full, rate=200)

		result = execute(self._dim_filters(accumulated_values=False))

		income_row = self._income_row(result)
		self.assertIsNotNone(income_row)
		self.assertEqual(income_row["total"], 500.0)

		summary = {s["label"]: s["value"] for s in (result[4] or [])}
		self.assertEqual(summary.get("Total Income"), 500.0)

	def test_dim_yearly_accumulated(self):
		"""
		accumulated_values=True, Yearly: one period per dim.
		Total = last-period per dim summed (not double-counted).
		"""
		cc2_full = f"_Test Dim PL CC2 - {self.company_abbr}"
		create_cost_center(cost_center_name="_Test Dim PL CC2", company=self.company)

		self._make_si(self.cost_center, rate=400)
		self._make_si(cc2_full, rate=100)

		result = execute(self._dim_filters(accumulated_values=True))

		income_row = self._income_row(result)
		self.assertIsNotNone(income_row)
		self.assertEqual(income_row["total"], 500.0)

		summary = {s["label"]: s["value"] for s in (result[4] or [])}
		self.assertEqual(summary.get("Total Income"), 500.0)

	def test_dim_net_profit_total(self):
		"""Profit for the year Total = sum of last-period per dim, not sum of all cells."""
		cc2_full = f"_Test Dim PL CC3 - {self.company_abbr}"
		create_cost_center(cost_center_name="_Test Dim PL CC3", company=self.company)

		self._make_si(self.cost_center, rate=600)
		self._make_si(cc2_full, rate=150)

		result = execute(self._dim_filters(accumulated_values=True))

		profit_row = next(
			(r for r in result[1] if r and "Profit for the year" in (r.get("account") or "")),
			None,
		)
		self.assertIsNotNone(profit_row)
		self.assertEqual(profit_row["total"], 750.0)

	def test_dim_columns_segregated(self):
		"""A dim's period column must not contain data from another dim."""
		cc2_full = f"_Test Dim PL CC4 - {self.company_abbr}"
		create_cost_center(cost_center_name="_Test Dim PL CC4", company=self.company)

		self._make_si(self.cost_center, rate=300)
		self._make_si(cc2_full, rate=200)

		result = execute(self._dim_filters(accumulated_values=False))
		columns = result[0]
		period_cols = [c for c in columns if c.get("fieldtype") == "Currency" and c["fieldname"] != "total"]

		income_row = self._income_row(result)
		self.assertIsNotNone(income_row)

		col_values = [income_row.get(c["fieldname"], 0) for c in period_cols]
		self.assertIn(300.0, col_values)
		self.assertIn(200.0, col_values)

	def test_dim_quarterly_not_accumulated(self):
		"""Quarterly + not accumulated: Total = sum of all period activity."""
		cc2_full = f"_Test Dim PL CC5 - {self.company_abbr}"
		create_cost_center(cost_center_name="_Test Dim PL CC5", company=self.company)

		self._make_si(self.cost_center, rate=500)
		self._make_si(cc2_full, rate=250)

		result = execute(self._dim_filters(accumulated_values=False, periodicity="Quarterly"))

		income_row = self._income_row(result)
		self.assertIsNotNone(income_row)
		self.assertEqual(income_row["total"], 750.0)

	def test_dim_quarterly_accumulated(self):
		"""
		Quarterly + accumulated_values=True: Total = last-quarter balance per dim summed,
		not sum of all quarterly cells.
		"""
		cc2_full = f"_Test Dim PL CC6 - {self.company_abbr}"
		create_cost_center(cost_center_name="_Test Dim PL CC6", company=self.company)

		self._make_si(self.cost_center, rate=600)
		self._make_si(cc2_full, rate=300)

		result = execute(self._dim_filters(accumulated_values=True, periodicity="Quarterly"))

		income_row = self._income_row(result)
		self.assertIsNotNone(income_row)
		# last-quarter per dim: each dim has only this period, so total = 600 + 300 = 900
		self.assertEqual(income_row["total"], 900.0)

		summary = {s["label"]: s["value"] for s in (result[4] or [])}
		self.assertEqual(summary.get("Total Income"), 900.0)
