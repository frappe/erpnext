# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import json

import frappe
from frappe import _, throw
from frappe.utils import add_days, cstr, date_diff, get_link_to_form, getdate
from frappe.utils.nestedset import NestedSet


class CircularReferenceError(frappe.ValidationError): pass

class Task(NestedSet):
	nsm_parent_field = 'parent_task'

	def get_feed(self):
		return '{0}: {1}'.format(_(self.status), self.subject)

	def get_project_details(self):
		return {
			"project": self.project
		}

	def get_customer_details(self):
		cust = frappe.db.sql("select customer_name from `tabCustomer` where name=%s", self.customer)
		if cust:
			ret = {'customer_name': cust and cust[0][0] or ''}
			return ret

	def validate(self):
		self.validate_dates()
		self.validate_progress()
		self.validate_status()
		self.update_depends_on()

	def validate_dates(self):
		if self.exp_start_date and self.exp_end_date and getdate(self.exp_start_date) > getdate(self.exp_end_date):
			frappe.throw(_("'Expected Start Date' can not be greater than 'Expected End Date'"))

		if self.act_start_date and self.act_end_date and getdate(self.act_start_date) > getdate(self.act_end_date):
			frappe.throw(_("'Actual Start Date' can not be greater than 'Actual End Date'"))

	def validate_status(self):
		if self.status!=self.get_db_value("status") and self.status == "Closed":
			for d in self.depends_on:
				if frappe.db.get_value("Task", d.task, "status") != "Closed":
					frappe.throw(_("Cannot close task as its dependant task {0} is not closed.").format(d.task))

			from frappe.desk.form.assign_to import clear
			clear(self.doctype, self.name)

	def validate_progress(self):
		if (self.progress or 0) > 100:
			frappe.throw(_("Progress % for a task cannot be more than 100."))

	def update_depends_on(self):
		depends_on_tasks = self.depends_on_tasks or ""
		for d in self.depends_on:
			if d.task and not d.task in depends_on_tasks:
				depends_on_tasks += d.task + ","
		self.depends_on_tasks = depends_on_tasks

	def update_nsm_model(self):
		frappe.utils.nestedset.update_nsm(self)

	def on_update(self):
		self.update_nsm_model()
		self.check_recursion()
		self.reschedule_dependent_tasks()
		self.update_project()
		self.unassign_todo()
		self.populate_depends_on()

	def unassign_todo(self):
		if self.status == "Closed" or self.status == "Cancelled":
			from frappe.desk.form.assign_to import clear
			clear(self.doctype, self.name)

	def update_total_expense_claim(self):
		self.total_expense_claim = frappe.db.sql("""select sum(total_sanctioned_amount) from `tabExpense Claim`
			where project = %s and task = %s and docstatus=1""",(self.project, self.name))[0][0]

	def update_time_and_costing(self):
		tl = frappe.db.sql("""select min(from_time) as start_date, max(to_time) as end_date,
			sum(billing_amount) as total_billing_amount, sum(costing_amount) as total_costing_amount,
			sum(hours) as time from `tabTimesheet Detail` where task = %s and docstatus=1"""
			,self.name, as_dict=1)[0]
		if self.status == "Open":
			self.status = "Working"
		self.total_costing_amount= tl.total_costing_amount
		self.total_billing_amount= tl.total_billing_amount
		self.actual_time= tl.time
		self.act_start_date= tl.start_date
		self.act_end_date= tl.end_date

	def update_project(self):
		if self.project and not self.flags.from_project:
			frappe.get_doc("Project", self.project).update_project()

	def check_recursion(self):
		if self.flags.ignore_recursion_check: return
		check_list = [['task', 'parent'], ['parent', 'task']]
		for d in check_list:
			task_list, count = [self.name], 0
			while (len(task_list) > count ):
				tasks = frappe.db.sql(" select %s from `tabTask Depends On` where %s = %s " %
					(d[0], d[1], '%s'), cstr(task_list[count]))
				count = count + 1
				for b in tasks:
					if b[0] == self.name:
						frappe.throw(_("Circular Reference Error"), CircularReferenceError)
					if b[0]:
						task_list.append(b[0])

				if count == 15:
					break

	def reschedule_dependent_tasks(self):
		end_date = self.exp_end_date or self.act_end_date
		if end_date:
			for task_name in frappe.db.sql("""
				select name from `tabTask` as parent
				where parent.project = %(project)s
					and parent.name in (
						select parent from `tabTask Depends On` as child
						where child.task = %(task)s and child.project = %(project)s)
			""", {'project': self.project, 'task':self.name }, as_dict=1):
				task = frappe.get_doc("Task", task_name.name)
				if task.exp_start_date and task.exp_end_date and task.exp_start_date < getdate(end_date) and task.status == "Open":
					task_duration = date_diff(task.exp_end_date, task.exp_start_date)
					task.exp_start_date = add_days(end_date, 1)
					task.exp_end_date = add_days(task.exp_start_date, task_duration)
					task.flags.ignore_recursion_check = True
					task.save()

	def has_webform_permission(self):
		project_user = frappe.db.get_value("Project User", {"parent": self.project, "user":frappe.session.user} , "user")
		if project_user:
			return True

	def populate_depends_on(self):
		if self.parent_task:
			parent = frappe.get_doc('Task', self.parent_task)
			if not self.name in [row.task for row in parent.depends_on]:
				parent.append("depends_on", {
					"doctype": "Task Depends On",
					"task": self.name,
					"subject": self.subject
				})
				parent.save()

	def on_trash(self):
		if check_if_child_exists(self.name):
			throw(_("Child Task exists for this Task. You can not delete this Task."))

		self.update_nsm_model()

