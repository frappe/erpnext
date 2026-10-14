import frappe
from frappe.core.doctype.user_permission.test_user_permission import create_user
from frappe.permissions import add_user_permission
from frappe.utils import add_days, add_months, nowdate

from erpnext.projects.doctype.project.test_project import make_project
from erpnext.projects.doctype.task.test_task import create_task
from erpnext.projects.report.delayed_tasks_summary.delayed_tasks_summary import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestDelayedTasksSummary(ERPNextTestSuite):
	@classmethod
	def setUp(self):
		task1 = create_task("_Test Task 98", add_days(nowdate(), -10), nowdate())
		create_task("_Test Task 99", add_days(nowdate(), -10), add_days(nowdate(), -1))

		task1.status = "Completed"
		task1.completed_on = add_days(nowdate(), -1)
		task1.save()

	def test_delayed_tasks_summary(self):
		filters = frappe._dict(
			{
				"from_date": add_months(nowdate(), -1),
				"to_date": nowdate(),
				"priority": "Low",
				"status": "Open",
			}
		)
		expected_data = [
			{"subject": "_Test Task 99", "status": "Open", "priority": "Low", "delay": 1},
			{"subject": "_Test Task 98", "status": "Completed", "priority": "Low", "delay": -1},
		]
		report = execute(filters)
		data = next(filter(lambda x: x.subject == "_Test Task 99", report[1]))

		for key in ["subject", "status", "priority", "delay"]:
			self.assertEqual(expected_data[0].get(key), data.get(key))

		filters.status = "Completed"
		report = execute(filters)
		data = next(filter(lambda x: x.subject == "_Test Task 98", report[1]))

		for key in ["subject", "status", "priority", "delay"]:
			self.assertEqual(expected_data[1].get(key), data.get(key))

	def test_cancelled_and_template_tasks_are_excluded(self):
		cancelled = create_task("_Test Task Cancelled", add_days(nowdate(), -10), add_days(nowdate(), -5))
		cancelled.status = "Cancelled"
		cancelled.save()
		template = create_task(
			"_Test Task Template", add_days(nowdate(), -10), add_days(nowdate(), -5), is_template=1
		)

		tasks = {row.name for row in execute(frappe._dict())[1]}
		self.assertNotIn(cancelled.name, tasks)
		self.assertNotIn(template.name, tasks)

	def make_delayed_task(self, project):
		return frappe.get_doc(
			doctype="Task",
			subject=f"_Test Delayed {project}",
			project=project,
			exp_start_date=add_days(nowdate(), -10),
			exp_end_date=add_days(nowdate(), -5),
		).insert()

	def test_restricted_user_sees_only_permitted_tasks(self):
		permitted = make_project({"project_name": "_Test Delayed Tasks Permitted"}).name
		other = make_project({"project_name": "_Test Delayed Tasks Other"}).name
		permitted_task = self.make_delayed_task(permitted)
		self.make_delayed_task(other)
		user = create_user("delayed_tasks_restricted@example.com", "Projects User").name
		add_user_permission("Project", permitted, user)

		with self.set_user(user):
			_columns, data, _message, chart = execute(frappe._dict())

		self.assertEqual({row.name for row in data}, {permitted_task.name})
		self.assertEqual(sum(chart["data"]["datasets"][0]["values"]), 1)
