# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import datetime
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase, change_settings
from frappe.utils import add_to_date, now_datetime, nowdate

from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_sales_return
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.projects.doctype.timesheet.timesheet import (
	OverlapError,
	get_activity_cost,
	make_sales_invoice,
)
from erpnext.setup.doctype.employee.test_employee import make_employee
from erpnext.tests.permission_test_utils import (
	OTHER_COMPANY,
	as_user,
	assert_not_found,
	assert_refused,
	assert_refused_for_names,
	assert_refused_without,
	insert_test_record,
	make_company_fenced_user,
	make_fenced_user,
	malformed_names,
)


class TestTimesheet(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("Timesheet")

	def test_timesheet_base_amount(self):
		emp = make_employee("test_employee_6@salary.com")
		timesheet = make_timesheet(emp, simulate=True, is_billable=1)

		self.assertEqual(timesheet.time_logs[0].base_billing_rate, 50)
		self.assertEqual(timesheet.time_logs[0].base_costing_rate, 20)
		self.assertEqual(timesheet.time_logs[0].base_billing_amount, 100)
		self.assertEqual(timesheet.time_logs[0].base_costing_amount, 40)

	def test_timesheet_billing_amount(self):
		emp = make_employee("test_employee_6@salary.com")
		timesheet = make_timesheet(emp, simulate=True, is_billable=1)

		self.assertEqual(timesheet.total_hours, 2)
		self.assertEqual(timesheet.total_billable_hours, 2)
		self.assertEqual(timesheet.time_logs[0].billing_rate, 50)
		self.assertEqual(timesheet.time_logs[0].billing_amount, 100)
		self.assertEqual(timesheet.total_billable_amount, 100)

	def test_timesheet_billing_amount_not_billable(self):
		emp = make_employee("test_employee_6@salary.com")
		timesheet = make_timesheet(emp, simulate=True, is_billable=0)

		self.assertEqual(timesheet.total_hours, 2)
		self.assertEqual(timesheet.total_billable_hours, 0)
		self.assertEqual(timesheet.time_logs[0].billing_rate, 0)
		self.assertEqual(timesheet.time_logs[0].billing_amount, 0)
		self.assertEqual(timesheet.total_billable_amount, 0)

	def test_sales_invoice_from_timesheet(self):
		emp = make_employee("test_employee_6@salary.com")

		timesheet = make_timesheet(emp, simulate=True, is_billable=1)
		sales_invoice = make_sales_invoice(timesheet.name, "_Test Item", "_Test Customer", currency="INR")
		sales_invoice.due_date = nowdate()
		sales_invoice.submit()
		timesheet = frappe.get_doc("Timesheet", timesheet.name)
		self.assertEqual(sales_invoice.total_billing_amount, 100)
		self.assertEqual(timesheet.status, "Billed")
		self.assertEqual(sales_invoice.customer, "_Test Customer")

		item = sales_invoice.items[0]
		self.assertEqual(item.item_code, "_Test Item")
		self.assertEqual(item.qty, 2.00)
		self.assertEqual(item.rate, 50.00)

	@change_settings("Projects Settings", {"fetch_timesheet_in_sales_invoice": 1})
	def test_timesheet_billing_based_on_project(self):
		emp = make_employee("test_employee_6@salary.com")
		project = frappe.get_value("Project", {"project_name": "_Test Project"})

		timesheet = make_timesheet(
			emp, simulate=True, is_billable=1, project=project, company="_Test Company"
		)
		sales_invoice = create_sales_invoice(do_not_save=True)
		sales_invoice.project = project
		sales_invoice.add_timesheet_data()
		sales_invoice.submit()

		ts = frappe.get_doc("Timesheet", timesheet.name)
		self.assertEqual(ts.per_billed, 100)
		self.assertEqual(ts.time_logs[0].sales_invoice, sales_invoice.name)

	def test_invoice_row_without_time_log_bills_the_unbilled_logs(self):
		emp = make_employee("test_employee_6@salary.com", company="_Test Company")
		timesheet = make_timesheet(emp, simulate=True, is_billable=1)

		sales_invoice = self._invoice_with_timesheet_row(timesheet.name, None, with_amounts=False)
		sales_invoice.submit()
		timesheet.reload()
		self.assertEqual(sales_invoice.timesheets[0].timesheet_detail, timesheet.time_logs[0].name)
		self.assertEqual(sales_invoice.total_billing_amount, 100)
		self.assertEqual(timesheet.status, "Billed")

		second_invoice = self._invoice_with_timesheet_row(timesheet.name, None, with_amounts=False)
		self.assertRaises(frappe.ValidationError, second_invoice.save)

	def test_invoice_from_timesheet_carries_the_project_of_its_logs(self):
		emp = make_employee("test_employee_6@salary.com", company="_Test Company")
		project = frappe.get_value("Project", {"project_name": "_Test Project"})
		timesheet = make_timesheet(emp, simulate=True, is_billable=1, project=project)

		sales_invoice = make_sales_invoice(timesheet.name, "_Test Item", "_Test Customer", currency="INR")
		self.assertEqual(sales_invoice.project, project)

	def test_zero_rate_log_can_be_invoiced_after_the_priced_logs(self):
		update_activity_type("_Test Activity Type")
		from_time = now_datetime()
		timesheet = frappe.get_doc(
			{
				"doctype": "Timesheet",
				"company": "_Test Company",
				"time_logs": [
					{
						"activity_type": "_Test Activity Type",
						"is_billable": 1,
						"from_time": from_time,
						"to_time": add_to_date(from_time, hours=2),
					},
					{
						"is_billable": 1,
						"from_time": add_to_date(from_time, hours=2),
						"to_time": add_to_date(from_time, hours=5),
					},
				],
			}
		).insert()
		timesheet.submit()

		sales_invoice = make_sales_invoice(timesheet.name, "_Test Item", "_Test Customer", currency="INR")
		sales_invoice.due_date = nowdate()
		sales_invoice.timesheets.pop()
		sales_invoice.submit()
		self.assertEqual(frappe.db.get_value("Timesheet", timesheet.name, "status"), "Billed")

		sales_invoice = make_sales_invoice(timesheet.name, "_Test Item", "_Test Customer", currency="INR")
		sales_invoice.due_date = nowdate()
		sales_invoice.submit()
		timesheet.reload()
		self.assertEqual(timesheet.time_logs[1].sales_invoice, sales_invoice.name)

	def test_same_time_log_twice_in_an_invoice_is_refused(self):
		emp = make_employee("test_employee_6@salary.com", company="_Test Company")
		timesheet = make_timesheet(emp, simulate=True, is_billable=1)

		sales_invoice = make_sales_invoice(timesheet.name, "_Test Item", "_Test Customer", currency="INR")
		sales_invoice.due_date = nowdate()
		sales_invoice.append("timesheets", sales_invoice.timesheets[0].as_dict(no_default_fields=True))
		self.assertRaises(frappe.ValidationError, sales_invoice.save)

	def _invoice_with_timesheet_row(self, time_sheet, timesheet_detail, with_amounts=True):
		sales_invoice = create_sales_invoice(do_not_save=True)
		row = {"time_sheet": time_sheet, "timesheet_detail": timesheet_detail}
		if with_amounts:
			row.update({"billing_hours": 2, "billing_amount": 100})
		sales_invoice.append("timesheets", row)
		return sales_invoice

	@change_settings("Projects Settings", {"ignore_user_time_overlap": 1})
	def test_timesheet_time_overlap(self):
		emp = make_employee("test_employee_6@salary.com")

		settings = frappe.get_single("Projects Settings")
		initial_setting = settings.ignore_employee_time_overlap
		settings.ignore_employee_time_overlap = 0
		settings.save()

		update_activity_type("_Test Activity Type")
		timesheet = frappe.new_doc("Timesheet")
		timesheet.employee = emp
		timesheet.append(
			"time_logs",
			{
				"billable": 1,
				"activity_type": "_Test Activity Type",
				"from_time": now_datetime(),
				"to_time": now_datetime() + datetime.timedelta(hours=3),
				"company": "_Test Company",
			},
		)
		timesheet.append(
			"time_logs",
			{
				"billable": 1,
				"activity_type": "_Test Activity Type",
				"from_time": now_datetime(),
				"to_time": now_datetime() + datetime.timedelta(hours=3),
				"company": "_Test Company",
			},
		)

		self.assertRaises(frappe.ValidationError, timesheet.save)

		settings.ignore_employee_time_overlap = 1
		settings.save()
		timesheet.save()  # should not throw an error

		settings.ignore_employee_time_overlap = initial_setting
		settings.save()

	def test_timesheet_not_overlapping_with_continuous_timelogs(self):
		emp = make_employee("test_employee_6@salary.com")

		update_activity_type("_Test Activity Type")
		timesheet = frappe.new_doc("Timesheet")
		timesheet.employee = emp
		timesheet.append(
			"time_logs",
			{
				"billable": 1,
				"activity_type": "_Test Activity Type",
				"from_time": now_datetime(),
				"to_time": now_datetime() + datetime.timedelta(hours=3),
				"company": "_Test Company",
			},
		)
		timesheet.append(
			"time_logs",
			{
				"billable": 1,
				"activity_type": "_Test Activity Type",
				"from_time": now_datetime() + datetime.timedelta(hours=3),
				"to_time": now_datetime() + datetime.timedelta(hours=4),
				"company": "_Test Company",
			},
		)

		timesheet.save()  # should not throw an error

	def test_to_time(self):
		emp = make_employee("test_employee_6@salary.com")
		from_time = now_datetime()

		timesheet = frappe.new_doc("Timesheet")
		timesheet.employee = emp
		timesheet.append(
			"time_logs",
			{
				"billable": 1,
				"activity_type": "_Test Activity Type",
				"from_time": from_time,
				"hours": 2,
				"company": "_Test Company",
			},
		)
		timesheet.save()

		to_time = timesheet.time_logs[0].to_time
		self.assertEqual(to_time, add_to_date(from_time, hours=2, as_datetime=True))

	def test_logs_entered_with_hours(self):
		update_activity_type("_Test Activity Type")
		time_log = {
			"activity_type": "_Test Activity Type",
			"is_billable": 1,
			"from_time": now_datetime(),
			"hours": 2,
		}

		timesheet = frappe.get_doc(
			{"doctype": "Timesheet", "company": "_Test Company", "time_logs": [time_log]}
		).insert()
		self.assertEqual(timesheet.total_billable_amount, 100)

		time_log.update({"from_time": add_to_date(now_datetime(), hours=5), "hours": -3})
		timesheet = frappe.get_doc(
			{"doctype": "Timesheet", "company": "_Test Company", "time_logs": [time_log]}
		)
		self.assertRaises(frappe.ValidationError, timesheet.insert)

	def test_per_billed_hours(self):
		"""If amounts are 0, per_billed should be calculated based on hours."""
		ts = frappe.new_doc("Timesheet")
		ts.total_billable_amount = 0
		ts.total_billed_amount = 0
		ts.total_billable_hours = 2

		ts.total_billed_hours = 0.5
		ts.calculate_percentage_billed()
		self.assertEqual(ts.per_billed, 25)

		ts.total_billed_hours = 2
		ts.calculate_percentage_billed()
		self.assertEqual(ts.per_billed, 100)

	def test_per_billed_amount(self):
		"""If amounts are > 0, per_billed should be calculated based on amounts, regardless of hours."""
		ts = frappe.new_doc("Timesheet")
		ts.total_billable_hours = 2
		ts.total_billed_hours = 1
		ts.total_billable_amount = 200
		ts.total_billed_amount = 50
		ts.calculate_percentage_billed()
		self.assertEqual(ts.per_billed, 25)

		ts.total_billed_hours = 3
		ts.total_billable_amount = 200
		ts.total_billed_amount = 200
		ts.calculate_percentage_billed()
		self.assertEqual(ts.per_billed, 100)

	def test_partial_billing_and_return(self):
		"""
		Test Timesheet status transitions during partial billing, full billing,
		sales return, and return cancellation.
		Scenario:
		1. Create a Timesheet with two billable time logs.
		2. Create a Sales Invoice billing only one time log → Timesheet becomes Partially Billed.
		3. Create another Sales Invoice billing the remaining time log → Timesheet becomes Billed.
		4. Create a Sales Return against the second invoice → Timesheet reverts to Partially Billed.
		5. Cancel the Sales Return → Timesheet returns to Billed status.
		This test ensures Timesheet status is recalculated correctly
		across billing and return lifecycle events.
		"""
		emp = make_employee("test_employee_6@salary.com")

		timesheet = make_timesheet(emp, simulate=True, is_billable=1, do_not_submit=True)
		timesheet_detail = timesheet.append("time_logs", {})
		timesheet_detail.is_billable = 1
		timesheet_detail.activity_type = "_Test Activity Type"
		timesheet_detail.from_time = timesheet.time_logs[0].to_time + datetime.timedelta(minutes=1)
		timesheet_detail.hours = 2
		timesheet_detail.to_time = timesheet_detail.from_time + datetime.timedelta(
			hours=timesheet_detail.hours
		)
		timesheet.save().submit()

		sales_invoice = make_sales_invoice(timesheet.name, "_Test Item", "_Test Customer", currency="INR")
		sales_invoice.due_date = nowdate()
		sales_invoice.timesheets.pop()
		sales_invoice.submit()

		timesheet_status = frappe.get_value("Timesheet", timesheet.name, "status")
		self.assertEqual(timesheet_status, "Partially Billed")

		sales_invoice2 = make_sales_invoice(timesheet.name, "_Test Item", "_Test Customer", currency="INR")
		sales_invoice2.due_date = nowdate()
		sales_invoice2.submit()

		timesheet_status = frappe.get_value("Timesheet", timesheet.name, "status")
		self.assertEqual(timesheet_status, "Billed")

		sales_return = make_sales_return(sales_invoice2.name).submit()
		timesheet_status = frappe.get_value("Timesheet", timesheet.name, "status")
		self.assertEqual(timesheet_status, "Partially Billed")

		sales_return.load_from_db()
		sales_return.cancel()

		timesheet.load_from_db()
		self.assertEqual(timesheet.time_logs[1].sales_invoice, sales_invoice2.name)
		self.assertEqual(timesheet.status, "Billed")

	def test_employee_activity_cost_is_converted_to_the_timesheet_currency(self):
		from erpnext.projects.doctype.timesheet.timesheet import get_activity_cost

		emp = make_employee("test_employee_currency@example.com", company="_Test Company")
		frappe.get_doc(
			{
				"doctype": "Activity Cost",
				"employee": emp,
				"activity_type": "_Test Activity Type",
				"billing_rate": 1000,
				"costing_rate": 600,
			}
		).insert()
		timesheet = frappe.get_doc(
			{
				"doctype": "Timesheet",
				"company": "_Test Company",
				"employee": emp,
				"currency": "EUR",
				"exchange_rate": 2,
				"time_logs": [
					{
						"activity_type": "_Test Activity Type",
						"is_billable": 1,
						"from_time": now_datetime(),
						"hours": 2,
					}
				],
			}
		)

		with patch("erpnext.projects.doctype.timesheet.timesheet.get_exchange_rate", return_value=0.5):
			self.assertEqual(get_activity_cost(emp, "_Test Activity Type", "EUR")["billing_rate"], 500)
			timesheet.insert()

		self.assertEqual(timesheet.time_logs[0].billing_rate, 500)
		self.assertEqual(timesheet.time_logs[0].costing_rate, 300)

	def test_amounts_follow_the_rates_without_an_activity_type(self):
		from_time = now_datetime()
		timesheet = frappe.get_doc(
			{
				"doctype": "Timesheet",
				"company": "_Test Company",
				"time_logs": [
					{
						"from_time": from_time,
						"to_time": add_to_date(from_time, hours=2),
						"is_billable": 1,
						"billing_rate": 100,
						"billing_amount": 50000,
						"costing_rate": 10,
						"costing_amount": 1,
					}
				],
			}
		).insert()

		self.assertEqual(timesheet.total_billable_amount, 200)
		self.assertEqual(timesheet.total_costing_amount, 20)

	def test_default_activity_cost_applies_to_employees_without_their_own(self):
		from erpnext.projects.doctype.timesheet.timesheet import get_activity_cost

		activity_type = frappe.get_doc(
			{"doctype": "Activity Type", "activity_type": "_Test Default Cost Activity"}
		).insert()
		emp = make_employee("test_employee_6@salary.com", company="_Test Company")
		frappe.get_doc(
			{
				"doctype": "Activity Cost",
				"activity_type": activity_type.name,
				"billing_rate": 80,
				"costing_rate": 40,
			}
		).insert()

		rate = get_activity_cost(emp, activity_type.name)
		self.assertEqual(rate["billing_rate"], 80)
		self.assertEqual(rate["costing_rate"], 40)

	def test_portal_lists_only_submitted_timesheets(self):
		from erpnext.projects.doctype.timesheet.timesheet import get_timesheets_list

		frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": "_Test Timesheet Portal Contact",
				"user": "Administrator",
				"links": [{"link_doctype": "Customer", "link_name": "_Test Customer"}],
			}
		).insert(ignore_permissions=True)
		project = frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": "_Test Timesheet Portal Project",
				"company": "_Test Company",
				"customer": "_Test Customer",
			}
		).insert()
		emp = make_employee("test_employee_6@salary.com", company="_Test Company")
		draft = make_timesheet(emp, simulate=True, project=project.name, do_not_submit=True)
		submitted = make_timesheet(emp, simulate=True, project=project.name)

		names = [row.name for row in get_timesheets_list("Timesheet", None, {}, 0, 500)]
		self.assertIn(submitted.name, names)
		self.assertNotIn(draft.name, names)

	def test_billing_fields_cannot_change_after_submit(self):
		emp = make_employee("test_employee_6@salary.com", company="_Test Company")
		timesheet = make_timesheet(emp, simulate=True, is_billable=1)

		timesheet.time_logs[0].billing_hours = 10
		self.assertRaises(frappe.UpdateAfterSubmitError, timesheet.save)

	@change_settings("Projects Settings", {"ignore_user_time_overlap": 0})
	def test_user_time_overlap(self):
		from_time = now_datetime()

		timesheet = make_timesheet_without_employee(from_time, 3).insert()
		self.assertEqual(timesheet.user, "Administrator")
		self.assertRaises(
			OverlapError, make_timesheet_without_employee(add_to_date(from_time, hours=1), 1).insert
		)

	def test_patch_sets_the_user_of_older_timesheets(self):
		from erpnext.patches.v16_0.set_user_on_timesheets import execute

		emp = make_employee("test_employee_6@salary.com", company="_Test Company")
		timesheet = make_timesheet(emp, simulate=True)
		timesheet.db_set("user", None)

		without_employee = make_timesheet_without_employee(now_datetime(), 1).insert()
		without_employee.db_set("user", None)

		execute()
		self.assertEqual(
			frappe.db.get_value("Timesheet", timesheet.name, "user"), "test_employee_6@salary.com"
		)
		self.assertEqual(frappe.db.get_value("Timesheet", without_employee.name, "user"), "Administrator")


