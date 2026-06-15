# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import add_days, flt, getdate, nowdate

from erpnext.projects.doctype.project.project import get_holiday_list
from erpnext.projects.doctype.project_template.test_project_template import make_project_template
from erpnext.projects.doctype.task.test_task import create_task
from erpnext.selling.doctype.sales_order.mapper import make_project as make_project_from_so
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.tests.utils import ERPNextTestSuite


class TestProject(ERPNextTestSuite):
	def test_project_total_costing_and_billing_amount(self):
		from erpnext.projects.doctype.timesheet.test_timesheet import make_timesheet
		from erpnext.setup.doctype.employee.test_employee import make_employee

		project_name = "Test Project Costing"
		employee = make_employee("employee@frappe.io", company="_Test Company")
		project = make_project({"project_name": project_name})
		timesheet = make_timesheet(
			employee=employee,
			is_billable=1,
			currency="USD",
			project=project.name,
			simulate=True,
			exchange_rate=80,
		)
		timesheet.reload()
		project.reload()
		self.assertEqual(project.total_costing_amount, 3200)
		self.assertEqual(project.total_billable_amount, 8000)

	def test_project_with_template_having_no_parent_and_depend_tasks(self):
		project_name = "Test Project with Template - No Parent and Dependend Tasks"
		frappe.db.sql(""" delete from tabTask where project = %s """, project_name)
		frappe.delete_doc("Project", project_name)

		task1 = task_exists("Test Template Task with No Parent and Dependency")
		if not task1:
			task1 = create_task(
				subject="Test Template Task with No Parent and Dependency",
				is_template=1,
				begin=5,
				duration=3,
				priority="High",
			)

		template = make_project_template("Test Project Template - No Parent and Dependend Tasks", [task1])
		project = get_project(project_name, template)
		tasks = frappe.get_all(
			"Task",
			["subject", "exp_end_date", "depends_on_tasks", "priority"],
			dict(project=project.name),
			order_by="creation asc",
		)

		self.assertEqual(tasks[0].priority, "High")
		self.assertEqual(tasks[0].subject, "Test Template Task with No Parent and Dependency")
		self.assertEqual(getdate(tasks[0].exp_end_date), calculate_end_date(project, 5, 3))
		self.assertEqual(len(tasks), 1)

	def test_project_template_having_parent_child_tasks(self):
		project_name = "Test Project with Template - Tasks with Parent-Child Relation"

		if frappe.db.get_value("Project", {"project_name": project_name}, "name"):
			project_name = frappe.db.get_value("Project", {"project_name": project_name}, "name")

		frappe.db.sql(""" delete from tabTask where project = %s """, project_name)
		frappe.delete_doc("Project", project_name)

		task1 = task_exists("Test Template Task Parent")
		if not task1:
			task1 = create_task(
				subject="Test Template Task Parent", is_group=1, is_template=1, begin=1, duration=10
			)

		task2 = task_exists("Test Template Task Child 1")
		if not task2:
			task2 = create_task(
				subject="Test Template Task Child 1",
				parent_task=task1.name,
				is_template=1,
				begin=1,
				duration=3,
			)

		task3 = task_exists("Test Template Task Child 2")
		if not task3:
			task3 = create_task(
				subject="Test Template Task Child 2",
				parent_task=task1.name,
				is_template=1,
				begin=2,
				duration=3,
			)

		template = make_project_template(
			"Test Project Template  - Tasks with Parent-Child Relation", [task1, task2, task3]
		)
		project = get_project(project_name, template)
		tasks = frappe.get_all(
			"Task",
			["subject", "exp_end_date", "depends_on_tasks", "name", "parent_task"],
			dict(project=project.name),
			order_by="creation asc",
		)

		self.assertEqual(tasks[0].subject, "Test Template Task Parent")
		self.assertEqual(getdate(tasks[0].exp_end_date), calculate_end_date(project, 1, 10))

		self.assertEqual(tasks[1].subject, "Test Template Task Child 1")
		self.assertEqual(getdate(tasks[1].exp_end_date), calculate_end_date(project, 1, 3))
		self.assertEqual(tasks[1].parent_task, tasks[0].name)

		self.assertEqual(tasks[2].subject, "Test Template Task Child 2")
		self.assertEqual(getdate(tasks[2].exp_end_date), calculate_end_date(project, 2, 3))
		self.assertEqual(tasks[2].parent_task, tasks[0].name)

		self.assertEqual(len(tasks), 3)

	def test_project_template_having_dependent_tasks(self):
		project_name = "Test Project with Template - Dependent Tasks"
		frappe.db.sql(""" delete from tabTask where project = %s  """, project_name)
		frappe.delete_doc("Project", project_name)

		task1 = task_exists("Test Template Task for Dependency")
		if not task1:
			task1 = create_task(
				subject="Test Template Task for Dependency", is_template=1, begin=3, duration=1
			)

		task2 = task_exists("Test Template Task with Dependency")
		if not task2:
			task2 = create_task(
				subject="Test Template Task with Dependency",
				depends_on=task1.name,
				is_template=1,
				begin=2,
				duration=2,
			)

		template = make_project_template("Test Project with Template - Dependent Tasks", [task1, task2])
		project = get_project(project_name, template)
		tasks = frappe.get_all(
			"Task",
			["subject", "exp_end_date", "depends_on_tasks", "name"],
			dict(project=project.name),
			order_by="creation asc",
		)

		self.assertEqual(tasks[1].subject, "Test Template Task with Dependency")
		self.assertEqual(getdate(tasks[1].exp_end_date), calculate_end_date(project, 2, 2))
		self.assertGreaterEqual(tasks[1].depends_on_tasks.find(tasks[0].name), 0)

		self.assertEqual(tasks[0].subject, "Test Template Task for Dependency")
		self.assertEqual(getdate(tasks[0].exp_end_date), calculate_end_date(project, 3, 1))

		self.assertEqual(len(tasks), 2)

	def test_project_linking_with_sales_order(self):
		so = make_sales_order()
		project = make_project_from_so(so.name)

		project.save()
		self.assertEqual(project.sales_order, so.name)

		so.reload()
		self.assertEqual(so.project, project.name)

		project.delete()

		so.reload()
		self.assertFalse(so.project)

	def test_project_with_template_tasks_having_common_name(self):
		# Step - 1: Create Template Parent Tasks
		template_parent_task1 = create_task(subject="Parent Task - 1", is_template=1, is_group=1)
		template_parent_task2 = create_task(subject="Parent Task - 2", is_template=1, is_group=1)
		template_parent_task3 = create_task(subject="Parent Task - 1", is_template=1, is_group=1)

		# Step - 2: Create Template Child Tasks
		template_task1 = create_task(
			subject="Task - 1", is_template=1, parent_task=template_parent_task1.name
		)
		template_task2 = create_task(
			subject="Task - 2", is_template=1, parent_task=template_parent_task2.name
		)
		template_task3 = create_task(
			subject="Task - 1", is_template=1, parent_task=template_parent_task3.name
		)

		# Step - 3: Create Project Template
		template_tasks = [
			template_parent_task1,
			template_task1,
			template_parent_task2,
			template_task2,
			template_parent_task3,
			template_task3,
		]
		project_template = make_project_template("Project template with common Task Subject", template_tasks)

		# Step - 4: Create Project against the Project Template
		project = get_project("Project with common Task Subject", project_template)
		project_tasks = frappe.get_all(
			"Task", {"project": project.name}, ["subject", "parent_task", "is_group"]
		)

		# Test - 1: No. of Project Tasks should be equal to No. of Template Tasks
		self.assertEqual(len(project_tasks), len(template_tasks))

		# Test - 2: All child Project Tasks should have Parent Task linked
		for pt in project_tasks:
			if not pt.is_group:
				self.assertIsNotNone(pt.parent_task)

	def test_project_having_no_tasks_complete(self):
		project_name = "Test Project - No Tasks Completion"
		frappe.db.sql(""" delete from tabTask where project = %s """, project_name)
		frappe.delete_doc("Project", project_name)

		project = frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": project_name,
				"status": "Open",
				"expected_start_date": nowdate(),
				"company": "_Test Company",
			}
		).insert()

		tasks = frappe.get_all(
			"Task",
			["subject", "exp_end_date", "depends_on_tasks", "name", "parent_task"],
			dict(project=project.name),
			order_by="creation asc",
		)

		self.assertEqual(project.status, "Open")
		self.assertEqual(len(tasks), 0)
		project.status = "Completed"
		project.save()
		self.assertEqual(project.status, "Completed")


