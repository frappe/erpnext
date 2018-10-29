# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import flt, getdate, get_url, now
from frappe import _

from frappe.model.document import Document
from erpnext.controllers.queries import get_filters_cond
from frappe.desk.reportview import get_match_cond
import datetime

from six import iteritems

class Project(Document):
	def get_feed(self):
		return '{0}: {1}'.format(_(self.status), self.project_name)

	def onload(self):
		"""Load project tasks for quick view"""
		if not self.get('__unsaved') and not self.get("tasks"):
			self.load_tasks()

		self.set_onload('activity_summary', frappe.db.sql('''select activity_type,
			sum(hours) as total_hours
			from `tabTimesheet Detail` where project=%s and docstatus < 2 group by activity_type
			order by total_hours desc''', self.name, as_dict=True))

		self.update_costing()

	def __setup__(self):
		self.onload()

	def load_tasks(self):
		"""Load `tasks` from the database"""
		self.tasks = []
		for task in self.get_tasks():
			task_map = {
				"title": task.subject,
				"status": task.status,
				"start_date": task.exp_start_date,
				"end_date": task.exp_end_date,
				"description": task.description,
				"task_description": task.task_description,
				"task_id": task.name,
				"task_weight": task.task_weight
			}

			self.map_custom_fields(task, task_map)

			self.append("tasks", task_map)

	def get_tasks(self):
		if self.name is None:
			return {}
		else:
			filters = {"project": self.name}

			if self.get("deleted_task_list"):
				filters.update({
					'name': ("not in", self.deleted_task_list)
				})

			return frappe.get_all("Task", "*", filters, order_by="exp_start_date asc")

	def validate(self):
		self.validate_project_name()
		self.validate_dates()
		self.validate_weights()
		self.sync_tasks()
		self.tasks = []
		self.load_tasks()
		self.send_welcome_email()
		self.update_percent_complete()

	def validate_project_name(self):
		if self.get("__islocal") and frappe.db.exists("Project", self.project_name):
			frappe.throw(_("Project {0} already exists").format(self.project_name))

	def validate_dates(self):
		if self.expected_start_date and self.expected_end_date:
			if getdate(self.expected_end_date) < getdate(self.expected_start_date):
				frappe.throw(_("Expected End Date can not be less than Expected Start Date"))

	def validate_weights(self):
		for task in self.tasks:
			if task.task_weight is not None:
				if task.task_weight < 0:
					frappe.throw(_("Task weight cannot be negative"))

	def sync_tasks(self):
		"""sync tasks and remove table"""
		if not hasattr(self, "deleted_task_list"):
			self.set("deleted_task_list", [])

		if self.flags.dont_sync_tasks: return
		task_names = []

		existing_task_data = {}

		fields = ["title", "status", "start_date", "end_date", "task_description", "description", "task_weight", "task_id"]
		exclude_fieldtype = ["Button", "Column Break",
			"Section Break", "Table", "Read Only", "Attach", "Attach Image", "Color", "Geolocation", "HTML", "Image"]

		custom_fields = frappe.get_all("Custom Field", {"dt": "Project Task",
			"fieldtype": ("not in", exclude_fieldtype)}, "fieldname")

		for d in custom_fields:
			fields.append(d.fieldname)

		for d in frappe.get_all('Project Task',
			fields = fields,
			filters = {'parent': self.name}):
			existing_task_data.setdefault(d.task_id, d)

		for t in self.tasks:
			if t.task_id:
				task = frappe.get_doc("Task", t.task_id)
			else:
				task = frappe.new_doc("Task")
				task.project = self.name

			if not t.task_id or self.is_row_updated(t, existing_task_data, fields):
				task.update({
					"subject": t.title,
					"status": t.status,
					"exp_start_date": t.start_date,
					"exp_end_date": t.end_date,
					"description": t.description,
					"task_description": t.task_description,
					"task_weight": t.task_weight
				})

				self.map_custom_fields(t, task)

				task.flags.ignore_links = True
				task.flags.from_project = True
				task.flags.ignore_feed = True

				if t.task_id:
					task.update({
						"modified_by": frappe.session.user,
						"modified": now()
					})

					task.run_method("validate")
					task.db_update()
				else:
					task.save(ignore_permissions = True)
				task_names.append(task.name)
			else:
				task_names.append(task.name)

		# delete
		for t in frappe.get_all("Task", ["name"], {"project": self.name, "name": ("not in", task_names)}):
			self.deleted_task_list.append(t.name)

	def update_costing_and_percentage_complete(self):
		self.update_percent_complete()
		self.update_costing()

	def is_row_updated(self, row, existing_task_data, fields):
		if self.get("__islocal") or not existing_task_data: return True

		d = existing_task_data.get(row.task_id)

		for field in fields:
			if row.get(field) != d.get(field):
				return True

	def map_custom_fields(self, source, target):
		project_task_custom_fields = frappe.get_all("Custom Field", {"dt": "Project Task"}, "fieldname")

		for field in project_task_custom_fields:
			target.update({
				field.fieldname: source.get(field.fieldname)
			})

	def update_project(self):
		self.update_percent_complete()
		self.update_costing()
		self.flags.dont_sync_tasks = True
		self.save(ignore_permissions=True)

	def after_insert(self):
		if self.sales_order:
			frappe.db.set_value("Sales Order", self.sales_order, "project", self.name)

	def update_percent_complete(self):
		if not self.tasks: return
		total = frappe.db.sql("""select count(name) from tabTask where project=%s""", self.name)[0][0]
		if not total and self.percent_complete:
			self.percent_complete = 0
		if (self.percent_complete_method == "Task Completion" and total > 0) or (
			not self.percent_complete_method and total > 0):
			completed = frappe.db.sql("""select count(name) from tabTask where
				project=%s and status in ('Closed', 'Cancelled')""", self.name)[0][0]
			self.percent_complete = flt(flt(completed) / total * 100, 2)

		if (self.percent_complete_method == "Task Progress" and total > 0):
			progress = frappe.db.sql("""select sum(progress) from tabTask where
				project=%s""", self.name)[0][0]
			self.percent_complete = flt(flt(progress) / total, 2)

		if (self.percent_complete_method == "Task Weight" and total > 0):
			weight_sum = frappe.db.sql("""select sum(task_weight) from tabTask where
				project=%s""", self.name)[0][0]
			weighted_progress = frappe.db.sql("""select progress,task_weight from tabTask where
				project=%s""", self.name, as_dict=1)
			pct_complete = 0
			for row in weighted_progress:
				pct_complete += row["progress"] * frappe.utils.safe_div(row["task_weight"], weight_sum)
			self.percent_complete = flt(flt(pct_complete), 2)
		if self.percent_complete == 100:
			self.status = "Completed"
		elif not self.status == "Cancelled":
			self.status = "Open"

	def update_costing(self):
		from_time_sheet = frappe.db.sql("""select
			sum(costing_amount) as costing_amount,
			sum(billing_amount) as billing_amount,
			min(from_time) as start_date,
			max(to_time) as end_date,
			sum(hours) as time
			from `tabTimesheet Detail` where project = %s and docstatus = 1""", self.name, as_dict=1)[0]

		from_expense_claim = frappe.db.sql("""select
			sum(total_sanctioned_amount) as total_sanctioned_amount
			from `tabExpense Claim` where project = %s
			and docstatus = 1""", self.name, as_dict=1)[0]

		self.actual_start_date = from_time_sheet.start_date
		self.actual_end_date = from_time_sheet.end_date

		self.total_costing_amount = from_time_sheet.costing_amount
		self.total_billable_amount = from_time_sheet.billing_amount
		self.actual_time = from_time_sheet.time

		self.total_expense_claim = from_expense_claim.total_sanctioned_amount
		self.update_purchase_costing()
		self.update_sales_amount()
		self.update_billed_amount()
		self.calculate_gross_margin()

	def calculate_gross_margin(self):
		expense_amount = (flt(self.total_costing_amount) + flt(self.total_expense_claim)
			+ flt(self.total_purchase_cost) + flt(self.get('total_consumed_material_cost', 0)))

		self.gross_margin = flt(self.total_billed_amount) - expense_amount
		if self.total_billed_amount:
			self.per_gross_margin = (self.gross_margin / flt(self.total_billed_amount)) * 100

	def update_purchase_costing(self):
		total_purchase_cost = frappe.db.sql("""select sum(base_net_amount)
			from `tabPurchase Invoice Item` where project = %s and docstatus=1""", self.name)

		self.total_purchase_cost = total_purchase_cost and total_purchase_cost[0][0] or 0

	def update_sales_amount(self):
		total_sales_amount = frappe.db.sql("""select sum(base_grand_total)
			from `tabSales Order` where project = %s and docstatus=1""", self.name)

		self.total_sales_amount = total_sales_amount and total_sales_amount[0][0] or 0

	def update_billed_amount(self):
		total_billed_amount = frappe.db.sql("""select sum(base_grand_total)
			from `tabSales Invoice` where project = %s and docstatus=1""", self.name)

		self.total_billed_amount = total_billed_amount and total_billed_amount[0][0] or 0

	def after_rename(self, old_name, new_name, merge=False):
		if old_name == self.copied_from:
			frappe.db.set_value('Project', new_name, 'copied_from', new_name)

	def send_welcome_email(self):
		url = get_url("/project/?name={0}".format(self.name))
		messages = (
			_("You have been invited to collaborate on the project: {0}".format(self.name)),
			url,
			_("Join")
		)

		content = """
		<p>{0}.</p>
		<p><a href="{1}">{2}</a></p>
		"""

		for user in self.users:
			if user.welcome_email_sent == 0:
				frappe.sendmail(user.user, subject=_("Project Collaboration Invitation"),
								content=content.format(*messages))
				user.welcome_email_sent = 1

	def on_update(self):
		self.delete_task()
		self.load_tasks()
		self.update_costing_and_percentage_complete()
		self.update_dependencies_on_duplicated_project()

	def delete_task(self):
		if not self.get('deleted_task_list'): return

		for d in self.get('deleted_task_list'):
			frappe.delete_doc("Task", d)

		self.deleted_task_list = []

	def update_dependencies_on_duplicated_project(self):
		if self.flags.dont_sync_tasks: return
		if not self.copied_from:
			self.copied_from = self.name

		if self.name != self.copied_from and self.get('__unsaved'):
			# duplicated project
			dependency_map = {}
			for task in self.tasks:
				_task = frappe.db.get_value(
					'Task',
					{"subject": task.title, "project": self.copied_from},
					['name', 'depends_on_tasks'],
					as_dict=True
				)

				if _task is None:
					continue

				name = _task.name

				dependency_map[task.title] = [x['subject'] for x in frappe.get_list(
					'Task Depends On', {"parent": name}, ['subject'])]

			for key, value in iteritems(dependency_map):
				task_name = frappe.db.get_value('Task', {"subject": key, "project": self.name })

				task_doc = frappe.get_doc('Task', task_name)

				for dt in value:
					dt_name = frappe.db.get_value('Task', {"subject": dt, "project": self.name})
					task_doc.append('depends_on', {"task": dt_name})

				task_doc.db_update()


