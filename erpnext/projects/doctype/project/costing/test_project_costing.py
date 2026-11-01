# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.classes.context_managers import freeze_time, patch_hooks
from frappe.utils import add_months, add_to_date, get_first_day, getdate, now_datetime, nowdate

from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.projects.doctype.project.costing.drivers import summarise_rate_gaps
from erpnext.projects.doctype.project.costing.project_costing import (
	CostingSummary,
	get_project_costing,
	monthly_rows,
	permitted_reports,
)
from erpnext.projects.doctype.project.costing.queries import ProjectCostQueries
from erpnext.projects.doctype.project.project import update_costing_and_billing
from erpnext.projects.doctype.project.test_project import issue_to_project, make_project
from erpnext.projects.doctype.timesheet.test_timesheet import make_timesheet
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.setup.doctype.employee.test_employee import make_employee
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.tests.utils import ERPNextTestSuite

UNPRICED_ACTIVITY = "_Test Unpriced Activity"
VIEWER = "costing-viewer@example.com"
ADD_GENERAL_LEDGER = "erpnext.projects.doctype.project.costing.test_project_costing.add_general_ledger"


class TestProjectCosting(ERPNextTestSuite):
	def test_summary_health_forecast_and_margins(self) -> None:
		"""Forecast scales cost by progress only while the project runs; health compares cost and
		forecast with the estimate; margins follow billing, contract and estimate."""
		running = summary(
			status="Open", percent_complete=50, estimate=1000, cost=600, billed=1500, contract=2000
		)
		self.assertEqual(running["forecast"], 1200)
		self.assertEqual(running["health"], "risk")
		self.assertEqual(running["margin"], 900)
		self.assertEqual(running["margin_percent"], 60)
		self.assertEqual(running["billed_percent"], 75)
		self.assertEqual(running["planned_margin"], 1000)

		self.assertEqual(summary(percent_complete=50, estimate=1000, cost=510)["health"], "ok")
		self.assertEqual(summary(percent_complete=0, estimate=1000, cost=1100)["health"], "over")
		self.assertEqual(summary(percent_complete=0, estimate=1000, cost=0)["health"], "empty")
		self.assertEqual(summary(percent_complete=0, cost=0)["health"], "empty")
		finished = summary(status="Completed", percent_complete=50, estimate=1000, cost=600)
		self.assertEqual((finished["forecast"], finished["health"]), (600, "ok"))

	def test_summary_without_estimate_contract_or_billing(self) -> None:
		bare = summary(percent_complete=40, cost=400)
		self.assertEqual(bare["health"], "none")
		self.assertIsNone(bare["variance"])
		self.assertIsNone(bare["margin_percent"])
		self.assertIsNone(bare["planned_margin"])
		self.assertTrue(bare["internal"])
		self.assertFalse(summary(customer="_Test Customer", cost=400)["internal"])

	def test_monthly_rows_fill_the_months_between(self) -> None:
		rows = monthly_rows({"labour": {"2025-11": 100.0}, "billed": {"2026-02": 50.0}})
		self.assertEqual([row["month"] for row in rows], ["2025-11", "2025-12", "2026-01", "2026-02"])
		self.assertEqual(rows[1], {"month": "2025-12", "labour": 0, "billed": 0})
		self.assertEqual(monthly_rows({"labour": {}}), [])

	def test_rate_gaps_flag_understated_labour(self) -> None:
		activities = [
			frappe._dict(name="Development", hours=92, amount=1840, unpriced_hours=0),
			frappe._dict(name=None, hours=3, amount=0, unpriced_hours=3),
			frappe._dict(name="Design", hours=5, amount=0, unpriced_hours=5),
		]
		gaps = summarise_rate_gaps(activities)
		self.assertEqual((gaps["hours"], gaps["share"], gaps["estimate"]), (8, 8, 160))
		self.assertTrue(gaps["understated"])
		self.assertIsNone(summarise_rate_gaps(activities[1:])["estimate"])

	def test_costing_matches_the_stored_totals(self) -> None:
		"""The tab computes live what the Project stores, and splits it out by invoice, order and person."""
		project = self.project_with_documents()
		update_costing_and_billing(project.name)
		project.reload()

		costing = get_project_costing(project.name)
		self.assertEqual(costing["errors"], {})
		stored_cost = (
			project.total_costing_amount + project.total_purchase_cost + project.total_consumed_material_cost
		)
		self.assertAlmostEqual(costing["summary"]["cost"], stored_cost, places=2)
		self.assertAlmostEqual(costing["summary"]["margin"], project.gross_margin, places=2)
		self.assertEqual(costing["summary"]["contract"], project.total_sales_amount)

		billing = costing["billing"]
		self.assertEqual(
			[invoice["amount"] for invoice in billing["invoices"]], [project.total_billed_amount]
		)
		self.assertEqual((billing["invoice_count"], billing["sales_order_count"]), (1, 1))
		self.assertEqual(costing["rate_gaps"]["hours"], 6)
		self.assertTrue(costing["rate_gaps"]["understated"])
		self.assertEqual(costing["drivers"]["activities"][0]["unpriced_hours"], 0)

	def test_invoice_filter_finds_the_counted_invoices(self) -> None:
		"""The Billing card's link to the invoice list filters by the invoice's project, by the
		items' project, or by name when the project's invoices mix the two, up to a limit."""
		project = make_project({"project_name": f"_Test Invoice Links {frappe.generate_hash(length=6)}"}).name
		invoice_for_project(project, qty=1)
		self.assertEqual(billing_of(project)["invoice_filter"], {"project": project})

		item_billed = make_project(
			{"project_name": f"_Test Item Links {frappe.generate_hash(length=6)}"}
		).name
		item_invoice_for_project(item_billed)
		self.assertEqual(
			billing_of(item_billed)["invoice_filter"], {"Sales Invoice Item.project": item_billed}
		)

		item_invoice = item_invoice_for_project(project)
		billing = billing_of(project)
		self.assertEqual(billing["invoice_filter"]["name"][0], "in")
		self.assertEqual(
			set(billing["invoice_filter"]["name"][1]), {row["name"] for row in billing["invoices"]}
		)
		self.assertIn(item_invoice, billing["invoice_filter"]["name"][1])

		with patch("erpnext.projects.doctype.project.costing.billing.NAME_FILTER_LIMIT", 1):
			self.assertIsNone(billing_of(project)["invoice_filter"])

	def test_viewer_without_cost_access_sees_totals_only(self) -> None:
		"""A Projects User sees the same totals, but not costing rates or the invoices behind them."""
		project = self.project_with_documents()
		cost = get_project_costing(project.name)["summary"]["cost"]

		frappe.set_user(make_viewer())
		costing = get_project_costing(project.name)
		frappe.set_user("Administrator")

		self.assertEqual(costing["errors"], {})
		self.assertEqual(
			costing["customer_name"], frappe.db.get_value("Customer", "_Test Customer", "customer_name")
		)
		self.assertFalse(costing["access"]["labour"])
		self.assertEqual(costing["summary"]["cost"], cost)
		self.assertIsNone(costing["billing"]["invoices"])
		self.assertIsNone(costing["rate_gaps"])
		self.assertNotIn("amount", costing["drivers"]["activities"][0])

	def test_lists_keep_to_the_documents_the_user_may_read(self) -> None:
		"""A user limited to their own Employee sees only their own time in the lists, while the
		totals still count everyone's."""
		project = self.project_with_documents()
		viewer = make_viewer()
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": viewer,
				"allow": "Employee",
				"for_value": self.priced_employee,
			}
		).insert()

		frappe.set_user(viewer)
		costing = get_project_costing(project.name)
		frappe.set_user("Administrator")

		self.assertEqual(costing["errors"], {})
		self.assertEqual([row.name for row in costing["drivers"]["employees"]], [self.priced_employee])
		self.assertEqual(sum(row.hours for row in costing["drivers"]["activities"]), 2)
		self.assertEqual(costing["summary"]["hours"], 8)

	def test_reports_come_from_the_dashboard_and_keep_to_those_that_open(self) -> None:
		"""The Reports menu lists the Project dashboard's reports, including those another app adds,
		filtered to the project; a disabled report, or one the user's roles may not open, is left out."""
		project = self.project_with_documents()
		with patch_hooks({"override_doctype_dashboards": {"Project": [ADD_GENERAL_LEDGER]}}):
			reports = get_project_costing(project.name)["reports"]

		self.assertEqual(
			reports,
			[
				{"name": "Timesheet Billing Summary", "filters": {"project": project.name}},
				{"name": "General Ledger", "filters": {"project_name": project.name}},
			],
		)

		names = ("General Ledger", "Timesheet Billing Summary", "_Test Missing Report")
		frappe.set_user(make_viewer())
		try:
			self.assertEqual(permitted_reports(names), ["Timesheet Billing Summary"])
		finally:
			frappe.set_user("Administrator")
		frappe.db.set_value("Report", "Timesheet Billing Summary", "disabled", 1)
		self.assertEqual(permitted_reports(names), ["General Ledger"])

	def test_monthly_amounts_add_up_to_the_stored_totals(self) -> None:
		"""Every source, split by month, sums to the total the Project stores for it, and each
		amount lands in the month of the document that booked it."""
		project = make_project({"project_name": f"_Test Cost By Month {frappe.generate_hash(length=6)}"})
		first_month, second_month = month_days(-2), month_days(-1)

		with freeze_time(first_month):
			self.book_first_month(project.name)
		with freeze_time(second_month):
			self.book_second_month(project.name)
		update_costing_and_billing(project.name)
		project.reload()

		queries = ProjectCostQueries(project.name)
		for method, field in (
			(queries.labour_cost, "total_costing_amount"),
			(queries.purchase_cost, "total_purchase_cost"),
			(queries.material_cost, "total_consumed_material_cost"),
			(queries.billed_amount, "total_billed_amount"),
		):
			self.assertAlmostEqual(sum(method(by_month=True).values()), project.get(field), places=2)
			self.assertAlmostEqual(method(), project.get(field), places=2)

		billed = queries.billed_amount(by_month=True)
		self.assertGreater(billed[month_key(first_month)], 0)
		self.assertLess(billed[month_key(second_month)], 0)
		self.assertEqual(
			set(queries.labour_cost(by_month=True)), {month_key(first_month), month_key(second_month)}
		)
		self.assertEqual(set(queries.material_cost(by_month=True)), {month_key(second_month)})

	def test_project_without_documents_has_nothing_to_split(self) -> None:
		project = make_project({"project_name": f"_Test Empty Cost {frappe.generate_hash(length=6)}"})
		queries = ProjectCostQueries(project.name)

		self.assertEqual(queries.labour_cost(by_month=True), {})
		self.assertEqual(queries.purchase_cost(by_month=True), {})
		self.assertEqual(queries.billed_amount(), 0)
		self.assertEqual(queries.sales_order_amount(), 0)

	def book_first_month(self, project: str) -> None:
		"""Time, a non-stock purchase and an invoice, all booked in the first month.

		Stock is received here, not beside the issue: under a frozen clock both would share one
		posting time, and the ledger could then order the issue first."""
		make_timesheet(self.monthly_employee(), simulate=True, project=project)
		service = make_item(properties={"is_stock_item": 0}).name
		make_purchase_invoice(item_code=service, qty=1, rate=500, project=project)
		invoice_for_project(project, qty=2)
		self.stock_item = make_item(properties={"is_stock_item": 1}).name
		make_stock_entry(item_code=self.stock_item, qty=5, to_warehouse="_Test Warehouse - _TC", rate=100)

	def book_second_month(self, project: str) -> None:
		"""More time, stock issued to the project, and a credit note against it."""
		make_timesheet(self.monthly_employee(), simulate=True, project=project)
		issue_to_project(self.stock_item, 3, project)
		invoice_for_project(project, qty=-1, is_return=1)

	def monthly_employee(self) -> str:
		return make_employee("cost-queries@example.com", company="_Test Company")

	def project_with_documents(self) -> frappe._dict:
		"""A customer project with a sales order, priced and unpriced time, and an invoice."""
		project = make_project({"project_name": f"_Test Costing {frappe.generate_hash(length=6)}"})
		project.db_set("customer", "_Test Customer")
		order = make_sales_order(qty=10, rate=1000, do_not_submit=True)
		order.project = project.name
		order.submit()
		self.priced_employee = make_employee("costing-priced@example.com", company="_Test Company")
		make_timesheet(self.priced_employee, project=project.name)
		log_unpriced_time(
			make_employee("costing-unpriced@example.com", company="_Test Company"), project.name
		)
		invoice_for_project(project.name, qty=4)
		return project


