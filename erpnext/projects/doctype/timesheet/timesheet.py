# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_to_date, flt, get_datetime, getdate, time_diff_in_hours

from erpnext.controllers.queries import get_match_cond
from erpnext.hr.utils import validate_active_employee
from erpnext.setup.utils import get_exchange_rate


class OverlapError(frappe.ValidationError):
	pass


class OverWorkLoggedError(frappe.ValidationError):
	pass


class Timesheet(Document):
	def validate(self):
		if self.employee:
			validate_active_employee(self.employee)
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
			self.employee_name = frappe.db.get_value("Employee", self.employee, "employee_name")

	def calculate_total_amounts(self):
		self.total_hours = 0.0
		self.total_billable_hours = 0.0
		self.total_billed_hours = 0.0
		self.total_billable_amount = self.base_total_billable_amount = 0.0
		self.total_costing_amount = self.base_total_costing_amount = 0.0
		self.total_billed_amount = self.base_total_billed_amount = 0.0

		for d in self.get("time_logs"):
			self.update_billing_hours(d)
			self.update_time_rates(d)

			self.total_hours += flt(d.hours)
			self.total_costing_amount += flt(d.costing_amount)
			self.base_total_costing_amount += flt(d.base_costing_amount)
			if d.is_billable:
				self.total_billable_hours += flt(d.billing_hours)
				self.total_billable_amount += flt(d.billing_amount)
				self.base_total_billable_amount += flt(d.base_billing_amount)
				self.total_billed_amount += flt(d.billing_amount) if d.sales_invoice else 0.0
				self.base_total_billed_amount += flt(d.base_billing_amount) if d.sales_invoice else 0.0
				self.total_billed_hours += flt(d.billing_hours) if d.sales_invoice else 0.0

	def calculate_percentage_billed(self):
		self.per_billed = 0
		if self.total_billed_amount > 0 and self.total_billable_amount > 0:
			self.per_billed = (self.total_billed_amount * 100) / self.total_billable_amount

	def update_billing_hours(self, args):
		if args.is_billable:
			if flt(args.billing_hours) == 0.0:
				args.billing_hours = args.hours
		else:
			args.billing_hours = 0

	def set_status(self):
		self.status = {"0": "Draft", "1": "Submitted", "2": "Cancelled"}[str(self.docstatus or 0)]

		if self.per_billed == 100:
			self.status = "Billed"

		if self.salary_slip:
			self.status = "Payslip"

		if self.sales_invoice and self.salary_slip:
			self.status = "Completed"

	def set_dates(self):
		if self.docstatus < 2 and self.time_logs:
			start_date = min(getdate(d.from_time) for d in self.time_logs)
			end_date = max(getdate(d.to_time) for d in self.time_logs)

			if start_date and end_date:
				self.start_date = getdate(start_date)
				self.end_date = getdate(end_date)

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
		for data in self.get("time_logs"):
			self.set_to_time(data)
			self.validate_overlap(data)
			self.set_project(data)
			self.validate_project(data)

	def set_to_time(self, data):
		if not (data.from_time and data.hours):
			return

		_to_time = get_datetime(add_to_date(data.from_time, hours=data.hours, as_datetime=True))
		if data.to_time != _to_time:
			data.to_time = _to_time

	def validate_overlap(self, data):
		settings = frappe.get_single("Projects Settings")
		self.validate_overlap_for("user", data, self.user, settings.ignore_user_time_overlap)
		self.validate_overlap_for("employee", data, self.employee, settings.ignore_employee_time_overlap)

	def set_project(self, data):
		data.project = data.project or frappe.db.get_value("Task", data.task, "project")

	def validate_project(self, data):
		if self.parent_project and self.parent_project != data.project:
			frappe.throw(
				_("Row {0}: Project must be same as the one set in the Timesheet: {1}.").format(
					data.idx, self.parent_project
				)
			)

	def validate_overlap_for(self, fieldname, args, value, ignore_validation=False):
		if not value or ignore_validation:
			return

		existing = self.get_overlap_for(fieldname, args, value)
		if existing:
			frappe.throw(
				_("Row {0}: From Time and To Time of {1} is overlapping with {2}").format(
					args.idx, self.name, existing.name
				),
				OverlapError,
			)

	def get_overlap_for(self, fieldname, args, value):
		timesheet = frappe.qb.DocType("Timesheet")
		timelog = frappe.qb.DocType("Timesheet Detail")

		from_time = get_datetime(args.from_time)
		to_time = get_datetime(args.to_time)

		existing = (
			frappe.qb.from_(timesheet)
			.join(timelog)
			.on(timelog.parent == timesheet.name)
			.select(
				timesheet.name.as_("name"), timelog.from_time.as_("from_time"), timelog.to_time.as_("to_time")
			)
			.where(
				(timelog.name != (args.name or "No Name"))
				& (timesheet.name != (args.parent or "No Name"))
				& (timesheet.docstatus < 2)
				& (timesheet[fieldname] == value)
				& (
					((from_time > timelog.from_time) & (from_time < timelog.to_time))
					| ((to_time > timelog.from_time) & (to_time < timelog.to_time))
					| ((from_time <= timelog.from_time) & (to_time >= timelog.to_time))
				)
			)
		).run(as_dict=True)

		if self.check_internal_overlap(fieldname, args):
			return self

		return existing[0] if existing else None

	def check_internal_overlap(self, fieldname, args):
		for time_log in self.time_logs:
			if not (time_log.from_time and time_log.to_time and args.from_time and args.to_time):
				continue

			from_time = get_datetime(time_log.from_time)
			to_time = get_datetime(time_log.to_time)
			args_from_time = get_datetime(args.from_time)
			args_to_time = get_datetime(args.to_time)

			if (
				(args.get(fieldname) == time_log.get(fieldname))
				and (args.idx != time_log.idx)
				and (
					(args_from_time > from_time and args_from_time < to_time)
					or (args_to_time > from_time and args_to_time < to_time)
					or (args_from_time <= from_time and args_to_time >= to_time)
				)
			):
				return True
		return False

	def update_cost(self):
		for data in self.time_logs:
			if data.activity_type or data.is_billable:
				rate = get_activity_cost(self.employee, data.activity_type)
				hours = data.billing_hours or 0
				costing_hours = data.billing_hours or data.hours or 0
				if rate:
					data.billing_rate = (
						flt(rate.get("billing_rate")) if flt(data.billing_rate) == 0 else data.billing_rate
					)
					data.costing_rate = (
						flt(rate.get("costing_rate")) if flt(data.costing_rate) == 0 else data.costing_rate
					)
					data.billing_amount = data.billing_rate * hours
					data.costing_amount = data.costing_rate * costing_hours

	def update_time_rates(self, ts_detail):
		if not ts_detail.is_billable:
			ts_detail.billing_rate = 0.0