def get_timeline_data(doctype, name):
	'''Return timeline for attendance'''
	return dict(frappe.db.sql('''select unix_timestamp(from_time), count(*)
		from `tabTimesheet Detail` where project=%s
			and from_time > date_sub(curdate(), interval 1 year)
			and docstatus < 2
			group by date(from_time)''', name))


def get_project_list(doctype, txt, filters, limit_start, limit_page_length=20, order_by="modified"):
	return frappe.db.sql('''select distinct project.*
		from tabProject project, `tabProject User` project_user
		where
			(project_user.user = %(user)s
			and project_user.parent = project.name)
			or project.owner = %(user)s
			order by project.modified desc
			limit {0}, {1}
		'''.format(limit_start, limit_page_length),
						 {'user': frappe.session.user},
						 as_dict=True,
						 update={'doctype': 'Project'})


def get_list_context(context=None):
	return {
		"show_sidebar": True,
		"show_search": True,
		'no_breadcrumbs': True,
		"title": _("Projects"),
		"get_list": get_project_list,
		"row_template": "templates/includes/projects/project_row.html"
	}

def get_users_for_project(doctype, txt, searchfield, start, page_len, filters):
	conditions = []
	return frappe.db.sql("""select name, concat_ws(' ', first_name, middle_name, last_name)
		from `tabUser`
		where enabled=1
			and name not in ("Guest", "Administrator")
			and ({key} like %(txt)s
				or full_name like %(txt)s)
			{fcond} {mcond}
		order by
			if(locate(%(_txt)s, name), locate(%(_txt)s, name), 99999),
			if(locate(%(_txt)s, full_name), locate(%(_txt)s, full_name), 99999),
			idx desc,
			name, full_name
		limit %(start)s, %(page_len)s""".format(**{
		'key': searchfield,
		'fcond': get_filters_cond(doctype, filters, conditions),
		'mcond': get_match_cond(doctype)
	}), {
							 'txt': "%%%s%%" % txt,
							 '_txt': txt.replace("%", ""),
							 'start': start,
							 'page_len': page_len
						 })