@frappe.whitelist()
def check_if_child_exists(name):
	child_tasks = frappe.get_all("Task", filters={"parent_task": name})
	child_tasks = [get_link_to_form("Task", task.name) for task in child_tasks]
	return child_tasks


def get_project(doctype, txt, searchfield, start, page_len, filters):
	from erpnext.controllers.queries import get_match_cond
	return frappe.db.sql(""" select name from `tabProject`
			where %(key)s like %(txt)s
				%(mcond)s
			order by name
			limit %(start)s, %(page_len)s""" % {
				'key': searchfield,
				'txt': frappe.db.escape('%' + txt + '%'),
				'mcond':get_match_cond(doctype),
				'start': start,
				'page_len': page_len
			})


@frappe.whitelist()
def set_multiple_status(names, status):
	names = json.loads(names)
	for name in names:
		task = frappe.get_doc("Task", name)
		task.status = status
		task.save()

def set_tasks_as_overdue():
	frappe.db.sql("""update tabTask set `status`='Overdue'
		where exp_end_date is not null
		and exp_end_date < CURDATE()
		and `status` not in ('Closed', 'Cancelled')""")

@frappe.whitelist()
def get_children(doctype, parent, task=None, project=None, is_root=False):

	filters = [['docstatus', '<', '2']]

	if task:
		filters.append(['parent_task', '=', task])
	elif parent and not is_root:
		# via expand child
		filters.append(['parent_task', '=', parent])
	else:
		filters.append(['ifnull(`parent_task`, "")', '=', ''])

	if project:
		filters.append(['project', '=', project])

	tasks = frappe.get_list(doctype, fields=[
		'name as value',
		'subject as title',
		'is_group as expandable'
	], filters=filters, order_by='name')

	# return tasks
	return tasks

@frappe.whitelist()
def add_node():
	from frappe.desk.treeview import make_tree_args
	args = frappe.form_dict
	args.update({
		"name_field": "subject"
	})
	args = make_tree_args(**args)

	if args.parent_task == 'All Tasks' or args.parent_task == args.project:
		args.parent_task = None

	frappe.get_doc(args).insert()

@frappe.whitelist()
def add_multiple_tasks(data, parent):
	data = json.loads(data)
	new_doc = {'doctype': 'Task', 'parent_task': parent if parent!="All Tasks" else ""}
	new_doc['project'] = frappe.db.get_value('Task', {"name": parent}, 'project') or ""

	for d in data:
		if not d.get("subject"): continue
		new_doc['subject'] = d.get("subject")
		new_task = frappe.get_doc(new_doc)
		new_task.insert()

def on_doctype_update():
	frappe.db.add_index("Task", ["lft", "rgt"])