@frappe.whitelist()
def get_projectwise_timesheet_data(project=None, parent=None, from_time=None, to_time=None):
	condition = ""
	if project:
		condition += "AND tsd.project = %(project)s "
	if parent:
		condition += "AND tsd.parent = %(parent)s "
	if from_time and to_time:
		condition += "AND CAST(tsd.from_time as DATE) BETWEEN %(from_time)s AND %(to_time)s"

	query = f"""
		SELECT
			tsd.name as name,
			tsd.parent as time_sheet,
			tsd.from_time as from_time,
			tsd.to_time as to_time,
			tsd.billing_hours as billing_hours,
			tsd.billing_amount as billing_amount,
			tsd.activity_type as activity_type,
			tsd.description as description,
			ts.currency as currency,
			tsd.project_name as project_name
		FROM `tabTimesheet Detail` tsd
			INNER JOIN `tabTimesheet` ts
			ON ts.name = tsd.parent
		WHERE
			tsd.parenttype = 'Timesheet'
			AND tsd.docstatus = 1
			AND tsd.is_billable = 1
			AND tsd.sales_invoice is NULL
			{condition}
		ORDER BY tsd.from_time ASC
	"""

	filters = {"project": project, "parent": parent, "from_time": from_time, "to_time": to_time}

	return frappe.db.sql(query, filters, as_dict=1)


@frappe.whitelist()
def get_timesheet_detail_rate(timelog, currency):
	timelog_detail = frappe.db.sql(
		"""SELECT tsd.billing_amount as billing_amount,
		ts.currency as currency FROM `tabTimesheet Detail` tsd
		INNER JOIN `tabTimesheet` ts ON ts.name=tsd.parent
		WHERE tsd.name = '{0}'""".format(
			timelog
		),
		as_dict=1,
	)[0]

	if timelog_detail.currency:
		exchange_rate = get_exchange_rate(timelog_detail.currency, currency)

		return timelog_detail.billing_amount * exchange_rate
	return timelog_detail.billing_amount


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_timesheet(doctype, txt, searchfield, start, page_len, filters):
	if not filters:
		filters = {}

	condition = ""
	if filters.get("project"):
		condition = "and tsd.project = %(project)s"

	return frappe.db.sql(
		"""select distinct tsd.parent from `tabTimesheet Detail` tsd,
			`tabTimesheet` ts where
			ts.status in ('Submitted', 'Payslip') and tsd.parent = ts.name and
			tsd.docstatus = 1 and ts.total_billable_amount > 0
			and tsd.parent LIKE %(txt)s {condition}
			order by tsd.parent limit %(start)s, %(page_len)s""".format(
			condition=condition
		),
		{
			"txt": "%" + txt + "%",
			"start": start,
			"page_len": page_len,
			"project": filters.get("project"),
		},
	)


@frappe.whitelist()
def get_timesheet_data(name, project):
	data = None
	if project and project != "":
		data = get_projectwise_timesheet_data(project, name)
	else:
		data = frappe.get_all(
			"Timesheet",
			fields=[
				"(total_billable_amount - total_billed_amount) as billing_amt",
				"total_billable_hours as billing_hours",
			],
			filters={"name": name},
		)
	return {
		"billing_hours": data[0].billing_hours if data else None,
		"billing_amount": data[0].billing_amt if data else None,
		"timesheet_detail": data[0].name if data and project and project != "" else None,
	}