@frappe.whitelist()
def get_cost_center_name(project):
	return frappe.db.get_value("Project", project, "cost_center")

@frappe.whitelist()
def hourly_reminder():
	project = frappe.db.sql("""SELECT `tabProject`.name FROM `tabProject` WHERE `tabProject`.frequency = "Hourly" and (CURTIME() BETWEEN `tabProject`.from and `tabProject`.to) AND `tabProject`.collect_progress = 1 ORDER BY `tabProject`.name;""")
	create_project_update(project)

@frappe.whitelist()
def twice_daily_reminder():
	project = frappe.db.sql("""SELECT `tabProject User`.user FROM `tabProject User` INNER JOIN `tabProject` ON `tabProject`.project_name = `tabProject User`.parent WHERE (`tabProject`.frequency = "Twice Daily") AND ((`tabProject`.first_email BETWEEN DATE_ADD(curtime(), INTERVAL -15 MINUTE) AND DATE_ADD(curtime(), INTERVAL 15 MINUTE)) OR (`tabProject`.second_email BETWEEN DATE_ADD(curtime(), INTERVAL -15 MINUTE) AND DATE_ADD(curtime(), INTERVAL 15 MINUTE))) AND `tabProject`.collect_progress = 1;""")
	create_project_update(project)

@frappe.whitelist()
def daily_reminder():
	project = frappe.db.sql("""SELECT `tabProject User`.user FROM `tabProject User` INNER JOIN `tabProject` ON `tabProject`.project_name = `tabProject User`.parent WHERE (`tabProject`.frequency = "Daily") AND (`tabProject`.daily_time_to_send BETWEEN DATE_ADD(curtime(), INTERVAL -15 MINUTE) AND DATE_ADD(curtime(), INTERVAL 15 MINUTE)) AND `tabProject`.collect_progress = 1;""")
	create_project_update(project)

