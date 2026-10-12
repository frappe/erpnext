# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import json
from itertools import pairwise
from unittest.mock import patch

import frappe
from frappe.utils import add_days, getdate, nowdate

from erpnext.projects.doctype.project import project_overview
from erpnext.projects.doctype.project.test_project import make_project
from erpnext.tests.utils import ERPNextTestSuite


class TestProjectOverview(ERPNextTestSuite):
	def setUp(self):
		self.project = make_project({"project_name": "_Test Overview Project"}).name

	def test_has_tasks_follows_the_project_tasks(self):
		data = project_overview.get_project_overview(self.project)
		self.assertFalse(data["summary"]["has_tasks"])
		self.assertFalse(data["errors"])

		self.make_task("Scoping")
		data = project_overview.get_project_overview(self.project)
		self.assertTrue(data["summary"]["has_tasks"])

	def test_stat_cards(self):
		self.make_task("Five days late", due=-5, expected_time=4)
		self.make_task("Due in three days", due=3, expected_time=6)
		self.make_task("Due in a month", due=30)
		self.make_task("Undated", expected_time=2)
		self.make_task("Done", due=-10, status="Completed", expected_time=8)
		self.make_task("Dropped", due=-10, status="Cancelled", expected_time=50)
		self.make_task("Phase", is_group=1, expected_time=100)
		frappe.db.set_value("Project", self.project, "actual_time", 12.5)

		stats = project_overview.get_project_overview(self.project)["stats"]

		self.assertEqual(stats["open_tasks"], {"count": 5, "due_soon": 1, "due_soon_days": 7})
		# cancelled, completed and undated tasks are never overdue
		self.assertEqual(stats["overdue"], {"count": 1, "oldest_days_late": 5})
		# cancelled and group tasks are left out of the expected hours
		self.assertEqual(stats["hours"], {"logged": 12.5, "expected": 20})

	def test_next_milestone_is_the_open_one_due_first(self):
		data = project_overview.get_project_overview(self.project)
		self.assertEqual(data["milestone"], {"next": None, "all_met": False})

		self.make_task("Kick-off", due=-3, status="Completed", is_milestone=1)
		self.make_task("Undated sign-off", is_milestone=1)
		go_live = self.make_task("Go-live", due=18, is_milestone=1)
		self.make_task("UAT", due=4)

		milestone = project_overview.get_project_overview(self.project)["milestone"]
		self.assertEqual(milestone["next"]["task"], go_live.name)
		self.assertEqual(milestone["next"]["days_left"], 18)
		self.assertFalse(milestone["all_met"])

	def test_all_milestones_met(self):
		self.make_task("Kick-off", due=-3, status="Completed", is_milestone=1)
		milestone = project_overview.get_project_overview(self.project)["milestone"]
		self.assertEqual(milestone, {"next": None, "all_met": True})

	def test_needs_attention_ranks_each_task_under_its_most_pressing_reason(self):
		dependency = self.make_task("Vendor contract", due=30, assigned=True)
		self.make_task("Waiting on vendor", due=20, assigned=True, depends_on=[{"task": dependency.name}])
		self.make_task("Five days late", due=-5)  # also unassigned, but overdue comes first
		self.make_task("Ten days late", due=-10, assigned=True)
		self.make_task("Nobody on it", due=20)
		self.make_task("Due in three days", due=3, assigned=True)
		self.make_task("Undated", assigned=True)  # no due date alone is not a reason
		self.make_task("Undated, nobody on it")
		self.make_task("On track", due=30, assigned=True)
		self.make_task("Phase", due=30, is_group=1)  # group tasks are never unassigned
		self.make_task("Done", due=-10, status="Completed")

		attention = project_overview.get_project_overview(self.project)["needs_attention"]

		rows = [(row["subject"], row["reason"]) for row in attention["tasks"]]
		self.assertEqual(
			rows,
			[
				("Ten days late", "Overdue"),
				("Five days late", "Overdue"),
				("Waiting on vendor", "Blocked"),
				("Nobody on it", "Unassigned"),
				("Undated, nobody on it", "Unassigned"),
				("Due in three days", "Due Soon"),
			],
		)
		self.assertEqual(attention["total"], 6)
		self.assertEqual(attention["tasks"][0]["days_late"], 10)
		self.assertEqual(attention["tasks"][0]["assigned_to"], ["Administrator"])

	def test_needs_attention_puts_higher_priority_first_within_a_reason(self):
		self.make_task("Ten days late, low", due=-10, assigned=True, priority="Low")
		self.make_task("Two days late, urgent", due=-2, assigned=True, priority="Urgent")
		self.make_task("Five days late, high", due=-5, assigned=True, priority="High")
		self.make_task("Eight days late, no priority", due=-8, assigned=True)
		self.make_task("Three days late, high", due=-3, assigned=True, priority="High")

		attention = project_overview.get_project_overview(self.project)["needs_attention"]

		self.assertEqual(
			[row["subject"] for row in attention["tasks"]],
			[
				"Two days late, urgent",
				"Five days late, high",
				"Three days late, high",
				"Ten days late, low",
				"Eight days late, no priority",
			],
		)

	def test_a_task_is_not_blocked_once_its_dependency_is_done(self):
		dependency = self.make_task("Vendor contract", due=30, assigned=True)
		self.make_task("Waiting on vendor", due=20, assigned=True, depends_on=[{"task": dependency.name}])
		dependency.db_set("status", "Completed")

		attention = project_overview.get_project_overview(self.project)["needs_attention"]
		self.assertEqual(attention["tasks"], [])

	def test_planned_vs_completed_follows_the_percent_complete_method(self):
		self.make_progress_plan()

		chart = self.planned_vs_completed("Task Completion")
		self.assertEqual(len(chart["points"]), 7)
		self.assertEqual(chart["today_index"], 3)
		self.assertEqual([p["planned"] for p in chart["points"]], [0, 25, 50, 50, 75, 100, 100])
		# a task finished late counts from its Completed On; nothing is completed after today
		self.assertEqual([p["completed"] for p in chart["points"]], [0, 25, 25, 50, None, None, None])

		# the open task's 50% progress counts at today's point, so the chart ends at the project's % Complete
		chart = self.planned_vs_completed("Task Progress")
		self.assertEqual(chart["points"][3]["completed"], 62.5)
		self.assertEqual(chart["points"][2]["completed"], 25)

		chart = self.planned_vs_completed("Task Weight")
		self.assertEqual([p["planned"] for p in chart["points"]], [0, 12.5, 25, 25, 50, 100, 100])
		self.assertEqual(chart["points"][3]["completed"], 37.5)

		self.assertEqual(self.planned_vs_completed("Manual")["points"], [])

	def test_completed_line_ends_on_today_and_the_axis_ends_on_whole_weeks(self):
		frappe.db.set_value(
			"Project",
			self.project,
			{"expected_start_date": add_days(nowdate(), -10), "expected_end_date": add_days(nowdate(), 10)},
		)
		self.make_task("Done", due=-5, status="Completed", completed_on=add_days(nowdate(), -5))
		self.make_task("Open", due=5)

		chart = project_overview.get_project_overview(self.project)["planned_vs_completed"]
		dates = [getdate(point["date"]) for point in chart["points"]]

		self.assertEqual(dates[chart["today_index"]], getdate(nowdate()))
		self.assertEqual({(later - earlier).days for earlier, later in pairwise(dates)}, {7})
		completed = [point["completed"] for point in chart["points"]]
		self.assertEqual(completed[chart["today_index"]], 50)
		self.assertTrue(all(value is None for value in completed[chart["today_index"] + 1 :]))

	def test_planned_line_needs_most_tasks_dated(self):
		self.make_task("Dated", due=7)
		self.make_task("Undated one")
		self.make_task("Undated two")

		chart = project_overview.get_project_overview(self.project)["planned_vs_completed"]
		self.assertFalse(chart["has_plan"])
		self.assertEqual(chart["undated"], 2)
		self.assertTrue(all(point["planned"] is None for point in chart["points"]))

	def test_no_chart_when_every_task_is_cancelled(self):
		self.make_task("Dropped", due=-5, status="Cancelled")
		self.make_task("Also dropped", due=5, status="Cancelled")

		chart = project_overview.get_project_overview(self.project)["planned_vs_completed"]
		self.assertEqual(chart["points"], [])

	def make_progress_plan(self):
		"""Four tasks over a project running three weeks either side of today, with weights 1, 1, 2, 4."""
		frappe.db.set_value(
			"Project",
			self.project,
			{
				"expected_start_date": add_days(nowdate(), -21),
				"expected_end_date": add_days(nowdate(), 21),
			},
		)
		on_time = add_days(nowdate(), -14)
		self.make_task("On time", due=-14, status="Completed", completed_on=on_time, task_weight=1)
		late = add_days(nowdate(), -3)
		self.make_task("Finished late", due=-7, status="Completed", completed_on=late, task_weight=1)
		self.make_task("Half done", due=7, progress=50, task_weight=2)
		self.make_task("Not started", due=14, task_weight=4)

	def planned_vs_completed(self, method):
		frappe.db.set_value("Project", self.project, "percent_complete_method", method)
		return project_overview.get_project_overview(self.project)["planned_vs_completed"]

	def test_tasks_by_status_counts_late_open_tasks_as_overdue(self):
		self.make_task("New", due=10)
		self.make_task("In progress", due=5, status="Working")
		self.make_task("Late", due=-3)
		self.make_task("Undated")
		self.make_task("Done", due=-10, status="Completed")
		self.make_task("Dropped", due=-10, status="Cancelled")

		breakdown = project_overview.get_project_overview(self.project)["tasks_by_status"]

		self.assertEqual(
			breakdown["statuses"],
			[
				{"status": "Open", "count": 2},
				{"status": "Working", "count": 1},
				{"status": "Overdue", "count": 1},
				{"status": "Completed", "count": 1},
				{"status": "Cancelled", "count": 1},
			],
		)
		self.assertEqual(breakdown["total"], 6)

	def test_workload_counts_open_and_overdue_per_person(self):
		other = "test1@example.com"
		self.make_task("Late", due=-2, assigned=True)
		self.make_task("Soon", due=5, assigned=True)
		self.make_task("Later", due=30, assigned=True)
		self.make_task("Shared", assigned=["Administrator", other])
		self.make_task("Nobody on it", due=3)
		self.make_task("Also late", due=-1, assigned=[other])
		self.make_task("Phase", due=30, is_group=1, assigned=True)
		self.make_task("Done", due=-5, status="Completed", assigned=True)

		workload = project_overview.get_project_overview(self.project)["workload"]

		# group and closed tasks are left out; a shared task counts for each person
		self.assertEqual(
			workload["rows"],
			[
				{"user": "Administrator", "open": 4, "overdue": 1},
				{"user": other, "open": 2, "overdue": 1},
				{"user": None, "open": 1, "overdue": 0},
			],
		)

	def test_unbilled_counts_billable_time_not_yet_invoiced(self):
		from erpnext.projects.doctype.timesheet.test_timesheet import make_timesheet
		from erpnext.setup.doctype.employee.test_employee import make_employee

		employee = make_employee("overview@example.com", company="_Test Company")
		billable = make_timesheet(employee, simulate=True, is_billable=1, project=self.project)
		make_timesheet(employee, simulate=True, is_billable=0, project=self.project)
		invoiced = make_timesheet(employee, simulate=True, is_billable=1, project=self.project)
		invoiced.time_logs[0].db_set("sales_invoice", "_Test Invoice")

		unbilled = project_overview.get_project_overview(self.project)["unbilled"]
		log = billable.time_logs[0]
		self.assertGreater(log.base_billing_amount, 0)
		self.assertEqual(
			unbilled,
			{
				"currency": frappe.get_cached_value("Company", "_Test Company", "default_currency"),
				"amount": log.base_billing_amount,
				"hours": log.billing_hours,
			},
		)

	def test_unbilled_is_left_out_without_timesheet_access(self):
		has_permission = frappe.has_permission

		def no_timesheets(doctype, *args, **kwargs):
			return doctype != "Timesheet" and has_permission(doctype, *args, **kwargs)

		with patch.object(frappe, "has_permission", side_effect=no_timesheets):
			data = project_overview.get_project_overview(self.project)
		self.assertIsNone(data["unbilled"])
		self.assertFalse(data["errors"])

	def test_only_this_projects_real_tasks_count(self):
		self.make_task("Ours", due=-1)
		other = make_project({"project_name": "_Test Overview Other Project"}).name
		frappe.get_doc(
			doctype="Task", subject="Theirs", project=other, exp_end_date=add_days(nowdate(), -1)
		).insert()
		frappe.get_doc(doctype="Task", subject="Template", project=self.project, is_template=1).insert()

		data = project_overview.get_project_overview(self.project)

		self.assertEqual(data["stats"]["open_tasks"]["count"], 1)
		self.assertEqual(data["stats"]["overdue"]["count"], 1)
		self.assertEqual(data["tasks_by_status"]["total"], 1)
		self.assertEqual([row["subject"] for row in data["needs_attention"]["tasks"]], ["Ours"])

	def test_needs_attention_sends_at_most_the_limit_but_counts_all(self):
		for day in range(1, 26):
			self.make_task(f"Late by {day}", due=-day, assigned=True)

		attention = project_overview.get_project_overview(self.project)["needs_attention"]

		self.assertEqual(attention["total"], 25)
		self.assertEqual(len(attention["tasks"]), project_overview.ATTENTION_LIMIT)
		self.assertEqual(attention["tasks"][0]["subject"], "Late by 25")

	def test_a_group_task_is_not_blocked_by_its_own_subtasks(self):
		phase = self.make_task("Phase", due=30, is_group=1, assigned=True)
		self.make_task("Subtask", due=20, assigned=True, parent_task=phase.name)
		phase.reload()
		# ERPNext lists a group task's subtasks under its Depends On by itself
		self.assertIn("Subtask", [row.subject for row in phase.depends_on])

		attention = project_overview.get_project_overview(self.project)["needs_attention"]
		self.assertNotIn("Phase", [row["subject"] for row in attention["tasks"]])

	def test_failing_section_is_flagged_without_failing_the_tab(self):
		with (
			patch.object(project_overview.ProjectOverview, "stats", side_effect=ValueError),
			patch.object(frappe, "log_error"),
		):
			data = project_overview.get_project_overview(self.project)

		self.assertIsNone(data["stats"])
		self.assertEqual(data["errors"], {"stats": 1})
		self.assertIsNotNone(data["summary"])

	def test_project_without_read_access_is_refused(self):
		with patch.object(frappe, "has_permission", return_value=False):
			self.assertRaises(frappe.PermissionError, project_overview.get_project_overview, self.project)

	def make_task(self, subject, due=None, assigned=False, **values):
		"""A task of the test project, due `due` days from today (undated when None)."""
		due_date = getdate(add_days(nowdate(), due)) if due is not None else None
		task = frappe.get_doc(
			doctype="Task",
			subject=subject,
			project=self.project,
			exp_start_date=due_date,
			exp_end_date=due_date,
			**values,
		).insert()
		if assigned:
			users = ["Administrator"] if assigned is True else assigned
			task.db_set("_assign", json.dumps(users))
		return task
