# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

import json
from datetime import timedelta
from erpnext.controllers.queries import get_match_cond
from frappe.utils import flt, time_diff_in_hours, get_datetime, getdate, cint
from frappe.model.document import Document
from erpnext.manufacturing.doctype.workstation.workstation import (check_if_within_operating_hours,
	WorkstationHolidayError)
from erpnext.manufacturing.doctype.manufacturing_settings.manufacturing_settings import get_mins_between_operations

class OverlapError(frappe.ValidationError): pass
class OverProductionLoggedError(frappe.ValidationError): pass

class Timesheet(Document):
	def onload(self):
		self.get("__onload").maintain_bill_work_hours_same = frappe.db.get_single_value('HR Settings', 'maintain_bill_work_hours_same')

	def validate(self):
		self.set_employee_name()
		self.set_status()
		self.validate_dates()
		self.validate_time_logs()
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
			if d.billable:
				self.total_billable_hours += flt(d.billing_hours)
				self.total_billable_amount += flt(d.billing_amount)
				self.total_costing_amount += flt(d.costing_amount)
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

	def before_cancel(self):
		self.set_status()

	def on_cancel(self):
		self.update_production_order(None)
		self.update_task_and_project()

	def on_submit(self):
		self.validate_mandatory_fields()
		self.update_production_order(self.name)
		self.update_task_and_project()

	def validate_mandatory_fields(self):
		if self.production_order:
			production_order = frappe.get_doc("Production Order", self.production_order)
			pending_qty = flt(production_order.qty) - flt(production_order.produced_qty)

		for data in self.time_logs:
			if not data.from_time and not data.to_time:
				frappe.throw(_("Row {0}: From Time and To Time is mandatory.").format(data.idx))

			if not data.activity_type and self.employee:
				frappe.throw(_("Row {0}: Activity Type is mandatory.").format(data.idx))

			if flt(data.hours) == 0.0:
				frappe.throw(_("Row {0}: Hours value must be greater than zero.").format(data.idx))

			if self.production_order and flt(data.completed_qty) == 0:
				frappe.throw(_("Row {0}: Completed Qty must be greater than zero.").format(data.idx))

			if self.production_order and flt(pending_qty) < flt(data.completed_qty) and flt(pending_qty) > 0:
				frappe.throw(_("Row {0}: Completed Qty cannot be more than {1} for operation {2}").format(data.idx, pending_qty, data.operation),
					OverProductionLoggedError)

	def update_production_order(self, time_sheet):
		if self.production_order:
			pro = frappe.get_doc('Production Order', self.production_order)

			for timesheet in self.time_logs:
				for data in pro.operations:
					if data.name == timesheet.operation_id:
						summary = self.get_actual_timesheet_summary(timesheet.operation_id)
						data.time_sheet = time_sheet
						data.completed_qty = summary.completed_qty
						data.actual_operation_time = summary.mins
						data.actual_start_time = summary.from_time
						data.actual_end_time = summary.to_time

			pro.flags.ignore_validate_update_after_submit = True
			pro.update_operation_status()
			pro.calculate_operating_cost()
			pro.set_actual_dates()
			pro.save()

	def get_actual_timesheet_summary(self, operation_id):
		"""Returns 'Actual Operating Time'. """
		return frappe.db.sql("""select
			sum(tsd.hours*60) as mins, sum(tsd.completed_qty) as completed_qty, min(tsd.from_time) as from_time,
			max(tsd.to_time) as to_time from `tabTimesheet Detail` as tsd, `tabTimesheet` as ts where
			ts.production_order = %s and tsd.operation_id = %s and ts.docstatus=1 and ts.name = tsd.parent""",
			(self.production_order, operation_id), as_dict=1)[0]

	def update_task_and_project(self):
		for data in self.time_logs:
			if data.task:
				task = frappe.get_doc("Task", data.task)
				task.update_time_and_costing()
				task.save()

			elif data.project:
				frappe.get_doc("Project", data.project).update_project()

	def validate_dates(self):
		for data in self.time_logs:
			if data.from_time and data.to_time and time_diff_in_hours(data.to_time, data.from_time) < 0:
				frappe.throw(_("To date cannot be before from date"))

	def validate_time_logs(self):
		for data in self.get('time_logs'):
			self.check_workstation_timings(data)
			self.validate_overlap(data)

	def validate_overlap(self, data):
		if self.production_order:
			self.validate_overlap_for("workstation", data, data.workstation)
		else:
			self.validate_overlap_for("user", data, self.user)
			self.validate_overlap_for("employee", data, self.employee)

	def validate_overlap_for(self, fieldname, args, value):
		if not value: return

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

	def check_workstation_timings(self, args):
		"""Checks if **Time Log** is between operating hours of the **Workstation**."""
		if args.workstation and args.from_time and args.to_time:
			check_if_within_operating_hours(args.workstation, args.operation, args.from_time, args.to_time)

	def schedule_for_production_order(self, index):
		for data in self.time_logs:
			if data.idx == index:
				self.move_to_next_day(data) #check for workstation holiday
				self.move_to_next_non_overlapping_slot(data) #check for overlap
				break

	def move_to_next_non_overlapping_slot(self, data):
		overlapping = self.get_overlap_for("workstation", data, data.workstation)
		if overlapping:
			time_sheet = self.get_last_working_slot(overlapping.name, data.workstation)
			data.from_time = get_datetime(time_sheet.to_time) + get_mins_between_operations()
			data.to_time = self.get_to_time(data)
			self.check_workstation_working_day(data)

	def get_last_working_slot(self, time_sheet, workstation):
		return frappe.db.sql(""" select max(from_time) as from_time, max(to_time) as to_time
			from `tabTimesheet Detail` where workstation = %(workstation)s""",
			{'workstation': workstation}, as_dict=True)[0]

	def move_to_next_day(self, data):
		"""Move start and end time one day forward"""
		self.check_workstation_working_day(data)

	def check_workstation_working_day(self, data):
		while True:
			try:
				self.check_workstation_timings(data)
				break
			except WorkstationHolidayError:
				if frappe.message_log: frappe.message_log.pop()
				data.from_time = get_datetime(data.from_time) + timedelta(hours=24)
				data.to_time = self.get_to_time(data)

	def get_to_time(self, data):
		return get_datetime(data.from_time) + timedelta(hours=data.hours)

	def update_cost(self):
		for data in self.time_logs:
			if data.activity_type and data.billable:
				rate = get_activity_cost(self.employee, data.activity_type)
				hours = data.billing_hours or 0
				if rate:
					data.billing_rate = flt(rate.get('billing_rate')) if flt(data.billing_rate) == 0 else data.billing_rate
					data.costing_rate = flt(rate.get('costing_rate')) if flt(data.costing_rate) == 0 else data.costing_rate
					data.billing_amount = data.billing_rate * hours
					data.costing_amount = data.costing_rate * hours

	def update_time_rates(self, ts_detail):
		if not ts_detail.billable:
			ts_detail.billing_rate = 0.0
			ts_detail.costing_rate = 0.0


