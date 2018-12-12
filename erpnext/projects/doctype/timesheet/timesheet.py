# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

import json
from datetime import timedelta
from erpnext.controllers.queries import get_match_cond
from frappe.utils import flt, time_diff_in_hours, get_datetime, getdate, cint, date_diff, add_to_date
from frappe.model.document import Document
from erpnext.manufacturing.doctype.workstation.workstation import (check_if_within_operating_hours,
	WorkstationHolidayError)
from erpnext.manufacturing.doctype.manufacturing_settings.manufacturing_settings import get_mins_between_operations

class OverlapError(frappe.ValidationError): pass
class OverWorkLoggedError(frappe.ValidationError): pass

class Timesheet(Document):
	def onload(self):
		self.get("__onload").maintain_bill_work_hours_same = frappe.db.get_single_value('HR Settings', 'maintain_bill_work_hours_same')

	def validate(self):
		self.set_employee_name()
		self.set_status()
		self.validate_dates()
		self.validate_time_logs()
		self.calculate_std_hours()
		self.update_cost()
		self.calculate_total_amounts()
		self.calculate_percentage_billed()
		self.set_dates()

	def set_employee_name(self):
		if self.employee and not self.employee_name:
			self.employee_name = frappe.db.get_value('Employee', self.employee, 'employee_name')

	def calculate_total_amounts(self):
		self.total_hours = 0.0
		self.total_billable_hours = 0.0
		self.total_billed_hours = 0.0
		self.total_billable_amount = 0.0
		self.total_costing_amount = 0.0
		self.total_billed_amount = 0.0

		for d in self.get("time_logs"):
			self.update_billing_hours(d)
			self.update_time_rates(d)

			self.total_hours += flt(d.hours)
			self.total_costing_amount += flt(d.costing_amount)
			if d.billable:
				self.total_billable_hours += flt(d.billing_hours)
				self.total_billable_amount += flt(d.billing_amount)
				self.total_billed_amount += flt(d.billing_amount) if d.sales_invoice else 0.0
				self.total_billed_hours += flt(d.billing_hours) if d.sales_invoice else 0.0

	def calculate_percentage_billed(self):
		self.per_billed = 0
		if self.total_billed_amount > 0 and self.total_billable_amount > 0:
			self.per_billed = (self.total_billed_amount * 100) / self.total_billable_amount

	def update_billing_hours(self, args):
		if args.billable:
			if flt(args.billing_hours) == 0.0:
				args.billing_hours = args.hours
		else:
			args.billing_hours = 0

	def set_status(self):
		self.status = {
			"0": "Draft",
			"1": "Submitted",
			"2": "Cancelled"
		}[str(self.docstatus or 0)]

		if self.per_billed == 100:
			self.status = "Billed"

		if self.salary_slip:
			self.status = "Payslip"

		if self.sales_invoice and self.salary_slip:
			self.status = "Completed"

	def set_dates(self):
		if self.docstatus < 2 and self.time_logs:
			start_date = min([getdate(d.from_time) for d in self.time_logs])
			end_date = max([getdate(d.to_time) for d in self.time_logs])

			if start_date and end_date:
				self.start_date = getdate(start_date)
				self.end_date = getdate(end_date)

	def calculate_std_hours(self):
		std_working_hours = frappe.get_value("Company", self.company, 'standard_working_hours')

		for time in self.time_logs:
			if time.from_time and time.to_time:
				if flt(std_working_hours) > 0:
					time.hours = flt(std_working_hours) * date_diff(time.to_time, time.from_time)
				else:
					if not time.hours:
						time.hours = time_diff_in_hours(time.to_time, time.from_time)

	def before_cancel(self):
		self.set_status()

	def on_cancel(self):
		self.update_task_and_project()

	def on_submit(self):
		self.validate_mandatory_fields()
		self.update_task_and_project()

	def validate_mandatory_fields(self):
		for data in self.time_logs:
			if not data.from_time and not data.to_time:
				frappe.throw(_("Row {0}: From Time and To Time is mandatory.").format(data.idx))

			if not data.activity_type and self.employee:
				frappe.throw(_("Row {0}: Activity Type is mandatory.").format(data.idx))

			if flt(data.hours) == 0.0:
				frappe.throw(_("Row {0}: Hours value must be greater than zero.").format(data.idx))

	def update_task_and_project(self):
		tasks, projects = [], []

		for data in self.time_logs:
			if data.task and data.task not in tasks:
				task = frappe.get_doc("Task", data.task)
				task.update_time_and_costing()
				task.save()
				tasks.append(data.task)

			elif data.project and data.project not in projects:
				frappe.get_doc("Project", data.project).update_project()
				projects.append(data.project)

	def validate_dates(self):
		for data in self.time_logs:
			if data.from_time and data.to_time and time_diff_in_hours(data.to_time, data.from_time) < 0:
				frappe.throw(_("To date cannot be before from date"))

	def validate_time_logs(self):
		for data in self.get('time_logs'):
			self.validate_overlap(data)

	def validate_overlap(self, data):
		settings = frappe.get_single('Projects Settings')
		self.validate_overlap_for("user", data, self.user, settings.ignore_user_time_overlap)
		self.validate_overlap_for("employee", data, self.employee, settings.ignore_employee_time_overlap)

	def validate_overlap_for(self, fieldname, args, value, ignore_validation=False):
		if not value or ignore_validation:
			return

		existing = self.get_overlap_for(fieldname, args, value)
		if existing:
			frappe.throw(_("Row {0}: From Time and To Time of {1} is overlapping with {2}")
				.format(args.idx, self.name, existing.name), OverlapError)

	def get_overlap_for(self, fieldname, args, value):
		cond = "ts.`{0}`".format(fieldname)
		if fieldname == 'workstation':
			cond = "tsd.`{0}`".format(fieldname)

		existing = frappe.db.sql("""select ts.name as name, tsd.from_time as from_time, tsd.to_time as to_time from
			`tabTimesheet Detail` tsd, `tabTimesheet` ts where {0}=%(val)s and tsd.parent = ts.name and
			(
				(%(from_time)s > tsd.from_time and %(from_time)s < tsd.to_time) or
				(%(to_time)s > tsd.from_time and %(to_time)s < tsd.to_time) or
				(%(from_time)s <= tsd.from_time and %(to_time)s >= tsd.to_time))
			and tsd.name!=%(name)s
			and ts.name!=%(parent)s
			and ts.docstatus < 2""".format(cond),
			{
				"val": value,
				"from_time": args.from_time,
				"to_time": args.to_time,
				"name": args.name or "No Name",
				"parent": args.parent or "No Name"
			}, as_dict=True)
		# check internal overlap
		for time_log in self.time_logs:
			if (fieldname != 'workstation' or args.get(fieldname) == time_log.get(fieldname)) and \
				args.idx != time_log.idx and ((args.from_time > time_log.from_time and args.from_time < time_log.to_time) or
				(args.to_time > time_log.from_time and args.to_time < time_log.to_time) or
				(args.from_time <= time_log.from_time and args.to_time >= time_log.to_time)):
				return self

		return existing[0] if existing else None

	def update_cost(self):
		for data in self.time_logs:
			if data.activity_type or data.billable:
				rate = get_activity_cost(self.employee, data.activity_type)
				hours = data.billing_hours or 0
				costing_hours = data.billing_hours or data.hours or 0
				if rate:
					data.billing_rate = flt(rate.get('billing_rate')) if flt(data.billing_rate) == 0 else data.billing_rate
					data.costing_rate = flt(rate.get('costing_rate')) if flt(data.costing_rate) == 0 else data.costing_rate
					data.billing_amount = data.billing_rate * hours
					data.costing_amount = data.costing_rate * costing_hours

	def update_time_rates(self, ts_detail):
		if not ts_detail.billable:
			ts_detail.billing_rate = 0.0

