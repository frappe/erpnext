# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, json
from frappe.utils import getdate, date_diff, add_days, cstr
from frappe.utils.data import today
from frappe import _

from frappe.model.document import Document

class CircularReferenceError(frappe.ValidationError): pass

class Task(Document):


	def get_feed(self):
		return '{0}: {1}'.format(_(self.status), self.subject)

	def onload(self):
		#Load task candidates for quick view
		if not self.get('__unsaved') and not self.get("candidates"):
			self.load_candidates()

	def __setup__(self):
		self.onload()

	def load_candidates(self):
		 #Load `candidates` from the database
		self.candidates = []

		for candidate in self.get_candidates():
			self.append("candidates", {
				"passport_no": candidate.passport_no,
				"pending_for": candidate.pending_for,
				"given_name": candidate.given_name,
				"india_experience":candidate.india_experience,
				"gulf_experience":candidate.gulf_experience,
				"current_ctc":candidate.current_ctc,
				"currency_type":candidate.currency_type,
				"expected_ctc":candidate.expected_ctc,
				"currency_type1":candidate.currency_type1,
				"expiry_date":candidate.expiry_date,
				"ecr_status":candidate.ecr_status,
				"current_location":candidate.current_location,
				"mobile": candidate.mobile,
				"landline":candidate.landline,
				"skype_id":candidate.skype_id,
				"associate_name":candidate.associate_name,
				"contact_email":candidate.contact_no,
				"email": candidate.email,
				"candidate_id": candidate.name
			})

	def get_candidates(self):
		return frappe.get_all("Candidate", "*", {"task": self.name}, order_by="given_name asc")
		# frappe.db.sql("select * from `tabCandidate` where task=%s order_by='given_name asc'", self.name)

	def get_project_details(self):
		return { "project": self.project }

	def get_customer_details(self):
		cust = frappe.db.sql("select customer_name from `tabCustomer` where name=%s", self.customer)
		if cust:
			ret = {'customer_name': cust and cust[0][0] or ''}
			return ret

	def validate(self):
		self.validate_dates()
		self.validate_progress()
		self.validate_status()
<<<<<<< HEAD
		self.update_depends_on()
=======
		self.sync_candidates()
		self.pending_count()
		self.update_dow()
>>>>>>> Vhrs Update 12/11/16

	def validate_dates(self):
		if self.exp_start_date and self.exp_end_date and getdate(self.exp_start_date) > getdate(self.exp_end_date):
			frappe.throw(_("'Expected Start Date' can not be greater than 'Expected End Date'"))

		if self.act_start_date and self.act_end_date and getdate(self.act_start_date) > getdate(self.act_end_date):
			frappe.throw(_("'Actual Start Date' can not be greater than 'Actual End Date'"))

	#Custom for candidates -->
	def sync_candidates(self):
		"""sync candidates and remove table"""
		if self.flags.dont_sync_candidates: return
		candidate_names = []
		for c in self.candidates:
			if c.candidate_id:
				candidate = frappe.get_doc("Candidate", c.candidate_id)
			else:
				candidate = frappe.new_doc("Candidate")
				candidate.task = self.name

			candidate.update({
				"passport_no": c.passport_no,
				"pending_for": c.pending_for,
				"given_name": c.given_name,
				"landline":c.landline,
				"mobile": c.mobile,
				"email": c.email,
				"india_experience":c.india_experience,
				"gulf_experience":c.gulf_experience,
				"current_ctc":c.current_ctc,
				"currency_type":c.currency_type,
				"expected_ctc":c.expected_ctc,
				"currency_type1":c.currency_type1,
				"expiry_date":c.expiry_date,
				"ecr_status":c.ecr_status,
				"current_location":c.current_location,
				"mobile": c.mobile,
				"landline":c.landline,
				"skype_id":c.skype_id,
				"associate_name":c.associate_name,
				"contact_email":c.contact_no,
				})

			candidate.flags.ignore_links = True
			candidate.flags.from_task = True
			candidate.flags.ignore_feed = True
			candidate.save(ignore_permissions = True)
			candidate_names.append(candidate.name)

		# delete
		for c in frappe.get_all("Candidate", ["name"], {"task": self.name, "name": ("not in", candidate_names)}):
			frappe.delete_doc("Candidate", c.name)


    #<---

	def validate_status(self):
		if self.status!=self.get_db_value("status") and self.status == "Closed":
			for d in self.depends_on:
				if frappe.db.get_value("Task", d.task, "status") != "Closed":
					frappe.throw(_("Cannot close task as its dependant task {0} is not closed.").format(d.task))

			from frappe.desk.form.assign_to import clear
			clear(self.doctype, self.name)
			
	def validate_progress(self):
		if self.progress > 100:
			frappe.throw(_("Progress % for a task cannot be more than 100."))