@frappe.whitelist()
def get_projectwise_timesheet_data(project, parent=None):
	cond = ''
	if parent:
		cond = "and parent = %(parent)s"

	return frappe.db.sql("""select name, parent, billing_hours, billing_amount as billing_amt
			from `tabTimesheet Detail` where docstatus=1 and project = %(project)s {0} and billable = 1
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
				"txt": "%%%s%%" % frappe.db.escape(txt),
				"start": start, "page_len": page_len, 'project': filters.get("project")
			})

@frappe.whitelist()
def get_timesheet_data(name, project):
	if project and project!='':
		data = get_projectwise_timesheet_data(project, name)
	else:
		data = frappe.get_all('Timesheet',
			fields = ["(total_billable_amount - total_billed_amount) as billing_amt", "total_billable_hours as billing_hours"], filters = {'name': name})

	return {
		'billing_hours': data[0].billing_hours,
		'billing_amount': data[0].billing_amt,
		'timesheet_detail': data[0].name if project and project!= '' else None
	}

@frappe.whitelist()
def make_sales_invoice(source_name, target=None):
	target = frappe.new_doc("Sales Invoice")
	timesheet = frappe.get_doc('Timesheet', source_name)

	target.append('timesheets', {
		'time_sheet': timesheet.name,
		'billing_hours': flt(timesheet.total_billable_hours) - flt(timesheet.total_billed_hours),
		'billing_amount': flt(timesheet.total_billable_amount) - flt(timesheet.total_billed_amount)
	})

	target.run_method("calculate_billing_amount_for_timesheet")

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
	filters = json.loads(filters)
	from frappe.desk.calendar import get_event_conditions
	conditions = get_event_conditions("Timesheet", filters)

	return frappe.db.sql("""select `tabTimesheet Detail`.name as name,
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
	# find list of Sales Invoice for made for customer.
	sales_invoice = frappe.db.sql('''SELECT name FROM `tabSales Invoice` WHERE customer = %s''',customer)
	if customer:
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