def get_project(name, template):
	project = frappe.get_doc(
		doctype="Project",
		project_name=name,
		status="Open",
		project_template=template.name,
		expected_start_date=nowdate(),
		company="_Test Company",
	).insert()

	return project


def make_project(args):
	args = frappe._dict(args)

	if args.project_name and frappe.db.exists("Project", {"project_name": args.project_name}):
		return frappe.get_doc("Project", {"project_name": args.project_name})

	project = frappe.get_doc(
		doctype="Project",
		project_name=args.project_name,
		status="Open",
		expected_start_date=args.start_date,
		company=args.company or "_Test Company",
	)

	if args.project_template_name:
		template = make_project_template(args.project_template_name)
		project.project_template = template.name

	project.insert()

	return project


def task_exists(subject):
	result = frappe.db.get_list("Task", filters={"subject": subject}, fields=["name"])
	if not len(result):
		return False
	return frappe.get_doc("Task", result[0].name)


def calculate_end_date(project, start, duration):
	start = add_days(project.expected_start_date, start)
	start = project.update_if_holiday(start)
	end = add_days(start, duration)
	end = project.update_if_holiday(end)
	return getdate(end)


class TestProjectCoverage(ERPNextTestSuite):
	"""Coverage for Project rollup / costing maths (project.py)."""

	def _make_bare_project(self, project_name, percent_complete_method=None, status="Open"):
		"""Create a saved Project with no template and no tasks."""
		project = frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": project_name,
				"status": status,
				"expected_start_date": nowdate(),
				"company": "_Test Company",
			}
		)
		if percent_complete_method:
			project.percent_complete_method = percent_complete_method
		return project.insert()

	def _make_task(self, project, subject, status="Open", progress=0, task_weight=0):
		"""Create a saved Task linked to ``project`` with the given rollup inputs."""
		# create_task() ignores its `project` arg for non-template tasks (an
		# operator-precedence quirk in the helper), so set the link explicitly.
		task = create_task(subject=subject, save=False)
		task.project = project.name
		task.status = status
		task.progress = progress
		task.task_weight = task_weight
		task.save()
		return task

	# ------------------------------------------------------------------
	# update_percent_complete
	# ------------------------------------------------------------------

	def test_percent_complete_task_completion(self):
		project = self._make_bare_project(
			"Test Coverage % Task Completion", percent_complete_method="Task Completion"
		)
		# 4 tasks, 1 Completed + 1 Cancelled both count as "done" -> 2/4 = 50%
		self._make_task(project, "Coverage TC Task A", status="Completed")
		self._make_task(project, "Coverage TC Task B", status="Cancelled")
		self._make_task(project, "Coverage TC Task C", status="Open")
		self._make_task(project, "Coverage TC Task D", status="Open")

		project.update_percent_complete()

		self.assertAlmostEqual(project.percent_complete, 50.0, places=2)
		# 50% != 100% -> status stays Open
		self.assertEqual(project.status, "Open")

	def test_percent_complete_task_completion_all_done_sets_status(self):
		project = self._make_bare_project(
			"Test Coverage % Task Completion All Done", percent_complete_method="Task Completion"
		)
		self._make_task(project, "Coverage TC All Task A", status="Completed")
		self._make_task(project, "Coverage TC All Task B", status="Completed")

		project.update_percent_complete()

		self.assertAlmostEqual(project.percent_complete, 100.0, places=2)
		# percent_complete == 100 -> status promoted to Completed
		self.assertEqual(project.status, "Completed")

	def test_percent_complete_empty_method_defaults_to_task_completion(self):
		# An empty percent_complete_method takes the `not self.percent_complete_method`
		# branch, which behaves like Task Completion.
		project = self._make_bare_project("Test Coverage % Empty Method")
		self._make_task(project, "Coverage Empty Method Task A", status="Completed")
		self._make_task(project, "Coverage Empty Method Task B", status="Open")
		self._make_task(project, "Coverage Empty Method Task C", status="Open")
		self._make_task(project, "Coverage Empty Method Task D", status="Open")

		# The doctype defaults the method to "Task Completion"; clear it in-memory
		# to exercise the empty-method branch (update_percent_complete does not save).
		project.percent_complete_method = ""
		project.update_percent_complete()

		self.assertAlmostEqual(project.percent_complete, 25.0, places=2)

	def test_percent_complete_task_progress(self):
		project = self._make_bare_project(
			"Test Coverage % Task Progress", percent_complete_method="Task Progress"
		)
		# Task Progress = sum(progress) / count -> (50 + 100) / 2 = 75
		self._make_task(project, "Coverage TP Task A", progress=50)
		self._make_task(project, "Coverage TP Task B", progress=100)

		project.update_percent_complete()

		self.assertAlmostEqual(project.percent_complete, 75.0, places=2)

	def test_percent_complete_task_weight(self):
		project = self._make_bare_project(
			"Test Coverage % Task Weight", percent_complete_method="Task Weight"
		)
		# weight_sum = 4; share_a = 1/4 = 0.25, share_b = 3/4 = 0.75
		# pct = 40*0.25 + 80*0.75 = 10 + 60 = 70
		self._make_task(project, "Coverage TW Task A", progress=40, task_weight=1)
		self._make_task(project, "Coverage TW Task B", progress=80, task_weight=3)

		project.update_percent_complete()

		self.assertAlmostEqual(project.percent_complete, 70.0, places=2)

	def test_percent_complete_manual_open_is_noop(self):
		# Manual + Open: method returns early, percent_complete untouched.
		project = self._make_bare_project("Test Coverage % Manual Open", percent_complete_method="Manual")
		self._make_task(project, "Coverage Manual Task A", status="Completed")
		self._make_task(project, "Coverage Manual Task B", status="Open")

		# Sentinel proves the Manual+Open path does not derive the value from tasks.
		project.percent_complete = 42.0
		project.update_percent_complete()

		self.assertAlmostEqual(project.percent_complete, 42.0, places=2)

	def test_percent_complete_manual_completed_sets_hundred(self):
		# Manual + Completed: percent forced to 100 without scanning tasks
		project = self._make_bare_project(
			"Test Coverage % Manual Completed", percent_complete_method="Manual", status="Open"
		)
		self._make_task(project, "Coverage Manual Done Task A", status="Open")
		project.status = "Completed"

		project.update_percent_complete()

		self.assertAlmostEqual(project.percent_complete, 100.0, places=2)

	def test_percent_complete_empty_project_no_division_error(self):
		# A project with no tasks must resolve to 0 without dividing by zero.
		project = self._make_bare_project(
			"Test Coverage % Empty Project", percent_complete_method="Task Completion"
		)

		project.update_percent_complete()

		self.assertAlmostEqual(project.percent_complete, 0.0, places=2)
		self.assertEqual(project.status, "Open")

	def test_percent_complete_empty_completed_project_becomes_manual(self):
		# Completing a task-less project flips method to Manual and percent to 100.
		project = self._make_bare_project(
			"Test Coverage % Empty Completed", percent_complete_method="Task Completion", status="Open"
		)
		project.status = "Completed"

		project.update_percent_complete()

		self.assertEqual(project.percent_complete_method, "Manual")
		self.assertAlmostEqual(project.percent_complete, 100.0, places=2)

	def test_percent_complete_cancelled_status_preserved(self):
		# Cancelled projects must not be flipped back to Open/Completed.
		project = self._make_bare_project(
			"Test Coverage % Cancelled", percent_complete_method="Task Completion"
		)
		self._make_task(project, "Coverage Cancelled Task A", status="Open")
		project.status = "Cancelled"

		project.update_percent_complete()

		self.assertEqual(project.status, "Cancelled")

	# ------------------------------------------------------------------
	# calculate_gross_margin / per_gross_margin
	# ------------------------------------------------------------------

	def test_calculate_gross_margin(self):
		# gross_margin = billed - (costing + purchase + consumed material)
		# Build an unsaved doc so update_costing() does not overwrite the inputs.
		project = frappe.new_doc("Project")
		project.project_name = "Test Coverage Gross Margin"
		project.company = "_Test Company"
		project.total_billed_amount = 1000
		project.total_costing_amount = 300
		project.total_purchase_cost = 100
		project.total_consumed_material_cost = 100

		project.calculate_gross_margin()

		# 1000 - (300 + 100 + 100) = 500
		self.assertAlmostEqual(flt(project.gross_margin), 500.0, places=2)
		# 500 / 1000 * 100 = 50%
		self.assertAlmostEqual(flt(project.per_gross_margin), 50.0, places=2)

	def test_calculate_gross_margin_negative(self):
		# Expenses exceeding billing produce a negative margin.
		project = frappe.new_doc("Project")
		project.project_name = "Test Coverage Gross Margin Negative"
		project.company = "_Test Company"
		project.total_billed_amount = 200
		project.total_costing_amount = 500
		project.total_purchase_cost = 0
		project.total_consumed_material_cost = 0

		project.calculate_gross_margin()

		self.assertAlmostEqual(flt(project.gross_margin), -300.0, places=2)
		self.assertAlmostEqual(flt(project.per_gross_margin), -150.0, places=2)

	def test_calculate_gross_margin_zero_billed_guard(self):
		# No billing -> per_gross_margin must be 0 (no division by zero).
		project = frappe.new_doc("Project")
		project.project_name = "Test Coverage Gross Margin Zero Billed"
		project.company = "_Test Company"
		project.total_billed_amount = 0
		project.total_costing_amount = 250
		project.total_purchase_cost = 50
		project.total_consumed_material_cost = 0

		project.calculate_gross_margin()

		# gross_margin = 0 - 300 = -300 ; per_gross_margin guarded to 0
		self.assertAlmostEqual(flt(project.gross_margin), -300.0, places=2)
		self.assertAlmostEqual(flt(project.per_gross_margin), 0.0, places=2)

	# ------------------------------------------------------------------
	# update_sales_amount / update_billed_amount (no transactions)
	# ------------------------------------------------------------------

	def test_update_sales_amount_without_sales_orders(self):
		# With no submitted Sales Orders the rollup must resolve to 0.
		project = self._make_bare_project("Test Coverage Sales Amount Empty")

		project.update_sales_amount()

		self.assertAlmostEqual(flt(project.total_sales_amount), 0.0, places=2)

	def test_update_billed_amount_without_invoices(self):
		# With no Sales Invoices both parent and child billed amounts are 0.
		project = self._make_bare_project("Test Coverage Billed Amount Empty")

		self.assertAlmostEqual(flt(project.get_billed_amount_from_parent()), 0.0, places=2)
		self.assertAlmostEqual(flt(project.get_billed_amount_from_child()), 0.0, places=2)

		project.update_billed_amount()
		self.assertAlmostEqual(flt(project.total_billed_amount), 0.0, places=2)

	# ------------------------------------------------------------------
	# set_consumed_material_cost (no stock entries)
	# ------------------------------------------------------------------

	def test_set_consumed_material_cost_without_stock_entries(self):
		# No manufacturing stock entries -> consumed material cost is 0.
		project = self._make_bare_project("Test Coverage Consumed Material Empty")

		project.set_consumed_material_cost()

		self.assertAlmostEqual(flt(project.total_consumed_material_cost), 0.0, places=2)

	# ------------------------------------------------------------------
	# copy_from_template + calculate_start_date / calculate_end_date
	# ------------------------------------------------------------------

	def test_copy_from_template_creates_tasks(self):
		template_task = create_task(
			subject="Coverage Template Task Solo",
			is_template=1,
			begin=2,
			duration=4,
			priority="Medium",
		)
		template = make_project_template("Test Coverage Project Template Solo", [template_task])

		project = get_project("Test Coverage Project From Template", template)

		tasks = frappe.get_all(
			"Task",
			["subject", "exp_start_date", "exp_end_date"],
			{"project": project.name},
			order_by="creation asc",
		)
		self.assertEqual(len(tasks), 1)
		self.assertEqual(tasks[0].subject, "Coverage Template Task Solo")
		# Dates honour begin/duration offsets plus holiday-skipping.
		self.assertEqual(getdate(tasks[0].exp_start_date), calculate_start_date(project, 2))
		self.assertEqual(getdate(tasks[0].exp_end_date), calculate_end_date(project, 2, 4))

	def test_calculate_start_and_end_date_skip_holidays(self):
		# Exercise calculate_start_date / calculate_end_date / update_if_holiday
		# directly against the company holiday list.
		project = self._make_bare_project("Test Coverage Date Helpers")

		task_details = frappe._dict({"start": 1, "duration": 3})
		start = project.calculate_start_date(task_details)
		end = project.calculate_end_date(task_details)

		holiday_list = project.holiday_list or get_holiday_list(project.company)
		# Computed dates land on working days only.
		self.assertFalse(is_company_holiday(holiday_list, start))
		self.assertFalse(is_company_holiday(holiday_list, end))
		# End date is never before the start date.
		self.assertGreaterEqual(getdate(end), getdate(start))


def calculate_start_date(project, start):
	start = add_days(project.expected_start_date, start)
	return getdate(project.update_if_holiday(start))


def is_company_holiday(holiday_list, date):
	from erpnext.setup.doctype.holiday_list.holiday_list import is_holiday

	return is_holiday(holiday_list, date)
