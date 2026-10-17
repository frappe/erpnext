# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from collections import Counter
from graphlib import TopologicalSorter

import frappe
from email_reply_parser import EmailReplyParser
from frappe import _, qb
from frappe.desk.reportview import get_match_cond
from frappe.model.document import Document
from frappe.query_builder import Interval
from frappe.query_builder.functions import Count, CurDate, Date, Sum, UnixTimestamp
from frappe.utils import add_days, flt, get_datetime, get_link_to_form, get_time, get_url, nowtime, today
from frappe.utils.html_utils import sanitize_html
from frappe.utils.user import is_website_user

from erpnext import get_default_company
from erpnext.controllers.queries import get_filters_cond
from erpnext.controllers.website_list_for_contact import get_customers_suppliers
from erpnext.setup.doctype.holiday_list.holiday_list import is_holiday

PORTAL_LIST_FIELDS = ["name", "project_name", "status", "percent_complete", "_assign", "modified"]


class Project(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.projects.doctype.project_user.project_user import ProjectUser

		actual_end_date: DF.Date | None
		actual_start_date: DF.Date | None
		actual_time: DF.Float
		collect_progress: DF.Check
		company: DF.Link
		copied_from: DF.Data | None
		cost_center: DF.Link | None
		customer: DF.Link | None
		daily_time_to_send: DF.Time | None
		day_to_send: DF.Literal["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
		department: DF.Link | None
		estimated_costing: DF.Currency
		expected_end_date: DF.Date | None
		expected_start_date: DF.Date | None
		first_email: DF.Time | None
		frequency: DF.Literal["Hourly", "Twice Daily", "Daily", "Weekly"]
		from_time: DF.Time | None
		gross_margin: DF.Currency
		holiday_list: DF.Link | None
		is_active: DF.Literal["Yes", "No"]
		message: DF.Text | None
		naming_series: DF.Literal["PROJ-.####"]
		notes: DF.TextEditor | None
		per_gross_margin: DF.Percent
		percent_complete: DF.Percent
		percent_complete_method: DF.Literal["Manual", "Task Completion", "Task Progress", "Task Weight"]
		priority: DF.Literal["Medium", "Low", "High"]
		project_name: DF.Data
		project_template: DF.Link | None
		project_type: DF.Link | None
		sales_order: DF.Link | None
		second_email: DF.Time | None
		status: DF.Literal["Open", "On hold", "Completed", "Cancelled"]
		subject: DF.Data | None
		to_time: DF.Time | None
		total_billable_amount: DF.Currency
		total_billed_amount: DF.Currency
		total_consumed_material_cost: DF.Currency
		total_costing_amount: DF.Currency
		total_purchase_cost: DF.Currency
		total_sales_amount: DF.Currency
		users: DF.Table[ProjectUser]
		weekly_time_to_send: DF.Time | None
	# end: auto-generated types

	def onload(self):
		self.set_onload(
			"activity_summary",
			frappe.db.sql(
				"""select activity_type,
			sum(hours) as total_hours
			from `tabTimesheet Detail` where project=%s and docstatus < 2 group by activity_type
			order by total_hours desc""",
				self.name,
				as_dict=True,
			),
		)

	def before_print(self, settings=None):
		self.onload()

	def validate(self):
		self.validate_project_template()
		if not self.is_new():
			self.control_access_for_project_users()
		self.send_welcome_email()
		self.update_costing()
		self.update_percent_complete()
		self.validate_from_to_dates("expected_start_date", "expected_end_date")
		self.validate_from_to_dates("actual_start_date", "actual_end_date")

	def validate_project_template(self):
		if (
			self.project_template
			and self.has_value_changed("project_template")
			and frappe.db.get_value("Project Template", self.project_template, "disabled")
		):
			frappe.throw(_("Project Template {0} is disabled").format(frappe.bold(self.project_template)))

	def copy_from_template(self):  # nosemgrep
		"""
		Copy tasks from template
		"""
		if self.project_template and not frappe.db.get_all("Task", dict(project=self.name), limit=1):
			# has a template, and no loaded tasks, so lets create
			if not self.expected_start_date:
				# project starts today
				self.expected_start_date = today()

			template = frappe.get_doc("Project Template", self.project_template)

			if not self.project_type:
				self.project_type = template.project_type

			# create tasks from template
			project_tasks = []
			tmp_task_details = []
			for task in template.tasks:
				template_task_details = frappe.get_doc("Task", task.task)
				tmp_task_details.append(template_task_details)
				task = self.create_task_from_template(template_task_details)
				project_tasks.append(task)

			self.dependency_mapping(tmp_task_details, project_tasks)

	def create_task_from_template(self, task_details):
		return frappe.get_doc(
			doctype="Task",
			subject=task_details.subject,
			project=self.name,
			status="Open",
			exp_start_date=self.calculate_start_date(task_details),
			exp_end_date=self.calculate_end_date(task_details),
			description=task_details.description,
			task_weight=task_details.task_weight,
			type=task_details.type,
			issue=task_details.issue,
			is_group=task_details.is_group,
			color=task_details.color,
			template_task=task_details.name,
			priority=task_details.priority,
		).insert()

	def calculate_start_date(self, task_details):
		self.start_date = add_days(self.expected_start_date, task_details.start)
		self.start_date = self.update_if_holiday(self.start_date)
		return self.start_date

	def calculate_end_date(self, task_details):
		self.end_date = add_days(self.start_date, task_details.duration)
		return self.update_if_holiday(self.end_date)

	def update_if_holiday(self, date):
		holiday_list = self.holiday_list or frappe.get_cached_value(
			"Company", self.company, "default_holiday_list"
		)
		while is_holiday(holiday_list, date):
			date = add_days(date, 1)
		return date

	def dependency_mapping(self, template_tasks, project_tasks):
		for project_task in project_tasks:
			template_task = frappe.get_doc("Task", project_task.template_task)

			self.check_depends_on_value(template_task, project_task, project_tasks)
			self.check_for_parent_tasks(template_task, project_task, project_tasks)

	def check_depends_on_value(self, template_task, project_task, project_tasks):
		if template_task.get("depends_on") and not project_task.get("depends_on"):
			project_template_map = {pt.template_task: pt for pt in project_tasks}

			for child_task in template_task.get("depends_on"):
				if project_template_map and project_template_map.get(child_task.task):
					project_task.reload()  # reload, as it might have been updated in the previous iteration
					project_task.append(
						"depends_on", {"task": project_template_map.get(child_task.task).name}
					)
					project_task.save()

	def check_for_parent_tasks(self, template_task, project_task, project_tasks):
		if template_task.get("parent_task") and not project_task.get("parent_task"):
			for pt in project_tasks:
				if pt.template_task == template_task.parent_task:
					project_task.parent_task = pt.name
					project_task.save()
					break

	def is_row_updated(self, row, existing_task_data, fields):
		if self.get("__islocal") or not existing_task_data:
			return True

		d = existing_task_data.get(row.task_id, {})

		for field in fields:
			if row.get(field) != d.get(field):
				return True

	def update_project(self):
		"""Called externally by Task"""
		self.update_percent_complete()
		self.update_costing()
		self.db_update()

	def after_insert(self):
		self.copy_from_template()  # nosemgrep
		if self.sales_order:
			frappe.db.set_value("Sales Order", self.sales_order, "project", self.name)
			self.update_sales_amount()
			self.db_set("total_sales_amount", self.total_sales_amount)
		self.control_access_for_project_users()

	def on_trash(self):
		frappe.db.set_value("Sales Order", {"project": self.name}, "project", "")

	def update_percent_complete(self):
		if self.status == "Completed":
			if (
				len(frappe.get_all("Task", dict(project=self.name))) == 0
			):  # A project without tasks should be able to complete
				self.percent_complete_method = "Manual"
				self.percent_complete = 100

		if self.percent_complete_method == "Manual":
			if self.status == "Completed":
				self.percent_complete = 100
			elif flt(self.percent_complete) < 0 or flt(self.percent_complete) > 100:
				frappe.throw(_("% Complete must be between 0 and 100"))
			return

		total = frappe.db.count("Task", dict(project=self.name))

		if not total:
			self.percent_complete = 0
		else:
			if (self.percent_complete_method == "Task Completion" and total > 0) or (
				not self.percent_complete_method and total > 0
			):
				completed = frappe.db.sql(
					"""select count(name) from tabTask where
					project=%s and status in ('Cancelled', 'Completed')""",
					self.name,
				)[0][0]
				self.percent_complete = flt(flt(completed) / total * 100, 2)

			if self.percent_complete_method in ("Task Progress", "Task Weight") and total > 0:
				self.percent_complete = flt(self.get_task_progress(), 2)

		# don't update status if it is manually set to cancelled or on hold
		if self.status in ("Cancelled", "On hold"):
			return

		self.validate_completed_status()
		self.status = "Completed" if self.percent_complete == 100 else "Open"

	def validate_completed_status(self):
		"""Refuse a status set to Completed by hand while the tasks are not all done."""
		previous = self.get_doc_before_save()
		if not previous or previous.status == "Completed" or self.status != "Completed":
			return

		if flt(self.percent_complete) < 100:
			frappe.throw(
				_("Project {0} is only {1} complete. Complete or cancel its tasks first.").format(
					frappe.bold(self.name), frappe.format(self.percent_complete, {"fieldtype": "Percent"})
				),
				title=_("Cannot set Project to Completed"),
			)

	def get_task_progress(self) -> float:
		"""Average task progress, weighted for Task Weight. Completed and cancelled tasks count as done."""
		tasks = frappe.get_all(
			"Task", filters={"project": self.name}, fields=["status", "progress", "task_weight"]
		)
		weights = [flt(task.task_weight) for task in tasks]
		if self.percent_complete_method != "Task Weight" or not sum(weights):
			weights = [1] * len(tasks)

		progress = [
			100 if task.status in ("Completed", "Cancelled") else flt(task.progress) for task in tasks
		]
		return sum(p * w for p, w in zip(progress, weights, strict=True)) / sum(weights)

	def update_costing(self):
		from frappe.query_builder.functions import Max, Min, Sum

		TimesheetDetail = frappe.qb.DocType("Timesheet Detail")
		from_time_sheet = (
			frappe.qb.from_(TimesheetDetail)
			.select(
				Sum(TimesheetDetail.costing_amount).as_("costing_amount"),
				Sum(TimesheetDetail.billing_amount).as_("billing_amount"),
				Min(TimesheetDetail.from_time).as_("start_date"),
				Max(TimesheetDetail.to_time).as_("end_date"),
				Sum(TimesheetDetail.hours).as_("time"),
				Sum(TimesheetDetail.base_costing_amount).as_("base_costing_amount"),
				Sum(TimesheetDetail.base_billing_amount).as_("base_billing_amount"),
			)
			.where((TimesheetDetail.project == self.name) & (TimesheetDetail.docstatus == 1))
		).run(as_dict=True)[0]

		self.actual_start_date = from_time_sheet.start_date
		self.actual_end_date = from_time_sheet.end_date

		self.total_costing_amount = from_time_sheet.base_costing_amount
		self.total_billable_amount = from_time_sheet.base_billing_amount
		self.actual_time = from_time_sheet.time

		self.update_purchase_costing()
		self.update_sales_amount()
		self.update_billed_amount()
		self.calculate_gross_margin()

	def calculate_gross_margin(self):
		expense_amount = (
			flt(self.total_costing_amount)
			+ flt(self.total_purchase_cost)
			+ flt(self.get("total_consumed_material_cost", 0))
		)

		self.gross_margin = flt(self.total_billed_amount) - expense_amount
		if self.total_billed_amount:
			self.per_gross_margin = (self.gross_margin / flt(self.total_billed_amount)) * 100
		else:
			self.per_gross_margin = 0

	def update_purchase_costing(self):
		total_purchase_cost = calculate_total_purchase_cost(self.name)
		self.total_purchase_cost = total_purchase_cost and total_purchase_cost[0][0] or 0

	def update_sales_amount(self):
		total_sales_amount = frappe.db.sql(
			"""select sum(base_net_total)
			from `tabSales Order` where project = %s and docstatus=1""",
			self.name,
		)

		self.total_sales_amount = total_sales_amount and total_sales_amount[0][0] or 0

	def update_billed_amount(self):
		self.total_billed_amount = self.get_billed_amount_from_parent() + self.get_billed_amount_from_child()

	def get_billed_amount_from_parent(self):
		total_billed_amount = frappe.db.sql(
			"""select sum(base_net_amount)
			from `tabSales Invoice` si join `tabSales Invoice Item` si_item on si_item.parent = si.name
				where si_item.project is null
				and si.project is not null
				and si.project = %s
				and si.docstatus = 1""",
			self.name,
		)

		return total_billed_amount and total_billed_amount[0][0] or 0

	def get_billed_amount_from_child(self):
		total_billed_amount = frappe.db.sql(
			"""select sum(base_net_amount)
			from `tabSales Invoice Item`
				where project = %s
				and docstatus = 1""",
			self.name,
		)

		return total_billed_amount and total_billed_amount[0][0] or 0

	def after_rename(self, old_name, new_name, merge=False):
		if old_name == self.copied_from:
			frappe.db.set_value("Project", new_name, "copied_from", new_name)

	def send_welcome_email(self):
		label = f"{self.project_name} ({self.name})"
		url = get_link_to_form(self.doctype, self.name, label)

		content = "<p>{}</p>".format(
			_("You have been invited to collaborate on the project {0}.").format(url)
		)

		for user in self.users:
			# process only users who haven't received the welcome email yet
			if user.welcome_email_sent == 0:
				# fetch canonical User data (enabled status + latest email)
				user_info = frappe.db.get_value("User", user.user, ["enabled", "email"], as_dict=True)
				# send email only if user is enabled and has a valid email
				if user_info and user_info.enabled and user_info.email:
					frappe.sendmail(
						recipients=[user_info.email],
						subject=_("Project Collaboration Invitation"),
						content=content,
					)
					user.welcome_email_sent = 1

	def control_access_for_project_users(self):
		def revoke_access_for_project_users(removed_users):
			users = set([d.user for d in frappe.share.get_users(self.doctype, self.name)])
			for user in removed_users:
				if user not in users:
					continue

				frappe.share.remove(self.doctype, self.name, user)

		def grant_access_for_project_users(new_users):
			for user in new_users:
				frappe.share.add_docshare(self.doctype, self.name, user=user)

		current_users = set([d.user for d in self.users])
		old_doc = self.get_doc_before_save()

		if not old_doc:
			grant_access_for_project_users(current_users)
			return

		previous_users = set([d.user for d in old_doc.users])

		new_users = current_users - previous_users
		removed_users = previous_users - current_users

		revoke_access_for_project_users(removed_users)
		grant_access_for_project_users(new_users)


def get_timeline_data(doctype: str, name: str) -> dict[int, int]:
	"""Return timeline for attendance"""

	timesheet_detail = frappe.qb.DocType("Timesheet Detail")

	return dict(
		frappe.qb.from_(timesheet_detail)
		.select(UnixTimestamp(timesheet_detail.from_time), Count("*"))
		.where(timesheet_detail.project == name)
		.where(timesheet_detail.from_time > CurDate() - Interval(years=1))
		.where(timesheet_detail.docstatus < 2)
		.groupby(Date(timesheet_detail.from_time))
		.run()
	)


def get_project_list(doctype, txt, filters, limit_start, limit_page_length=20, order_by="creation"):
	customers, suppliers = get_customers_suppliers("Project", frappe.session.user)

	ignore_permissions = False
	if is_website_user() and frappe.session.user != "Guest":
		if not filters:
			filters = []

		if customers:
			filters.append([doctype, "customer", "in", customers])
			ignore_permissions = True

	meta = frappe.get_meta(doctype)

	or_filters = []

	if txt:
		if meta.search_fields:
			for f in meta.get_search_fields():
				if f == "name" or meta.get_field(f).fieldtype in (
					"Data",
					"Text",
					"Small Text",
					"Text Editor",
					"select",
				):
					or_filters.append([doctype, f, "like", "%" + txt + "%"])
		else:
			if isinstance(filters, dict):
				filters["name"] = ("like", "%" + txt + "%")
			else:
				filters.append([doctype, "name", "like", "%" + txt + "%"])

	return frappe.get_list(
		doctype,
		fields=PORTAL_LIST_FIELDS,
		filters=filters,
		or_filters=or_filters,
		limit_start=limit_start,
		limit_page_length=limit_page_length,
		order_by=order_by,
		ignore_permissions=ignore_permissions,
		distinct=True,
	)


def get_list_context(context=None):
	from erpnext.controllers.website_list_for_contact import get_list_context

	list_context = get_list_context(context)
	list_context.update(
		{
			"show_sidebar": True,
			"show_search": True,
			"no_breadcrumbs": True,
			"title": _("Projects"),
			"get_list": get_project_list,
			"row_template": "templates/includes/projects/project_row.html",
			"list_template": "templates/includes/list/list.html",
		}
	)

	return list_context


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_users_for_project(doctype, txt, searchfield, start, page_len, filters):
	conditions = []
	return frappe.db.sql(
		"""select name, concat_ws(' ', first_name, middle_name, last_name)
		from `tabUser`
		where enabled=1
			and name not in ("Guest", "Administrator")
			and ({key} like %(txt)s
				or full_name like %(txt)s)
			{fcond} {mcond}
		order by
			(case when locate(%(_txt)s, name) > 0 then locate(%(_txt)s, name) else 99999 end),
			(case when locate(%(_txt)s, full_name) > 0 then locate(%(_txt)s, full_name) else 99999 end),
			idx desc,
			name, full_name
		limit %(page_len)s offset %(start)s""".format(
			**{
				"key": searchfield,
				"fcond": get_filters_cond(doctype, filters, conditions),
				"mcond": get_match_cond(doctype),
			}
		),
		{"txt": "%%%s%%" % txt, "_txt": txt.replace("%", ""), "start": start, "page_len": page_len},
	)


@frappe.whitelist()
def get_cost_center_name(project):
	frappe.has_permission("Project", "select", project, throw=True)
	return frappe.db.get_value("Project", project, "cost_center")


def hourly_reminder():
	fields = ["from_time", "to_time"]
	projects = get_projects_for_collect_progress("Hourly", fields)

	for project in projects:
		if is_now_between(project.from_time, project.to_time):
			send_project_update_email_to_users(project.name)


def is_now_between(from_time, to_time) -> bool:
	"""Whether the current time is in the window, which may cross midnight."""
	now, from_time, to_time = get_time(nowtime()), get_time(from_time), get_time(to_time)
	if from_time <= to_time:
		return from_time <= now <= to_time
	return now >= from_time or now <= to_time


def project_status_update_reminder():
	daily_reminder()
	twice_daily_reminder()
	weekly_reminder()


def daily_reminder():
	fields = ["daily_time_to_send"]
	projects = get_projects_for_collect_progress("Daily", fields)

	for project in projects:
		if get_due_project_updates(project.name, project.daily_time_to_send):
			send_project_update_email_to_users(project.name)


def twice_daily_reminder():
	projects = get_projects_for_collect_progress("Twice Daily", ["first_email", "second_email"])

	for project in projects:
		for _due in range(get_due_project_updates(project.name, project.first_email, project.second_email)):
			send_project_update_email_to_users(project.name)


def weekly_reminder():
	fields = ["day_to_send", "weekly_time_to_send"]
	projects = get_projects_for_collect_progress("Weekly", fields)

	current_day = get_datetime().strftime("%A")
	for project in projects:
		if current_day != project.day_to_send:
			continue

		if get_due_project_updates(project.name, project.weekly_time_to_send):
			send_project_update_email_to_users(project.name)


def get_due_project_updates(project: str, *times) -> int:
	"""Send times already passed today that have no Project Update yet."""
	now = get_time(nowtime())
	times_passed = sum(now >= get_time(time) for time in times)
	return max(times_passed - frappe.db.count("Project Update", {"project": project, "date": today()}), 0)


@frappe.whitelist()
def create_duplicate_project(prev_doc, project_name):
	"""Create duplicate project based on the old project"""
	import json

	prev_doc = json.loads(prev_doc)

	source_name = prev_doc.get("name")
	if not source_name:
		frappe.throw(_("Save the Project before duplicating it"))

	# prev_doc is caller-supplied, but the tasks below are read from the db by name
	frappe.has_permission("Project", "read", source_name, throw=True)

	if project_name == source_name:
		frappe.throw(_("Use a name that is different from previous project name"))

	# change the copied doc name to new project name
	project = frappe.copy_doc(prev_doc)
	project.name = project_name
	project.project_template = ""
	project.project_name = project_name
	project.insert()

	copy_tasks(source_name, project.name)

	project.db_set("project_template", prev_doc.get("project_template"))


def copy_tasks(source_project: str, target_project: str):
	"""Copy the tasks of a project, pointing parent tasks and dependencies at the copies."""
	source_tasks = [
		frappe.get_doc("Task", name)
		for name in frappe.get_all("Task", filters={"project": source_project}, order_by="lft", pluck="name")
	]

	copied_names = {}
	for source_task in source_tasks:
		task = frappe.copy_doc(source_task)
		task.project = target_project
		task.parent_task = copied_names.get(task.parent_task)
		task.set("depends_on", [])
		copied_names[source_task.name] = task.insert().name

	for source_task in source_tasks:
		if not source_task.depends_on:
			continue

		task = frappe.get_doc("Task", copied_names[source_task.name])
		task.set(
			"depends_on", [{"task": copied_names.get(row.task, row.task)} for row in source_task.depends_on]
		)
		task.save()


def get_projects_for_collect_progress(frequency, fields):
	fields.extend(["name"])

	return frappe.get_all(
		"Project",
		fields=fields,
		filters={"collect_progress": 1, "frequency": frequency, "status": "Open"},
	)


def send_project_update_email_to_users(project):
	doc = frappe.get_doc("Project", project)

	if is_holiday(doc.holiday_list) or not doc.users:
		return

	project_update = frappe.get_doc(
		{
			"doctype": "Project Update",
			"project": project,
			"sent": 0,
			"date": today(),
			"time": nowtime(),
			"naming_series": "UPDATE-.project.-.YY.MM.DD.-.####",
		}
	).insert()

	incoming_email_account = frappe.db.get_value(
		"Email Account", dict(enable_incoming=1, default_incoming=1), "email_id"
	)

	frappe.sendmail(
		recipients=get_users_email(doc),
		message=doc.message,
		subject=doc.subject,
		reference_doctype=project_update.doctype,
		reference_name=project_update.name,
		reply_to=incoming_email_account,
	)


def collect_project_status():
	for data in frappe.get_all("Project Update", {"date": today(), "sent": 0}):
		doc = frappe.get_doc("Project Update", data.name)
		new_replies = get_uncollected_replies(doc)
		if new_replies:
			for reply in new_replies:
				doc.append("users", reply)
			doc.save(ignore_permissions=True)


def get_uncollected_replies(project_update):
	collected = Counter((row.user, row.project_status) for row in project_update.users)
	new_replies = []
	for reply in get_project_update_replies(project_update.name):
		key = (reply["user"], reply["project_status"])
		if collected[key]:
			collected[key] -= 1
		else:
			new_replies.append(reply)
	return new_replies


def get_project_update_replies(project_update):
	replies = frappe.get_all(
		"Communication",
		fields=["content", "text_content", "sender"],
		filters=dict(
			reference_doctype="Project Update",
			reference_name=project_update,
			communication_type="Communication",
			sent_or_received="Received",
		),
		order_by="creation asc",
	)

	users = []
	for d in replies:
		user_data = frappe.db.get_value(
			"User", {"email": d.sender}, ["full_name", "user_image", "name"], as_dict=True
		)
		if not user_data:
			continue

		users.append(
			{
				"user": user_data.name,
				"full_name": user_data.full_name,
				"image": user_data.user_image,
				"project_status": sanitize_html(
					frappe.utils.md_to_html(EmailReplyParser.parse_reply(d.text_content) or d.content),
					linkify=True,
				),
			}
		)
	return users


def send_project_status_email_to_users():
	yesterday = add_days(today(), -1)

	for d in frappe.get_all("Project Update", {"date": yesterday, "sent": 0}):
		doc = frappe.get_doc("Project Update", d.name)

		project_doc = frappe.get_doc("Project", doc.project)

		args = {"users": doc.users, "title": _("Project Summary for {0}").format(yesterday)}

		frappe.sendmail(
			recipients=get_users_email(project_doc),
			template="daily_project_summary",
			args=args,
			subject=_("Daily Project Summary for {0}").format(d.name),
			reference_doctype="Project Update",
			reference_name=d.name,
		)

		doc.db_set("sent", 1)


def update_project_sales_billing():
	sales_update_frequency = frappe.get_single_value("Selling Settings", "sales_update_frequency")
	if sales_update_frequency == "Each Transaction":
		return
	elif sales_update_frequency == "Monthly" and frappe.utils.now_datetime().day != 1:
		return

	# Else simply fallback to Daily
	for project in frappe.get_all("Project", filters={"status": ["!=", "Cancelled"]}):
		frappe.get_doc("Project", project.name).save()


@frappe.whitelist()
def create_kanban_board_if_not_exists(project: str) -> str:
	from frappe.desk.doctype.kanban_board.kanban_board import quick_kanban_board
	from frappe.model.naming import append_number_if_name_exists

	project = frappe.get_doc("Project", project)
	project.check_permission("read")

	if board := get_project_kanban_board(project.name):
		return board

	board_name = append_number_if_name_exists("Kanban Board", project.project_name)
	return quick_kanban_board("Task", board_name, "status", project.name).name


def get_project_kanban_board(project: str) -> str | None:
	for board in frappe.get_list(
		"Kanban Board", filters={"reference_doctype": "Task"}, fields=["name", "filters"]
	):
		filters = frappe.parse_json(board.filters or "[]")
		if any(isinstance(f, list) and f[1:4] == ["project", "=", project] for f in filters):
			return board.name


@frappe.whitelist()
def set_project_status(project, status):
	"""
	set status for project and all related tasks
	"""
	if status not in ("Completed", "Cancelled"):
		frappe.throw(_("Status must be Cancelled or Completed"))

	project = frappe.get_doc("Project", project)
	project.check_permission("write")

	for task_name in get_tasks_in_dependency_order(project.name, status):
		task = frappe.get_doc("Task", task_name)
		task.status = status
		task.flags.ignore_reschedule = True
		task.save(ignore_permissions=True)

	project.status = status
	project.save()


def get_tasks_in_dependency_order(project: str, status: str) -> list[str]:
	"""Project tasks not in `status`, each after the tasks it depends on."""
	tasks = frappe.get_all("Task", filters={"project": project, "status": ["!=", status]}, pluck="name")
	if not tasks:
		return []

	dependencies = {task: set() for task in tasks}
	for row in frappe.get_all(
		"Task Depends On", filters={"parenttype": "Task", "parent": ["in", tasks]}, fields=["parent", "task"]
	):
		dependencies[row.parent].add(row.task)

	return [task for task in TopologicalSorter(dependencies).static_order() if task in dependencies]


def get_holiday_list(company=None):
	if not company:
		company = get_default_company() or frappe.get_all("Company")[0].name

	holiday_list = frappe.get_cached_value("Company", company, "default_holiday_list")
	if not holiday_list:
		frappe.throw(
			_("Please set a default Holiday List for Company {0}").format(frappe.bold(get_default_company()))
		)
	return holiday_list


def get_users_email(doc):
	return [d.email for d in doc.users if frappe.db.get_value("User", d.user, "enabled")]


def calculate_total_purchase_cost(project: str | None = None):
	if project:
		pitem = qb.DocType("Purchase Invoice Item")
		total_purchase_cost = (
			qb.from_(pitem)
			.select(Sum(pitem.base_net_amount))
			.where((pitem.project == project) & (pitem.docstatus == 1))
			.run(as_list=True)
		)
		return total_purchase_cost
	return None


@frappe.whitelist()
def update_costing_and_billing(project: str | None = None):
	project = frappe.get_doc("Project", project)
	project.check_permission("write")
	project.update_costing()
	project.db_update()
