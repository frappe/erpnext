# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

import frappe
from frappe.desk.query_report import export_query
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate, today

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.report.financial_statements import get_period_list
from erpnext.accounts.report.profit_and_loss_statement.profit_and_loss_statement import execute
from erpnext.accounts.test.accounts_mixin import AccountsTestMixin


class TestProfitAndLossStatement(AccountsTestMixin, IntegrationTestCase):
	def setUp(self):
		self.create_company()
		self.create_customer()
		self.create_item()

	def tearDown(self):
		frappe.db.rollback()

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
