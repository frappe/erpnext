# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import datetime

import frappe
from frappe.utils import add_to_date, now_datetime, nowdate

from erpnext.accounts.doctype.sales_invoice.mapper import make_sales_return
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.projects.doctype.task.test_task import create_task
from erpnext.projects.doctype.timesheet.timesheet import OverlapError, make_sales_invoice
from erpnext.setup.doctype.employee.test_employee import make_employee
from erpnext.tests.utils import ERPNextTestSuite


class TestTimesheet(ERPNextTestSuite):
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
				"from_time": now_datetime(),
				"to_time": now_datetime() + datetime.timedelta(hours=2),
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

	def test_timesheet_base_amount(self):
		emp = make_employee("test_employee_6@salary.com", company="_Test Company")
		timesheet = make_timesheet(emp, simulate=True, is_billable=1)

		self.assertEqual(timesheet.time_logs[0].base_billing_rate, 50)
		self.assertEqual(timesheet.time_logs[0].base_costing_rate, 20)
		self.assertEqual(timesheet.time_logs[0].base_billing_amount, 100)
		self.assertEqual(timesheet.time_logs[0].base_costing_amount, 40)

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

	def _bill_timesheet_into_invoice(self, emp):
		"""Submit a billable timesheet into a Sales Invoice; return (timesheet, invoice)."""
		timesheet = make_timesheet(emp, simulate=True, is_billable=1)
		sales_invoice = make_sales_invoice(timesheet.name, "_Test Item", "_Test Customer", currency="INR")
		sales_invoice.due_date = nowdate()
		sales_invoice.submit()
		timesheet.reload()
		# Submitting links the timesheet detail to the invoice and marks it billed
		self.assertEqual(timesheet.time_logs[0].sales_invoice, sales_invoice.name)
		self.assertEqual(timesheet.status, "Billed")
		return timesheet, sales_invoice

	def test_timesheet_billing_link_lifecycle(self):
		emp = make_employee("test_employee_6@salary.com", company="_Test Company")

		with self.subTest("link released on cancel"):
			timesheet, sales_invoice = self._bill_timesheet_into_invoice(emp)
			sales_invoice.reload()
			sales_invoice.cancel()
			timesheet.reload()
			self.assertFalse(timesheet.time_logs[0].sales_invoice)
			self.assertNotEqual(timesheet.status, "Billed")

		with self.subTest("link released on sales return"):
			timesheet, sales_invoice = self._bill_timesheet_into_invoice(emp)
			sales_return = make_sales_return(sales_invoice.name)
			sales_return.insert()
			sales_return.submit()
			timesheet.reload()
			self.assertFalse(timesheet.time_logs[0].sales_invoice)

	def test_timesheet_billing_validations(self):
		emp = make_employee("test_employee_6@salary.com", company="_Test Company")

		with self.subTest("unsubmitted timesheet is rejected"):
			draft = make_timesheet(emp, simulate=True, is_billable=1, do_not_submit=True)
			sales_invoice = self._invoice_with_timesheet_row(draft.name, draft.time_logs[0].name)
			self.assertRaises(frappe.ValidationError, sales_invoice.save)

		with self.subTest("already invoiced detail is rejected"):
			timesheet, _ = self._bill_timesheet_into_invoice(emp)
			sales_invoice = self._invoice_with_timesheet_row(timesheet.name, timesheet.time_logs[0].name)
			self.assertRaises(frappe.ValidationError, sales_invoice.save)

	@ERPNextTestSuite.change_settings("Projects Settings", {"fetch_timesheet_in_sales_invoice": 1})
	def test_timesheet_billing_data_population(self):
		emp = make_employee("test_employee_6@salary.com", company="_Test Company")

		with self.subTest("blank hours/amount are back-filled from the timesheet"):
			timesheet = make_timesheet(emp, simulate=True, is_billable=1)
			sales_invoice = self._invoice_with_timesheet_row(
				timesheet.name, timesheet.time_logs[0].name, with_amounts=False
			)
			sales_invoice.save()
			self.assertEqual(sales_invoice.timesheets[0].billing_hours, 2)
			self.assertEqual(sales_invoice.timesheets[0].billing_amount, 100)

		with self.subTest("project invoice auto-fetches the project's timesheets"):
			project = frappe.get_value("Project", {"project_name": "_Test Project"})
			make_timesheet(emp, simulate=True, is_billable=1, project=project, company="_Test Company")
			sales_invoice = create_sales_invoice(do_not_save=True)
			sales_invoice.project = project
			sales_invoice.set("timesheets", [])
			sales_invoice.save()
			self.assertTrue(sales_invoice.timesheets)

	def _invoice_with_timesheet_row(self, time_sheet, timesheet_detail, with_amounts=True):
		sales_invoice = create_sales_invoice(do_not_save=True)
		row = {"time_sheet": time_sheet, "timesheet_detail": timesheet_detail}
		if with_amounts:
			row.update({"billing_hours": 2, "billing_amount": 100})
		sales_invoice.append("timesheets", row)
		return sales_invoice

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

	def test_get_timesheets_list_portal_sales_invoice(self):
		# get_timesheets_list selects COALESCE(timesheet.sales_invoice, detail.sales_invoice). The earlier
		# `timesheet.sales_invoice | detail.sales_invoice` bitwise-ORed two varchars -- it errored on
		# Postgres and returned 0 (names cast to int) on MariaDB.
		from erpnext.projects.doctype.timesheet.timesheet import get_timesheets_list

		customer = "_Test Customer"

		# tie the current user (Administrator) to the customer so the portal resolves it
		contact = frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": "_Test Timesheet Portal Contact",
				"user": "Administrator",
				"links": [{"link_doctype": "Customer", "link_name": customer}],
			}
		).insert(ignore_permissions=True)
		self.addCleanup(self._delete_if_exists, "Contact", contact.name)

		si = create_sales_invoice(customer=customer)

		employee = make_employee("_test_timesheet_portal@example.com", company="_Test Company")
		timesheet = make_timesheet(employee, is_billable=0)
		frappe.db.set_value("Timesheet", timesheet.name, "sales_invoice", si.name)

		rows = get_timesheets_list("Timesheet", None, {}, 0, 500)

		row = next((r for r in rows if r.name == timesheet.name), None)
		self.assertIsNotNone(row, "billed timesheet not returned by portal list")
		self.assertEqual(row.sales_invoice, si.name)

	def test_get_activity_cost_falls_back_to_activity_type(self):
		from erpnext.projects.doctype.timesheet.timesheet import get_activity_cost

		update_activity_type("_Test Activity Type")
		# no employee-specific Activity Cost row, so the Activity Type rates are used
		rate = get_activity_cost(employee=None, activity_type="_Test Activity Type")
		self.assertEqual(rate["billing_rate"], 50.0)
		self.assertEqual(rate["costing_rate"], 20.0)

		# an unknown activity type yields an empty dict, not an error
		self.assertEqual(get_activity_cost(activity_type="__Nonexistent Activity__"), {})

	def test_billing_helpers_for_timesheet_detail(self):
		from erpnext.projects.doctype.timesheet.timesheet import (
			get_timesheet_data,
			get_timesheet_detail_rate,
		)

		employee = make_employee("_test_timesheet_billing_helpers@example.com", company="_Test Company")
		timesheet = make_timesheet(employee, is_billable=1, simulate=True)
		detail = timesheet.time_logs[0]

		# 2 billable hours at a billing rate of 50
		data = get_timesheet_data(timesheet.name, project="")
		self.assertEqual(data["billing_hours"], 2)
		self.assertEqual(data["billing_amount"], 100)

		# same currency on both sides, so the rate is the raw billing amount
		rate = get_timesheet_detail_rate(detail.name, timesheet.currency)
		self.assertEqual(rate, detail.billing_amount)

	@staticmethod
	def _delete_if_exists(doctype, name):
		if frappe.db.exists(doctype, name):
			frappe.delete_doc(doctype, name, force=True)


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