def make_timesheet_without_employee(start, hours):
	return frappe.get_doc(
		{
			"doctype": "Timesheet",
			"company": "_Test Company",
			"time_logs": [{"from_time": start, "to_time": add_to_date(start, hours=hours)}],
		}
	)


def make_timesheet(
	employee,
	simulate=False,
	is_billable=0,
	activity_type="_Test Activity Type",
	project=None,
	task=None,
	company=None,
	do_not_submit=False,
):
	update_activity_type(activity_type)
	timesheet = frappe.new_doc("Timesheet")
	timesheet.employee = employee
	timesheet.company = company or "_Test Company"
	timesheet_detail = timesheet.append("time_logs", {})
	timesheet_detail.is_billable = is_billable
	timesheet_detail.activity_type = activity_type
	timesheet_detail.from_time = now_datetime()
	timesheet_detail.hours = 2
	timesheet_detail.to_time = timesheet_detail.from_time + datetime.timedelta(hours=timesheet_detail.hours)
	timesheet_detail.project = project
	timesheet_detail.task = task

	for data in timesheet.get("time_logs"):
		if simulate:
			while True:
				try:
					timesheet.save(ignore_permissions=True)
					break
				except OverlapError:
					data.from_time = data.from_time + datetime.timedelta(minutes=10)
					data.to_time = data.from_time + datetime.timedelta(hours=data.hours)
		else:
			timesheet.save(ignore_permissions=True)

	if not do_not_submit:
		timesheet.submit()

	return timesheet