<<<<<<< HEAD
	def update_depends_on(self):
		depends_on_tasks = ""
		for d in self.depends_on:
			if d.task:
				depends_on_tasks += d.task + ","
		self.depends_on_tasks = depends_on_tasks
=======
	def pending_count(self):
		count = 0
		for candidate in self.get_candidates() :
			if candidate.pending_for == "Client Interview":
				count = count + 1

		self.r2_test = count

		if self.r1_count:
			r1 = int(self.r1_count)
			r3 = int(self.r3_count)
			r4 = int(self.r4_count)
			r6 = int(self.r6_count)
			r8 = int(self.r8_count)
			prop = int(self.proposition)
			self.pending_profiles_to_send = (r1 - (r6 + r8))*prop - (r3 + r4)

	def update_dow(self):
		if self.status == 'Working':
			self.date_of_working =today()
>>>>>>> Vhrs Update 12/11/16

	def on_update(self):
		self.check_recursion()
		self.reschedule_dependent_tasks()
		self.update_project()

	def update_total_expense_claim(self):
		self.total_expense_claim = frappe.db.sql("""select sum(total_sanctioned_amount) from `tabExpense Claim`
			where project = %s and task = %s and approval_status = "Approved" and docstatus=1""",(self.project, self.name))[0][0]

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
			for task_name in frappe.db.sql("""select name from `tabTask` as parent where parent.project = %(project)s and parent.name in \
				(select parent from `tabTask Depends On` as child where child.task = %(task)s and child.project = %(project)s)""",
				{'project': self.project, 'task':self.name }, as_dict=1):

				task = frappe.get_doc("Task", task_name.name)
				if task.exp_start_date and task.exp_end_date and task.exp_start_date < getdate(end_date) and task.status == "Open":
					task_duration = date_diff(task.exp_end_date, task.exp_start_date)
					task.exp_start_date = add_days(end_date, 1)
					task.exp_end_date = add_days(task.exp_start_date, task_duration)
					task.flags.ignore_recursion_check = True
					task.save()

	def has_webform_permission(doc):
		project_user = frappe.db.get_value("Project User", {"parent": doc.project, "user":frappe.session.user} , "user")
		if project_user:
			return True				

@frappe.whitelist()
def get_events(start, end, filters=None):
	"""Returns events for Gantt / Calendar view rendering.

	:param start: Start date-time.
	:param end: End date-time.
	:param filters: Filters (JSON).
	"""
	from frappe.desk.calendar import get_event_conditions
	conditions = get_event_conditions("Task", filters)

	data = frappe.db.sql("""select name, exp_start_date, exp_end_date,
		subject, status, project from `tabTask`
		where ((ifnull(exp_start_date, '0000-00-00')!= '0000-00-00') \
				and (exp_start_date <= %(end)s) \
			or ((ifnull(exp_end_date, '0000-00-00')!= '0000-00-00') \
				and exp_end_date >= %(start)s))
		{conditions}""".format(conditions=conditions), {
			"start": start,
			"end": end
		}, as_dict=True, update={"allDay": 0})

	return data

def get_project(doctype, txt, searchfield, start, page_len, filters):
	from erpnext.controllers.queries import get_match_cond
	return frappe.db.sql(""" select name from `tabProject`
			where %(key)s like "%(txt)s"
				%(mcond)s
			order by name
			limit %(start)s, %(page_len)s """ % {'key': searchfield,
			'txt': "%%%s%%" % frappe.db.escape(txt), 'mcond':get_match_cond(doctype),
			'start': start, 'page_len': page_len})			


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
<<<<<<< HEAD
		and `status` not in ('Closed', 'Cancelled')""")
		
=======
		and `status` not in ('Closed', 'Cancelled', 'Hold','Pending Review','DnD')""")

def set_dow():
	frappe.db.sql("""update tabTask set `date_of_working`=%s
		where `status`='Working'""",today())
>>>>>>> Vhrs Update 12/11/16
