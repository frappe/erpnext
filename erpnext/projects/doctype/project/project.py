# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import flt, getdate, get_url
from frappe import _

from frappe.model.document import Document
from erpnext.controllers.queries import get_filters_cond
from frappe.desk.reportview import get_match_cond

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
				"task_id": task.name,
				"task_weight": task.task_weight
			}

			self.map_custom_fields(task, task_map)

			self.append("tasks", task_map)

	def get_tasks(self):
		return frappe.get_all("Task", "*", {"project": self.name}, order_by="exp_start_date asc")

	def validate(self):
		self.validate_dates()
		self.validate_weights()
		self.sync_tasks()
		self.tasks = []
		self.send_welcome_email()

	def validate_dates(self):
		if self.expected_start_date and self.expected_end_date:
			if getdate(self.expected_end_date) < getdate(self.expected_start_date):
				frappe.throw(_("Expected End Date can not be less than Expected Start Date"))
				
	def validate_weights(self):
		sum = 0
		for task in self.tasks:
			if task.task_weight > 0:
				sum = sum + task.task_weight
		if sum > 0 and sum != 1:
			frappe.throw(_("Total of all task weights should be 1. Please adjust weights of all Project tasks accordingly"))

	def sync_tasks(self):
		"""sync tasks and remove table"""
		if self.flags.dont_sync_tasks: return
		task_names = []
		for t in self.tasks:
			if t.task_id:
				task = frappe.get_doc("Task", t.task_id)
			else:
				task = frappe.new_doc("Task")
				task.project = self.name
			task.update({
				"subject": t.title,
				"status": t.status,
				"exp_start_date": t.start_date,
				"exp_end_date": t.end_date,
				"description": t.description,
				"task_weight": t.task_weight
			})

			self.map_custom_fields(t, task)

			task.flags.ignore_links = True
			task.flags.from_project = True
			task.flags.ignore_feed = True
			task.save(ignore_permissions = True)
			task_names.append(task.name)

		# delete
		for t in frappe.get_all("Task", ["name"], {"project": self.name, "name": ("not in", task_names)}):
			frappe.delete_doc("Task", t.name)

		self.update_percent_complete()
		self.update_costing()

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
		self.save(ignore_permissions = True)

	def update_percent_complete(self):
		total = frappe.db.sql("""select count(name) from tabTask where project=%s""", self.name)[0][0]
		if not total and self.percent_complete:
			self.percent_complete = 0
		if (self.percent_complete_method == "Task Completion" and total > 0) or (not self.percent_complete_method and total > 0):
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
			if weight_sum == 1:
				weighted_progress = frappe.db.sql("""select progress,task_weight from tabTask where
					project=%s""", self.name,as_dict=1)
				pct_complete=0
				for row in weighted_progress:
					pct_complete += row["progress"] * row["task_weight"]
				self.percent_complete = flt(flt(pct_complete), 2)

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
			from `tabExpense Claim` where project = %s and approval_status='Approved'
			and docstatus = 1""",
			self.name, as_dict=1)[0]

		self.actual_start_date = from_time_sheet.start_date
		self.actual_end_date = from_time_sheet.end_date

		self.total_costing_amount = from_time_sheet.costing_amount
		self.total_billing_amount = from_time_sheet.billing_amount
		self.actual_time = from_time_sheet.time

		self.total_expense_claim = from_expense_claim.total_sanctioned_amount

		self.gross_margin = flt(self.total_billing_amount) - flt(self.total_costing_amount)

		if self.total_billing_amount:
			self.per_gross_margin = (self.gross_margin / flt(self.total_billing_amount)) *100

	def update_purchase_costing(self):
		total_purchase_cost = frappe.db.sql("""select sum(base_net_amount)
			from `tabPurchase Invoice Item` where project = %s and docstatus=1""", self.name)

		self.total_purchase_cost = total_purchase_cost and total_purchase_cost[0][0] or 0
		
	def update_sales_costing(self):
		total_sales_cost = frappe.db.sql("""select sum(grand_total)
			from `tabSales Order` where project = %s and docstatus=1""", self.name)

		self.total_sales_cost = total_sales_cost and total_sales_cost[0][0] or 0
				

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
			if user.welcome_email_sent==0:
				frappe.sendmail(user.user, subject=_("Project Collaboration Invitation"), content=content.format(*messages))
				user.welcome_email_sent=1

	def on_update(self):
		self.load_tasks()
		self.sync_tasks()
		self.update_dependencies_on_duplicated_project()
	
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
				depends_on_tasks = _task.depends_on_tasks

				depends_on_tasks = [x for x in depends_on_tasks.split(',') if x]
				dependency_map[task.title] = [ x['subject'] for x in frappe.get_list(
					'Task Depends On', {"parent": name}, ['subject'])]

			for key, value in dependency_map.iteritems():
				task_name = frappe.db.get_value('Task', {"subject": key, "project": self.name })
				task_doc = frappe.get_doc('Task', task_name)

				for dt in value:
					dt_name = frappe.db.get_value('Task', {"subject": dt, "project": self.name })
					task_doc.append('depends_on', {"task": dt_name})
				task_doc.save()

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
			{'user':frappe.session.user},
			as_dict=True,
			update={'doctype':'Project'})

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