@frappe.whitelist()
def weekly():
	today = datetime.datetime.now().strftime("%A")
	project = frappe.db.sql("""SELECT `tabProject User`.user FROM `tabProject User` INNER JOIN `tabProject` ON `tabProject`.project_name = `tabProject User`.parent WHERE (`tabProject`.frequency = "Weekly") AND (`tabProject`.day_to_send = %s) AND (`tabProject`.weekly_time_to_send BETWEEN DATE_ADD(curtime(), INTERVAL -15 MINUTE) AND DATE_ADD(curtime(), INTERVAL 15 MINUTE)) AND `tabProject`.collect_progress = 1""", today)
	create_project_update(project)

@frappe.whitelist()
def times_check(from1, to, first_email, second_email, daily_time_to_send, weekly_time_to_send):
    from1 = datetime.datetime.strptime(from1, "%H:%M:%S.%f")
    from1 = from1.strftime("%H:00:00")
    to = datetime.datetime.strptime(to, "%H:%M:%S.%f")
    to = to.strftime("%H:00:00")
    first_email = datetime.datetime.strptime(first_email, "%H:%M:%S.%f")
    first_email = first_email.strftime("%H:00:00")
    second_email = datetime.datetime.strptime(second_email, "%H:%M:%S.%f")
    second_email = second_email.strftime("%H:00:00")
    daily_time_to_send = datetime.datetime.strptime(daily_time_to_send, "%H:%M:%S.%f")
    daily_time_to_send = daily_time_to_send.strftime("%H:00:00")
    weekly_time_to_send = datetime.datetime.strptime(weekly_time_to_send, "%H:%M:%S.%f")
    weekly_time_to_send = weekly_time_to_send.strftime("%H:00:00")
    return {"from1": from1, "to": to, "first_email": first_email, "second_email": second_email,"daily_time_to_send": daily_time_to_send, "weekly_time_to_send": weekly_time_to_send}