def update_activity_type(activity_type):
	activity_type = frappe.get_doc("Activity Type", activity_type)
	activity_type.billing_rate = 50.0
	activity_type.costing_rate = 20.0
	activity_type.save(ignore_permissions=True)


class TestActivityCostPermissions(FrappeTestCase):
	def setUp(self):
		self.employee_a = make_employee("activity-cost-a@example.com", company="_Test Company")
		self.employee_b = make_employee("activity-cost-b@example.com", company=OTHER_COMPANY)
		for employee, rate in ((self.employee_a, 111), (self.employee_b, 999)):
			frappe.get_doc(
				{
					"doctype": "Activity Cost",
					"employee": employee,
					"activity_type": "Planning",
					"costing_rate": rate,
					"billing_rate": rate * 2,
				}
			).insert()

	def tearDown(self):
		frappe.db.rollback()

	def cost_kwargs(self, name):
		return {"employee": name, "activity_type": "Planning"}

	def activity_kwargs(self, name):
		return {"employee": self.employee_a, "activity_type": name}

	def make_activity_fenced_user(self):
		insert_test_record(
			"Activity Type",
			{
				"name": "_Test Hidden Activity",
				"activity_type": "_Test Hidden Activity",
				"costing_rate": 7,
				"billing_rate": 14,
			},
		)
		return make_fenced_user(
			"activity-cost-activity@example.com", ["Projects User"], [("Activity Type", "Planning")]
		)

	def test_get_activity_cost_refuses_an_activity_type_outside_the_fence_for_an_employee(self):
		fenced = self.make_activity_fenced_user()
		with as_user(fenced):
			assert_refused(self, get_activity_cost, **self.activity_kwargs("_Test Hidden Activity"))
			rate = get_activity_cost(**self.activity_kwargs("Planning"))
		self.assertEqual(rate["costing_rate"], 111)

	def test_get_activity_cost_finds_no_malformed_activity_type_for_an_employee(self):
		fenced = self.make_activity_fenced_user()
		with as_user(fenced):
			for name in malformed_names():
				assert_not_found(self, get_activity_cost, **self.activity_kwargs(name))
			assert_refused(self, get_activity_cost, **self.activity_kwargs(""))

	def test_get_activity_cost_refuses_an_employee_outside_the_company_fence(self):
		fenced = make_company_fenced_user(
			"activity-cost-fenced@example.com", ["Projects User"], "_Test Company"
		)
		with as_user(fenced):
			assert_refused_for_names(
				self, get_activity_cost, self.cost_kwargs, [self.employee_b], caller_supplied=True
			)
			assert_refused_without(
				self,
				["linked to", "'_Test Company 1'"],
				get_activity_cost,
				**self.cost_kwargs(self.employee_b),
			)
			rate = get_activity_cost(**self.cost_kwargs(self.employee_a))
		self.assertEqual(rate["costing_rate"], 111)

	def test_get_activity_cost_refuses_an_employee_outside_the_employee_fence(self):
		fenced = make_fenced_user(
			"activity-cost-employee@example.com", ["Projects User"], [("Employee", self.employee_a)]
		)
		with as_user(fenced):
			assert_refused(self, get_activity_cost, **self.cost_kwargs(self.employee_b))

	def test_get_activity_cost_requires_timesheet_read(self):
		user = make_fenced_user("activity-cost-no-timesheet@example.com", ["Stock Manager"])
		with as_user(user):
			assert_refused(self, get_activity_cost, **self.cost_kwargs(self.employee_a))

	def test_get_activity_cost_allows_an_unfenced_projects_user(self):
		user = make_fenced_user("activity-cost-open@example.com", ["Projects User"])
		with as_user(user):
			rate = get_activity_cost(**self.cost_kwargs(self.employee_b))
		self.assertEqual(rate["billing_rate"], 1998)
