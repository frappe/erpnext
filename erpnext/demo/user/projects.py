# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe, erpnext
from frappe.utils import flt
from frappe.utils.make_random import get_random
from erpnext.projects.doctype.timesheet.test_timesheet import make_timesheet
from erpnext.demo.user.hr import make_sales_invoice_for_timesheet

def run_projects(current_date):
	frappe.set_user(frappe.db.get_global('demo_projects_user'))
	if frappe.db.get_global('demo_projects_user'):
		make_project(current_date)
		make_timesheet_for_projects(current_date)
		close_tasks(current_date)

def make_timesheet_for_projects(current_date	):
	for data in frappe.get_all("Task", ["name", "project"], {"status": "Open", "exp_end_date": ("<", current_date)}):
		employee = get_random("Employee")
		ts = make_timesheet(employee, simulate = True, billable = 1, company = erpnext.get_default_company(),
			activity_type=get_random("Activity Type"), project=data.project, task =data.name)

		if flt(ts.total_billable_amount) > 0.0:
			make_sales_invoice_for_timesheet(ts.name)
			frappe.db.commit()

def close_tasks(current_date):
	for task in frappe.get_all("Task", ["name"], {"status": "Open", "exp_end_date": ("<", current_date)}):
		task = frappe.get_doc("Task", task.name)
		task.status = "Closed"
		task.save()

def make_project(current_date):
	if not frappe.db.exists('Project', 
		"New Product Development " + current_date.strftime("%Y-%m-%d")):
		project = frappe.get_doc({
			"doctype": "Project",
			"project_name": "New Product Development " + current_date.strftime("%Y-%m-%d"),
		})
		project.set("tasks", [
				{
					"title": "Review Requirements",
					"start_date": frappe.utils.add_days(current_date, 10),
					"end_date": frappe.utils.add_days(current_date, 11)
				},
				{
					"title": "Design Options",
					"start_date": frappe.utils.add_days(current_date, 11),
					"end_date": frappe.utils.add_days(current_date, 20)
				},
				{
					"title": "Make Prototypes",
					"start_date": frappe.utils.add_days(current_date, 20),
					"end_date": frappe.utils.add_days(current_date, 30)
				},
				{
					"title": "Customer Feedback on Prototypes",
					"start_date": frappe.utils.add_days(current_date, 30),
					"end_date": frappe.utils.add_days(current_date, 40)
				},
				{
					"title": "Freeze Feature Set",
					"start_date": frappe.utils.add_days(current_date, 40),
					"end_date": frappe.utils.add_days(current_date, 45)
				},
				{
					"title": "Testing",
					"start_date": frappe.utils.add_days(current_date, 45),
					"end_date": frappe.utils.add_days(current_date, 60)
				},
				{
					"title": "Product Engineering",
					"start_date": frappe.utils.add_days(current_date, 45),
					"end_date": frappe.utils.add_days(current_date, 55)
				},
				{
					"title": "Supplier Contracts",
					"start_date": frappe.utils.add_days(current_date, 55),
					"end_date": frappe.utils.add_days(current_date, 70)
				},
				{
					"title": "Design and Build Fixtures",
					"start_date": frappe.utils.add_days(current_date, 45),
					"end_date": frappe.utils.add_days(current_date, 65)
				},
				{
					"title": "Test Run",
					"start_date": frappe.utils.add_days(current_date, 70),
					"end_date": frappe.utils.add_days(current_date, 80)
				},
				{
					"title": "Launch",
					"start_date": frappe.utils.add_days(current_date, 80),
					"end_date": frappe.utils.add_days(current_date, 90)
				},
			])
		project.insert()