#Call this function in order to generate the Project Update for a specific project
def create_project_update(project):
	data = []
	date_today = datetime.date.today()
	time_now = frappe.utils.now_datetime().strftime('%H:%M:%S')
	for projects in project:
		project_update_dict = {
			"doctype" : "Project Update",
			"project" : projects[0],
			"date": date_today,
			"time": time_now,
			"naming_series": "UPDATE-.project.-.YY.MM.DD.-"
		}
		project_update = frappe.get_doc(project_update_dict)
		project_update.insert()
		#you can edit your local_host
		local_host = "http://localhost:8003"
		project_update_url = "<a class = 'btn btn-primary' href=%s target='_blank'>" % (local_host +"/desk#Form/Project%20Update/" + (project_update.name)) + ("CREATE PROJECT UPDATE" + "</a>")
		data.append(project_update_url)

		email = frappe.db.sql("""SELECT user from `tabProject User` WHERE parent = %s;""", project[0])
		for emails in email:
			frappe.sendmail(
				recipients=emails,
				subject=frappe._(projects[0]),
				header=[frappe._("Please Update your Project Status"), 'blue'],
				message= project_update_url
			)
	return data

def update_project_sales_billing():
	sales_update_frequency = frappe.db.get_single_value("Selling Settings", "sales_update_frequency")
	if sales_update_frequency == "Each Transaction":
		return
	elif (sales_update_frequency == "Monthly" and frappe.utils.now_datetime().day != 1):
		return

	#Else simply fallback to Daily
	exists_query = '(SELECT 1 from `tab{doctype}` where docstatus = 1 and project = `tabProject`.name)'
	project_map = {}
	for project_details in frappe.db.sql('''
			SELECT name, 1 as order_exists, null as invoice_exists from `tabProject` where
			exists {order_exists}
			union
			SELECT name, null as order_exists, 1 as invoice_exists from `tabProject` where
			exists {invoice_exists}
		'''.format(
			order_exists=exists_query.format(doctype="Sales Order"),
			invoice_exists=exists_query.format(doctype="Sales Invoice"),
		), as_dict=True):
		project = project_map.setdefault(project_details.name, frappe.get_doc('Project', project_details.name))
		if project_details.order_exists:
			project.update_sales_amount()
		if project_details.invoice_exists:
			project.update_billed_amount()

	for project in project_map.values():
		project.save()

@frappe.whitelist()
def create_kanban_board_if_not_exists(project):
	from frappe.desk.doctype.kanban_board.kanban_board import quick_kanban_board

	if not frappe.db.exists('Kanban Board', project):
		quick_kanban_board('Task', project, 'status')

	return True