def summary(
	status: str = "Open",
	percent_complete: float = 0,
	customer: str | None = None,
	estimate: float = 0,
	cost: float = 0,
	billed: float = 0,
	contract: float = 0,
) -> dict:
	project = frappe._dict(
		status=status, percent_complete=percent_complete, customer=customer, estimated_costing=estimate
	)
	return CostingSummary(project, {"labour": cost, "billed": billed}, contract).build()


def log_unpriced_time(employee: str, project: str) -> None:
	"""Six hours on an activity without a costing rate."""
	if not frappe.db.exists("Activity Type", UNPRICED_ACTIVITY):
		frappe.get_doc({"doctype": "Activity Type", "activity_type": UNPRICED_ACTIVITY}).insert()
	start = add_to_date(now_datetime(), days=-3)
	timesheet = frappe.get_doc(
		{
			"doctype": "Timesheet",
			"employee": employee,
			"company": "_Test Company",
			"time_logs": [
				{
					"activity_type": UNPRICED_ACTIVITY,
					"from_time": start,
					"to_time": add_to_date(start, hours=6),
					"hours": 6,
					"project": project,
				}
			],
		}
	)
	timesheet.insert()
	timesheet.submit()


def add_general_ledger(data: dict) -> dict:
	"""A dashboard override, as another app would add its report, with a filter field of its own."""
	data["reports"].append({"label": "Accounts", "items": ["General Ledger"]})
	data["non_standard_fieldnames"]["General Ledger"] = "project_name"
	return data


def make_viewer() -> str:
	if not frappe.db.exists("User", VIEWER):
		user = frappe.get_doc(
			{"doctype": "User", "email": VIEWER, "first_name": "Costing Viewer", "send_welcome_email": 0}
		).insert()
		user.add_roles("Projects User")
	return VIEWER


def billing_of(project: str) -> dict:
	return get_project_costing(project)["billing"]


def item_invoice_for_project(project: str) -> str:
	"""An invoice that names the project only on its item."""
	invoice = create_sales_invoice(qty=1, rate=1000, do_not_submit=True)
	invoice.items[0].project = project
	invoice.submit()
	return invoice.name


def invoice_for_project(project: str, qty: int, is_return: int = 0) -> None:
	invoice = create_sales_invoice(qty=qty, rate=1000, is_return=is_return, do_not_submit=True)
	invoice.project = project
	invoice.submit()


def month_days(months_back: int) -> str:
	"""The 15th of a month `months_back` from today, so frozen dates never cross a month end."""
	return str(getdate(add_months(get_first_day(nowdate()), months_back)).replace(day=15))


def month_key(date: str) -> str:
	return str(date)[:7]
