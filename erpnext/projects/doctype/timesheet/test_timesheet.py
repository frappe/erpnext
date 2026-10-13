# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import datetime
from unittest.mock import patch

import frappe
from frappe.utils import add_to_date, now_datetime, nowdate

from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_sales_return
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.projects.doctype.task.test_task import create_task
from erpnext.projects.doctype.timesheet.timesheet import (
	OverlapError,
	get_activity_cost,
	get_projectwise_timesheet_data,
	make_sales_invoice,
)
from erpnext.setup.doctype.employee.test_employee import make_employee
from erpnext.tests.permission_test_utils import (
	OTHER_COMPANY,
	as_user,
	assert_refused,
	assert_refused_for_names,
	assert_refused_without,
	make_company_fenced_user,
	make_fenced_user,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestTimesheet(ERPNextTestSuite):
	def test_get_projectwise_timesheet_data_without_allowed_projects(self):
		with patch("frappe.get_list", side_effect=[["TS-0001"], []]):
			self.assertEqual(get_projectwise_timesheet_data(), [])

	def test_time_log_with_empty_project_and_sales_invoice_is_unbilled(self):
		emp = make_employee("test_employee_6@salary.com", company="_Test Company")
		timesheet = make_timesheet(emp, simulate=True, is_billable=1)
		time_log = timesheet.time_logs[0].name
		frappe.db.set_value("Timesheet Detail", time_log, {"project": "", "sales_invoice": ""})

		self.assertEqual(
			[log.name for log in get_projectwise_timesheet_data(parent=timesheet.name)], [time_log]
		)

	def test_timesheet_post_update(self):
		frappe.get_doc(
			{
				"doctype": "Property Setter",
				"doctype_or_field": "DocField",
				"doc_type": "Timesheet",
				"field_name": "time_logs",
				"property": "allow_on_submit",
				"property_type": "Check",
				"value": "1",
			}
		).insert(ignore_permissions=True)

		task = create_task("Test Task 1")

		timesheet = frappe.new_doc("Timesheet")
		timesheet.append(
			"time_logs",
			{
				"task": task.name,
				"from_time": now_datetime(),
				"to_time": now_datetime() + datetime.timedelta(hours=1),
				"company": "_Test Company",
			},
		)

		timesheet.save()
		timesheet.submit()
		task.reload()
		self.assertEqual(task.actual_time, 1)
		timesheet.append(
			"time_logs",
			{
				"task": task.name,
				"from_time": now_datetime() + datetime.timedelta(hours=1),
				"to_time": now_datetime() + datetime.timedelta(hours=3),
				"hours": 2,
			},
		)

		timesheet.save()
		task.reload()
		self.assertEqual(task.actual_time, 3)

		frappe.db.delete(
			"Property Setter",
			{"doc_type": "Timesheet", "field_name": "time_logs", "property": "allow_on_submit"},
		)

	def test_task_status_follows_its_remaining_time_logs(self):
		emp = make_employee("test_employee_6@salary.com", company="_Test Company")
		task = create_task("_Test Timesheet Status Task")

		def log_time(completed=0):
			timesheet = make_timesheet(emp, simulate=True, task=task.name, do_not_submit=True)
			timesheet.time_logs[0].completed = completed
			return timesheet.submit()

		def task_status():
			return frappe.db.get_value("Task", task.name, "status")

		log_time().cancel()
		self.assertEqual(task_status(), "Open")

		completed = log_time(completed=1)
		later = log_time()
		self.assertEqual(task_status(), "Completed")
		later.cancel()
		self.assertEqual(task_status(), "Completed")

		frappe.db.set_value("Task", task.name, "status", "Cancelled")
		completed.cancel()
		self.assertEqual(task_status(), "Cancelled")

	def test_timesheet_base_amount(self):
		emp = make_employee("test_employee_6@salary.com", company="_Test Company")
		timesheet = make_timesheet(emp, simulate=True, is_billable=1)

		self.assertEqual(timesheet.time_logs[0].base_billing_rate, 50)
		self.assertEqual(timesheet.time_logs[0].base_costing_rate, 20)
		self.assertEqual(timesheet.time_logs[0].base_billing_amount, 100)
		self.assertEqual(timesheet.time_logs[0].base_costing_amount, 40)

	def test_base_amounts_use_the_exchange_rate_being_saved(self):
		emp = make_employee("test_employee_6@salary.com", company="_Test Company")
		timesheet = make_timesheet(emp, simulate=True, is_billable=1, exchange_rate=2, do_not_submit=True)

		self.assertEqual(timesheet.time_logs[0].base_billing_amount, 200)
		self.assertEqual(timesheet.base_total_billable_amount, 200)

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

	def test_billing_fields_cannot_change_after_submit(self):
		emp = make_employee("test_employee_6@salary.com", company="_Test Company")
		timesheet = make_timesheet(emp, simulate=True, is_billable=1)

		timesheet.time_logs[0].billing_hours = 10
		self.assertRaises(frappe.UpdateAfterSubmitError, timesheet.save)

	def test_timesheet_billing_amount(self):
		emp = make_employee("test_employee_6@salary.com", company="_Test Company")
		timesheet = make_timesheet(emp, simulate=True, is_billable=1)

		self.assertEqual(timesheet.total_hours, 2)
		self.assertEqual(timesheet.total_billable_hours, 2)
		self.assertEqual(timesheet.time_logs[0].billing_rate, 50)
		self.assertEqual(timesheet.time_logs[0].billing_amount, 100)
		self.assertEqual(timesheet.total_billable_amount, 100)

	def test_timesheet_billing_amount_not_billable(self):
		emp = make_employee("test_employee_6@salary.com", company="_Test Company")
		timesheet = make_timesheet(emp, simulate=True, is_billable=0)

		self.assertEqual(timesheet.total_hours, 2)
		self.assertEqual(timesheet.total_billable_hours, 0)
		self.assertEqual(timesheet.time_logs[0].billing_rate, 0)
		self.assertEqual(timesheet.time_logs[0].billing_amount, 0)
		self.assertEqual(timesheet.total_billable_amount, 0)

	def test_sales_invoice_from_timesheet(self):
		emp = make_employee("test_employee_6@salary.com", company="_Test Company")

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

	def test_sales_invoice_from_timesheet_needs_timesheet_read(self):
		emp = make_employee("test_employee_6@salary.com", company="_Test Company")
		timesheet = make_timesheet(emp, simulate=True, is_billable=1)
		sales_user = make_fenced_user("timesheet-invoice-sales@example.com", ["Sales User"])

		with as_user(sales_user):
			self.assertRaises(frappe.PermissionError, make_sales_invoice, timesheet.name)

	@ERPNextTestSuite.change_settings("Projects Settings", {"fetch_timesheet_in_sales_invoice": 1})
	def test_timesheet_billing_based_on_project(self):
		emp = make_employee("test_employee_6@salary.com", company="_Test Company")
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

	def test_invoice_row_without_time_log_keeps_its_amount(self):
		emp = make_employee("test_employee_6@salary.com", company="_Test Company")
		timesheet = make_timesheet(emp, simulate=True, is_billable=1)

		sales_invoice = create_sales_invoice(do_not_save=True)
		sales_invoice.append("timesheets", {"time_sheet": timesheet.name, "billing_amount": 70})
		sales_invoice.save()
		self.assertEqual(len(sales_invoice.timesheets), 1)
		self.assertEqual(sales_invoice.timesheets[0].timesheet_detail, timesheet.time_logs[0].name)
		self.assertEqual(sales_invoice.timesheets[0].billing_amount, 70)

		two_logs = make_timesheet(emp, simulate=True, is_billable=1, do_not_submit=True)
		log = two_logs.time_logs[0]
		two_logs.append(
			"time_logs",
			{
				"activity_type": log.activity_type,
				"is_billable": 1,
				"from_time": log.to_time,
				"to_time": add_to_date(log.to_time, hours=1),
				"hours": 1,
			},
		)
		two_logs.submit()
		sales_invoice = create_sales_invoice(do_not_save=True)
		sales_invoice.append("timesheets", {"time_sheet": two_logs.name, "billing_amount": 70})
		self.assertRaises(frappe.ValidationError, sales_invoice.save)

	def test_invoice_converts_time_log_amount_to_invoice_currency(self):
		from_time = add_to_date(now_datetime(), days=400)
		timesheet = frappe.get_doc(
			{
				"doctype": "Timesheet",
				"company": "_Test Company",
				"currency": "USD",
				"exchange_rate": 80,
				"time_logs": [
					{
						"is_billable": 1,
						"from_time": from_time,
						"to_time": add_to_date(from_time, hours=2),
						"hours": 2,
						"billing_hours": 2,
						"billing_rate": 50,
					}
				],
			}
		).submit()

		sales_invoice = create_sales_invoice(do_not_save=True)
		sales_invoice.append(
			"timesheets", {"time_sheet": timesheet.name, "timesheet_detail": timesheet.time_logs[0].name}
		)
		with patch("erpnext.accounts.doctype.sales_invoice.sales_invoice.get_exchange_rate", return_value=0):
			self.assertRaises(frappe.ValidationError, sales_invoice.save)

		with patch("erpnext.accounts.doctype.sales_invoice.sales_invoice.get_exchange_rate", return_value=80):
			sales_invoice.save()

		self.assertEqual(sales_invoice.timesheets[0].billing_amount, 8000)

	def _invoice_with_timesheet_row(self, time_sheet, timesheet_detail, with_amounts=True):
		sales_invoice = create_sales_invoice(do_not_save=True)
		row = {"time_sheet": time_sheet, "timesheet_detail": timesheet_detail}
		if with_amounts:
			row.update({"billing_hours": 2, "billing_amount": 100})
		sales_invoice.append("timesheets", row)
		return sales_invoice

	@ERPNextTestSuite.change_settings("Projects Settings", {"ignore_user_time_overlap": 0})
	def test_employees_without_a_user_do_not_overlap_each_other(self):
		from erpnext.patches.v16_0.set_user_on_timesheets import execute

		from_time = now_datetime()
		for first_name in ("_Test Userless One", "_Test Userless Two"):
			employee = frappe.get_doc(
				{
					"doctype": "Employee",
					"first_name": first_name,
					"company": "_Test Company",
					"gender": "Male",
					"date_of_birth": "1990-01-01",
					"date_of_joining": "2020-01-01",
				}
			).insert()
			timesheet = make_timesheet_without_employee(from_time, 1)
			timesheet.employee = employee.name
			timesheet.insert()
			self.assertFalse(timesheet.user)

		execute()
		self.assertFalse(frappe.db.get_value("Timesheet", timesheet.name, "user"))

	@ERPNextTestSuite.change_settings("Projects Settings", {"ignore_user_time_overlap": 0})
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

	@ERPNextTestSuite.change_settings("Projects Settings", {"ignore_user_time_overlap": 1})
	def test_timesheet_time_overlap(self):
		emp = make_employee("test_employee_6@salary.com", company="_Test Company")

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
		timesheet.submit()  # should not throw an error
		settings.ignore_employee_time_overlap = 0
		settings.save()

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
		self.assertRaises(frappe.ValidationError, timesheet.submit)

		settings.ignore_employee_time_overlap = initial_setting
		settings.save()

	def test_timesheet_not_overlapping_with_continuous_timelogs(self):
		emp = make_employee("test_employee_6@salary.com", company="_Test Company")

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
		emp = make_employee("test_employee_6@salary.com", company="_Test Company")
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
		emp = make_employee("test_employee_6@salary.com", company="_Test Company")

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

	def make_costed_employee(self, first_name, company, costing_rate, billing_rate):
		employee = frappe.get_doc(
			{
				"doctype": "Employee",
				"first_name": first_name,
				"company": company,
				"gender": "Male",
				"date_of_birth": "1990-01-01",
				"date_of_joining": "2020-01-01",
				"status": "Active",
			}
		).insert(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": "Activity Cost",
				"activity_type": "Planning",
				"employee": employee.name,
				"costing_rate": costing_rate,
				"billing_rate": billing_rate,
			}
		).insert(ignore_permissions=True)
		return employee.name

	def make_company_fenced_projects_user(self):
		return make_company_fenced_user(
			"activity_cost_fenced@example.com", ["Projects User"], "_Test Company"
		)

	def assert_rates(self, rate, costing_rate, billing_rate):
		self.assertEqual(rate.costing_rate, costing_rate)
		self.assertEqual(rate.billing_rate, billing_rate)

	def test_get_activity_cost_respects_company_user_permission(self):
		inside = self.make_costed_employee("Activity Cost Inside", "_Test Company", 11, 21)
		outside = self.make_costed_employee("Activity Cost Outside", OTHER_COMPANY, 91, 92)
		fenced_user = self.make_company_fenced_projects_user()
		unfenced_user = make_fenced_user("activity_cost_unfenced@example.com", ["Projects User"])

		with as_user(fenced_user):
			assert_refused_without(
				self,
				[OTHER_COMPANY, "Activity Cost Outside"],
				get_activity_cost,
				employee=outside,
				activity_type="Planning",
			)
			rate = get_activity_cost(employee=inside, activity_type="Planning")

		self.assert_rates(rate, 11, 21)

		with as_user(unfenced_user):
			rate = get_activity_cost(employee=outside, activity_type="Planning")

		self.assert_rates(rate, 91, 92)

	def test_get_activity_cost_respects_activity_type_user_permission(self):
		frappe.db.set_value("Activity Type", "Planning", {"costing_rate": 13, "billing_rate": 23})
		frappe.db.set_value("Activity Type", "Execution", {"costing_rate": 14, "billing_rate": 24})
		user = make_fenced_user(
			"activity_cost_type_fenced@example.com", ["Projects User"], [("Activity Type", "Planning")]
		)

		with as_user(user):
			assert_refused(self, get_activity_cost, activity_type="Execution")
			rate = get_activity_cost(activity_type="Planning")

		self.assert_rates(rate, 13, 23)

	def test_get_activity_cost_with_employee_refuses_activity_type_outside_user_permission(self):
		frappe.db.set_value("Activity Type", "Execution", {"costing_rate": 14, "billing_rate": 24})
		inside = self.make_costed_employee("Activity Cost Inside", "_Test Company", 11, 21)
		user = make_fenced_user(
			"activity_cost_type_fenced@example.com", ["Projects User"], [("Activity Type", "Planning")]
		)

		with as_user(user):
			assert_refused(self, get_activity_cost, employee=inside, activity_type="Execution")
			rate = get_activity_cost(employee=inside, activity_type="Planning")

		self.assert_rates(rate, 11, 21)

	def test_get_activity_cost_with_employee_refuses_forbidden_missing_and_malformed_activity_types(self):
		frappe.db.set_value("Activity Type", "Execution", {"costing_rate": 14, "billing_rate": 24})
		inside = self.make_costed_employee("Activity Cost Inside", "_Test Company", 11, 21)
		user = make_fenced_user(
			"activity_cost_type_fenced@example.com", ["Projects User"], [("Activity Type", "Planning")]
		)

		def with_employee(name):
			return {"employee": inside, "activity_type": name}

		with as_user(user):
			assert_refused_for_names(
				self,
				get_activity_cost,
				with_employee,
				["Execution"],
				type_gated=True,
				caller_supplied=True,
			)
			assert_refused(self, get_activity_cost, employee=inside)

	def test_get_activity_cost_refuses_forbidden_missing_and_malformed_names(self):
		inside = self.make_costed_employee("Activity Cost Inside", "_Test Company", 11, 21)
		outside = self.make_costed_employee("Activity Cost Outside", OTHER_COMPANY, 91, 92)
		user = self.make_company_fenced_projects_user()

		def as_employee(name):
			return {"employee": name, "activity_type": "Planning"}

		def as_activity_type(name):
			return {"activity_type": name}

		with as_user(user):
			assert_refused_without(
				self, [OTHER_COMPANY, "Activity Cost Outside"], get_activity_cost, **as_employee(outside)
			)
			assert_refused_for_names(
				self,
				get_activity_cost,
				as_employee,
				[[inside, outside]],
				type_gated=True,
				caller_supplied=True,
			)
			assert_refused_for_names(
				self, get_activity_cost, as_activity_type, [], type_gated=True, caller_supplied=True
			)
			assert_refused(self, get_activity_cost)

	def test_employee_activity_cost_is_converted_to_the_timesheet_currency(self):
		from erpnext.projects.doctype.timesheet.timesheet import get_activity_cost

		emp = make_employee("test_employee_6@salary.com", company="_Test Company")
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
				"currency": "USD",
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
			self.assertEqual(get_activity_cost(emp, "_Test Activity Type", "USD")["billing_rate"], 500)
			timesheet.insert()

		self.assertEqual(timesheet.time_logs[0].billing_rate, 500)
		self.assertEqual(timesheet.time_logs[0].costing_rate, 300)

	def test_activity_cost_refuses_a_missing_exchange_rate(self):
		from erpnext.projects.doctype.timesheet.timesheet import get_activity_cost

		with patch("erpnext.projects.doctype.timesheet.timesheet.get_exchange_rate", return_value=0):
			self.assertRaises(frappe.ValidationError, get_activity_cost, None, "_Test Activity Type", "EUR")

			timesheet = frappe.get_doc(
				{
					"doctype": "Timesheet",
					"company": "_Test Company",
					"currency": "EUR",
					"exchange_rate": 80,
					"time_logs": [
						{
							"activity_type": "_Test Activity Type",
							"is_billable": 1,
							"from_time": now_datetime(),
							"hours": 2,
							"billing_rate": 50,
							"costing_rate": 20,
						}
					],
				}
			).insert()

		self.assertEqual(timesheet.time_logs[0].billing_rate, 50)

	def test_default_activity_cost_applies_to_employees_without_their_own(self):
		from erpnext.projects.doctype.timesheet.timesheet import get_activity_cost

		update_activity_type("_Test Activity Type")
		emp = make_employee("test_employee_6@salary.com", company="_Test Company")
		frappe.get_doc(
			{
				"doctype": "Activity Cost",
				"activity_type": "_Test Activity Type",
				"billing_rate": 80,
				"costing_rate": 40,
			}
		).insert()

		rate = get_activity_cost(emp, "_Test Activity Type")
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
	currency=None,
	exchange_rate=None,
	do_not_submit=False,
):
	update_activity_type(activity_type)
	timesheet = frappe.new_doc("Timesheet")
	timesheet.employee = employee
	timesheet.company = company or "_Test Company"
	timesheet.exchange_rate = exchange_rate
	timesheet_detail = timesheet.append("time_logs", {})
	timesheet_detail.is_billable = is_billable
	timesheet_detail.activity_type = activity_type
	timesheet_detail.from_time = now_datetime()
	timesheet_detail.hours = 2
	timesheet_detail.to_time = timesheet_detail.from_time + datetime.timedelta(hours=timesheet_detail.hours)
	timesheet_detail.project = project
	timesheet_detail.task = task
	timesheet_detail.currency = currency

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