@frappe.whitelist()
def get_projectwise_timesheet_data(project, parent=None):
	cond = ''
	if parent:
		cond = "and parent = %(parent)s"

	return frappe.db.sql("""select name, parent, billing_hours, billing_amount as billing_amt
			from `tabTimesheet Detail` where parenttype = 'Timesheet' and docstatus=1 and project = %(project)s {0} and billable = 1
			and sales_invoice is null""".format(cond), {'project': project, 'parent': parent}, as_dict=1)

@frappe.whitelist()
def get_timesheet(doctype, txt, searchfield, start, page_len, filters):
	if not filters: filters = {}

	condition = ""
	if filters.get("project"):
		condition = "and tsd.project = %(project)s"

	return frappe.db.sql("""select distinct tsd.parent from `tabTimesheet Detail` tsd,
			`tabTimesheet` ts where
			ts.status in ('Submitted', 'Payslip') and tsd.parent = ts.name and
			tsd.docstatus = 1 and ts.total_billable_amount > 0
			and tsd.parent LIKE %(txt)s {condition}
			order by tsd.parent limit %(start)s, %(page_len)s"""
			.format(condition=condition), {
				'txt': '%' + txt + '%',
				"start": start, "page_len": page_len, 'project': filters.get("project")
			})

@frappe.whitelist()
def get_timesheet_data(name, project):
	data = None
	if project and project!='':
		data = get_projectwise_timesheet_data(project, name)
	else:
		data = frappe.get_all('Timesheet',
			fields = ["(total_billable_amount - total_billed_amount) as billing_amt", "total_billable_hours as billing_hours"], filters = {'name': name})
	return {
		'billing_hours': data[0].billing_hours if data else None,
		'billing_amount': data[0].billing_amt if data else None,
		'timesheet_detail': data[0].name if data and project and project!= '' else None
	}