@frappe.whitelist()
def make_sales_invoice(source_name, item_code=None, customer=None, currency=None):
	target = frappe.new_doc("Sales Invoice")
	timesheet = frappe.get_doc("Timesheet", source_name)

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

	if currency:
		target.currency = currency

	if item_code:
		target.append("items", {"item_code": item_code, "qty": hours, "rate": billing_rate})

	for time_log in timesheet.time_logs:
		if time_log.is_billable:
			target.append(
				"timesheets",
				{
					"time_sheet": timesheet.name,
					"billing_hours": time_log.billing_hours,
					"billing_amount": time_log.billing_amount,
					"timesheet_detail": time_log.name,
					"activity_type": time_log.activity_type,
					"description": time_log.description,
				},
			)

	target.run_method("calculate_billing_amount_for_timesheet")
	target.run_method("set_missing_values")

	return target


@frappe.whitelist()
def make_salary_slip(source_name, target_doc=None):
	target = frappe.new_doc("Salary Slip")
	set_missing_values(source_name, target)
	target.run_method("get_emp_and_working_day_details")

	return target


def set_missing_values(time_sheet, target):
	doc = frappe.get_doc("Timesheet", time_sheet)
	target.employee = doc.employee
	target.employee_name = doc.employee_name
	target.salary_slip_based_on_timesheet = 1
	target.start_date = doc.start_date
	target.end_date = doc.end_date
	target.posting_date = doc.modified
	target.total_working_hours = doc.total_hours
	target.append("timesheets", {"time_sheet": doc.name, "working_hours": doc.total_hours})


@frappe.whitelist()
def get_activity_cost(employee=None, activity_type=None, currency=None):
	base_currency = frappe.defaults.get_global_default("currency")
	rate = frappe.db.get_values(
		"Activity Cost",
		{"employee": employee, "activity_type": activity_type},
		["costing_rate", "billing_rate"],
		as_dict=True,
	)
	if not rate:
		rate = frappe.db.get_values(
			"Activity Type",
			{"activity_type": activity_type},
			["costing_rate", "billing_rate"],
			as_dict=True,
		)
		if rate and currency and currency != base_currency:
			exchange_rate = get_exchange_rate(base_currency, currency)
			rate[0]["costing_rate"] = rate[0]["costing_rate"] * exchange_rate
			rate[0]["billing_rate"] = rate[0]["billing_rate"] * exchange_rate

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

	return frappe.db.sql(
		"""select `tabTimesheet Detail`.name as name,
			`tabTimesheet Detail`.docstatus as status, `tabTimesheet Detail`.parent as parent,
			from_time as start_date, hours, activity_type,
			`tabTimesheet Detail`.project, to_time as end_date,
			CONCAT(`tabTimesheet Detail`.parent, ' (', ROUND(hours,2),' hrs)') as title
		from `tabTimesheet Detail`, `tabTimesheet`
		where `tabTimesheet Detail`.parent = `tabTimesheet`.name
			and `tabTimesheet`.docstatus < 2
			and (from_time <= %(end)s and to_time >= %(start)s) {conditions} {match_cond}
		""".format(
			conditions=conditions, match_cond=get_match_cond("Timesheet")
		),
		{"start": start, "end": end},
		as_dict=True,
		update={"allDay": 0},
	)


def get_timesheets_list(
	doctype, txt, filters, limit_start, limit_page_length=20, order_by="modified"
):
	user = frappe.session.user
	# find customer name from contact.
	customer = ""
	timesheets = []

	contact = frappe.db.exists("Contact", {"user": user})
	if contact:
		# find customer
		contact = frappe.get_doc("Contact", contact)
		customer = contact.get_link_for("Customer")

	if customer:
		sales_invoices = [
			d.name for d in frappe.get_all("Sales Invoice", filters={"customer": customer})
		] or [None]
		projects = [d.name for d in frappe.get_all("Project", filters={"customer": customer})]
		# Return timesheet related data to web portal.
		timesheets = frappe.db.sql(
			"""
			SELECT
				ts.name, tsd.activity_type, ts.status, ts.total_billable_hours,
				COALESCE(ts.sales_invoice, tsd.sales_invoice) AS sales_invoice, tsd.project
			FROM `tabTimesheet` ts, `tabTimesheet Detail` tsd
			WHERE tsd.parent = ts.name AND
				(
					ts.sales_invoice IN %(sales_invoices)s OR
					tsd.sales_invoice IN %(sales_invoices)s OR
					tsd.project IN %(projects)s
				)
			ORDER BY `end_date` ASC
			LIMIT {0}, {1}
		""".format(
				limit_start, limit_page_length
			),
			dict(sales_invoices=sales_invoices, projects=projects),
			as_dict=True,
		)  # nosec

	return timesheets


def get_list_context(context=None):
	return {
		"show_sidebar": True,
		"show_search": True,
		"no_breadcrumbs": True,
		"title": _("Timesheets"),
		"get_list": get_timesheets_list,
		"row_template": "templates/includes/timesheet/timesheet_row.html",
	}
