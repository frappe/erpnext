# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from unittest.mock import patch

import frappe
from frappe.core.doctype.user_permission.test_user_permission import create_user
from frappe.tests.classes.context_managers import freeze_time, patch_hooks
from frappe.utils import add_months, add_to_date, get_first_day, getdate, now_datetime, nowdate

from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.projects.doctype.project.costing.drivers import summarise_rate_gaps
from erpnext.projects.doctype.project.costing.project_costing import (
	CostingSummary,
	get_project_costing,
	get_project_invoices,
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
EMPLOYEE_USER = "costing-employee@example.com"
HR_MANAGER = "costing-hr-manager@example.com"
SALES_VIEWER = "costing-sales-viewer@example.com"
ADD_GENERAL_LEDGER = "erpnext.projects.doctype.project.costing.test_project_costing.add_general_ledger"


class TestProjectCosting(ERPNextTestSuite):
	def test_summary_health_forecast_and_margins(self) -> None:
		"""Forecast scales cost by progress only while the project runs; health compares cost and
		forecast with the estimate; margins follow billing, contract and estimate, when there are."""
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

		# without an estimate, a contract or billing
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
		"""The Billing card's link to the invoice list filters by the invoice's project or by the
		items' project. A mix of the two has no filter, so the card pages through the invoices."""
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
		self.assertIsNone(billing["invoice_filter"])

		# a mix pages through every invoice instead, newest first, a page at a time
		with patch("erpnext.projects.doctype.project.costing.project_costing.INVOICE_PAGE", 1):
			pages = [get_project_invoices(project, start=start) for start in range(3)]
		self.assertEqual([len(page) for page in pages], [1, 1, 0])
		self.assertEqual(
			[page[0]["name"] for page in pages[:2]], [row["name"] for row in billing["invoices"]]
		)
		self.assertIn(item_invoice, {page[0]["name"] for page in pages[:2]})

	def test_viewers_see_the_totals_and_only_what_they_may_read(self) -> None:
		"""A Projects User sees the same totals, without costing rates or the invoices behind them. A
		Sales User the project is shared with cannot read timesheets: the labour lists are left out,
		and every section still builds."""
		project = self.project_with_documents()
		cost = get_project_costing(project.name)["summary"]["cost"]
		sales_viewer = create_user(SALES_VIEWER, "Sales User").name
		frappe.share.add("Project", project.name, sales_viewer, read=1)

		try:
			frappe.set_user(make_viewer())
			projects_view = get_project_costing(project.name)
			frappe.set_user(sales_viewer)
			sales_view = get_project_costing(project.name)
		finally:
			frappe.set_user("Administrator")

		self.assertEqual((projects_view["errors"], sales_view["errors"]), ({}, {}))
		self.assertEqual((projects_view["summary"]["cost"], sales_view["summary"]["cost"]), (cost, cost))
		self.assertFalse(projects_view["access"]["labour"])
		self.assertFalse(projects_view["access"]["create"]["Sales Invoice"])
		self.assertIsNone(projects_view["billing"]["invoices"])
		self.assertIsNone(projects_view["rate_gaps"])
		self.assertNotIn("amount", projects_view["drivers"]["activities"][0])
		self.assertFalse(sales_view["access"]["timesheets"])
		self.assertIsNone(sales_view["drivers"]["activities"])
		self.assertIsNone(sales_view["drivers"]["employees"])

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
		project = make_project({"project_name": f"_Test Costing Reports {frappe.generate_hash(length=6)}"})
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
		# an Employee is on the report's roles, but may not run reports on Timesheet
		employee = create_user(EMPLOYEE_USER, "Employee").name
		frappe.set_user(make_viewer())
		try:
			self.assertEqual(permitted_reports(names), ["Timesheet Billing Summary"])
			frappe.set_user(employee)
			self.assertEqual(permitted_reports(names), [])
		finally:
			frappe.set_user("Administrator")
		# a Custom Report opens as the report it is saved from, so it follows that report's roles
		custom = timesheet_custom_report()
		frappe.set_user(create_user(HR_MANAGER, "HR Manager").name)
		try:
			# both checks pass on the Custom Report itself
			self.assertTrue(frappe.get_doc("Report", custom).is_permitted())
			self.assertTrue(frappe.has_permission("Timesheet", "report"))
			self.assertEqual(permitted_reports((custom,)), [])
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(permitted_reports((custom,)), [custom])

		frappe.db.set_value("Report", "Timesheet Billing Summary", "disabled", 1)
		self.assertEqual(permitted_reports(names), ["General Ledger"])
		self.assertEqual(permitted_reports((custom,)), [])

	def test_monthly_amounts_land_in_their_month(self) -> None:
		"""Every source, split by month, adds up to its total, and each amount lands in the month of
		the document that booked it."""
		project = make_project({"project_name": f"_Test Cost By Month {frappe.generate_hash(length=6)}"})
		first_month, second_month = month_days(-2), month_days(-1)

		with freeze_time(first_month):
			self.book_first_month(project.name)
		with freeze_time(second_month):
			self.book_second_month(project.name)

		queries = ProjectCostQueries(project.name)
		for method in (
			queries.labour_cost,
			queries.labour_hours,
			queries.purchase_cost,
			queries.material_cost,
			queries.billed_amount,
		):
			self.assertAlmostEqual(sum(method(by_month=True).values()), method(), places=2)

		billed = queries.billed_amount(by_month=True)
		self.assertGreater(billed[month_key(first_month)], 0)
		self.assertLess(billed[month_key(second_month)], 0)
		self.assertEqual(
			set(queries.labour_cost(by_month=True)), {month_key(first_month), month_key(second_month)}
		)
		self.assertEqual(
			set(queries.labour_hours(by_month=True)), {month_key(first_month), month_key(second_month)}
		)
		self.assertEqual(set(queries.material_cost(by_month=True)), {month_key(second_month)})

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
		"""More time, one log of it with only an end time, as the API and Data Import can add, stock
		issued to the project, and a credit note against it."""
		make_timesheet(self.monthly_employee(), simulate=True, project=project)
		employee = make_employee("cost-queries-ended@example.com", company="_Test Company")
		ended_only = make_timesheet(employee, project=project, do_not_submit=True)
		ended_only.time_logs[0].from_time = None
		ended_only.save()
		ended_only.submit()
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


def timesheet_custom_report() -> str:
	"""A Custom Report saved from Timesheet Billing Summary. It takes its roles from Timesheet, which
	lets an HR Manager in, while the report it is saved from does not."""
	name = "_Test Costing Timesheet Custom"
	if not frappe.db.exists("Report", name):
		frappe.get_doc(
			{
				"doctype": "Report",
				"report_name": name,
				"report_type": "Custom Report",
				"reference_report": "Timesheet Billing Summary",
				"ref_doctype": "Timesheet",
				"is_standard": "No",
				"module": "Projects",
			}
		).insert()
	return name


def make_viewer() -> str:
	return create_user(VIEWER, "Projects User").name


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