@frappe.whitelist()
def make_sales_invoice(source_name, item_code=None, customer=None):
	target = frappe.new_doc("Sales Invoice")
	timesheet = frappe.get_doc('Timesheet', source_name)

	if not timesheet.total_billable_hours:
		frappe.throw(_("Invoice can't be made for zero billing hour"))

	if timesheet.total_billable_hours == timesheet.total_billed_hours:
		frappe.throw(_("Invoice already created for all billing hours"))

	hours = flt(timesheet.total_billable_hours) - flt(timesheet.total_billed_hours)
	billing_amount = flt(timesheet.total_billable_amount) - flt(timesheet.total_billed_amount)
	billing_rate = billing_amount / hours

	target.company = timesheet.company
	if customer:
		target.customer = customer

	if item_code:
		target.append('items', {
			'item_code': item_code,
			'qty': hours,
			'rate': billing_rate
		})

	target.append('timesheets', {
		'time_sheet': timesheet.name,
		'billing_hours': hours,
		'billing_amount': billing_amount
	})

	target.run_method("calculate_billing_amount_for_timesheet")
	target.run_method("set_missing_values")

	return target

@frappe.whitelist()
def make_salary_slip(source_name, target_doc=None):
	target = frappe.new_doc("Salary Slip")
	set_missing_values(source_name, target)
	target.run_method("get_emp_and_leave_details")

	return target

def set_missing_values(time_sheet, target):
	doc = frappe.get_doc('Timesheet', time_sheet)
	target.employee = doc.employee
	target.employee_name = doc.employee_name
	target.salary_slip_based_on_timesheet = 1
	target.start_date = doc.start_date
	target.end_date = doc.end_date
	target.posting_date = doc.modified
	target.total_working_hours = doc.total_hours
	target.append('timesheets', {
		'time_sheet': doc.name,
		'working_hours': doc.total_hours
	})

@frappe.whitelist()
def get_activity_cost(employee=None, activity_type=None):
	rate = frappe.db.get_values("Activity Cost", {"employee": employee,
		"activity_type": activity_type}, ["costing_rate", "billing_rate"], as_dict=True)
	if not rate:
		rate = frappe.db.get_values("Activity Type", {"activity_type": activity_type},
			["costing_rate", "billing_rate"], as_dict=True)

	return rate[0] if rate else {}

@frappe.whitelist()
def get_events(start, end, filters=None):
	"""Returns events for Gantt / Calendar view rendering.
	:param start: Start date-time.
	:param end: End date-time.
	:param filters: Filters (JSON).
	"""
	#filters = json.loads(filters)
	from frappe.desk.calendar import get_event_conditions
	conditions = get_event_conditions("Timesheet", filters)

	return frappe.db.sql("""select `tabTimesheet Detail`.name as name, note,
			`tabTimesheet Detail`.docstatus as status, `tabTimesheet Detail`.parent as parent,
			from_time as start_date, hours, activity_type,
			`tabTimesheet Detail`.project, to_time as end_date,
			CONCAT(`tabTimesheet Detail`.parent, ' (', ROUND(hours,2),' hrs)') as title
		from `tabTimesheet Detail`, `tabTimesheet`
		where `tabTimesheet Detail`.parent = `tabTimesheet`.name
			and `tabTimesheet`.docstatus < 2
			and (from_time <= %(end)s and to_time >= %(start)s) {conditions} {match_cond}
		""".format(conditions=conditions, match_cond = get_match_cond('Timesheet')),
		{
			"start": start,
			"end": end
		}, as_dict=True, update={"allDay": 0})

def get_timesheets_list(doctype, txt, filters, limit_start, limit_page_length=20, order_by="modified"):
	user = frappe.session.user
	# find customer name from contact.
	customer = frappe.db.sql('''SELECT dl.link_name FROM `tabContact` AS c inner join \
		`tabDynamic Link` AS dl ON c.first_name=dl.link_name WHERE c.email_id=%s''',user)

	if customer:
		# find list of Sales Invoice for made for customer.
		sales_invoice = frappe.db.sql('''SELECT name FROM `tabSales Invoice` WHERE customer = %s''',customer)
		# Return timesheet related data to web portal.
		return frappe. db.sql('''SELECT ts.name, tsd.activity_type, ts.status, ts.total_billable_hours, \
			tsd.sales_invoice, tsd.project  FROM `tabTimesheet` AS ts inner join `tabTimesheet Detail` \
			AS tsd ON tsd.parent = ts.name where tsd.sales_invoice IN %s order by\
			end_date asc limit {0} , {1}'''.format(limit_start, limit_page_length), [sales_invoice], as_dict = True)

def get_list_context(context=None):
	return {
		"show_sidebar": True,
		"show_search": True,
		'no_breadcrumbs': True,
		"title": _("Timesheets"),
		"get_list": get_timesheets_list,
		"row_template": "templates/includes/timesheet/timesheet_row.html"
	}
