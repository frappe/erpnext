# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cint, cstr, date_diff, flt, formatdate, getdate, get_url_to_form, \
	comma_or, get_fullname
from frappe import msgprint, throw, _
from frappe.model.controller import DocListController

class LeaveDayBlockedError(webnotes.ValidationError): pass
class OverlapError(webnotes.ValidationError): pass
class InvalidLeaveApproverError(webnotes.ValidationError): pass
class LeaveApproverIdentityError(webnotes.ValidationError): pass

class DocType(DocListController):
	def setup(self):
		if frappe.conn.exists(self.doc.doctype, self.doc.name):
			self.previous_doc = frappe.doc(self.doc.doctype, self.doc.name)
		else:
			self.previous_doc = None

	def validate(self):
		self.validate_to_date()
		self.validate_balance_leaves()
		self.validate_leave_overlap()
		self.validate_max_days()
		self.show_block_day_warning()
		self.validate_block_days()
		self.validate_leave_approver()

	def on_update(self):
		if (not self.previous_doc and self.doc.leave_approver) or (self.previous_doc and \
				self.doc.status == "Open" and self.previous_doc.leave_approver != self.doc.leave_approver):
			# notify leave approver about creation
			self.notify_leave_approver()
		elif self.previous_doc and \
				self.previous_doc.status == "Open" and self.doc.status == "Rejected":
			# notify employee about rejection
			self.notify_employee(self.doc.status)

	def on_submit(self):
		if self.doc.status != "Approved":
			throw(_("Only Leave Applications with status 'Approved' can be Submitted"))

		# notify leave applier about approval
		self.notify_employee(self.doc.status)

	def on_cancel(self):
		# notify leave applier about cancellation
		self.notify_employee("cancelled")

	def show_block_day_warning(self):
		from erpnext.hr.doctype.leave_block_list.leave_block_list import get_applicable_block_dates		

		block_dates = get_applicable_block_dates(self.doc.from_date, self.doc.to_date, 
			self.doc.employee, self.doc.company, all_lists=True)
			
		if block_dates:
			msgprint(_("Warning: Leave application contains following block dates") + ":")
			for d in block_dates:
				msgprint(formatdate(d.block_date) + ": " + d.reason)

	def validate_block_days(self):
		from erpnext.hr.doctype.leave_block_list.leave_block_list import get_applicable_block_dates

		block_dates = get_applicable_block_dates(self.doc.from_date, self.doc.to_date, 
			self.doc.employee, self.doc.company)
			
		if block_dates:
			if self.doc.status == "Approved":
				throw(_("Cannot approve leave as you are not authorized to approve leaves on Block Dates"), 
					exc=LeaveDayBlockedError)

	def get_holidays(self):
		tot_hol = frappe.conn.sql("""select count(*) from `tabHoliday` h, `tabHoliday List` hl, 
			`tabEmployee` emp where emp.name=%s and h.parent=hl.name and emp.holiday_list=hl.name 
			and h.holiday_date between %s and %s""", (self.doc.employee, self.doc.from_date, self.doc.to_date))
		if not tot_hol:
			tot_hol = frappe.conn.sql("""select count(*) from `tabHoliday` h, `tabHoliday List` hl 
				where h.parent = hl.name and h.holiday_date between %s and %s
				and ifnull(hl.is_default,0) = 1 and hl.period = %s""",
				(self.doc.from_date, self.doc.to_date, self.doc.period))

		return tot_hol and flt(tot_hol[0][0]) or 0

	def get_total_leave_days(self):
		"""Calculates total leave days based on input and holidays"""
		ret = {'total_leave_days' : 0.5}
		if not self.doc.half_day:
			tot_days = date_diff(self.doc.to_date, self.doc.from_date) + 1
			holidays = self.get_holidays()
			ret = {
				'total_leave_days' : flt(tot_days) - flt(holidays)
			}
		return ret

	def validate_to_date(self):
		if self.doc.from_date and self.doc.to_date and \
				(getdate(self.doc.to_date) < getdate(self.doc.from_date)):
			throw(_("To date cannot be before from date"))

	def validate_balance_leaves(self):
		if self.doc.from_date and self.doc.to_date:
			self.doc.total_leave_days = self.get_total_leave_days()["total_leave_days"]
			
			if self.doc.total_leave_days == 0:
				throw(_("""The day(s) on which you are applying for leave coincide with holiday(s). \
					You need not apply for leave."""))

			if not is_lwp(self.doc.leave_type):
				self.doc.leave_balance = get_leave_balance(self.doc.employee,
					self.doc.leave_type, self.doc.period)["leave_balance"]

				if self.doc.status != "Rejected" \
						and self.doc.leave_balance - self.doc.total_leave_days < 0:
					# check if this leave type allow the remaining balance to be in negative. 
					# If yes then warn the user and continue to save else warn the user and don't save.
					throw("{msg}: {leave_type}".format(**{
						"msg": _("There is not enough leave balance for Leave Type"),
						"leave_type": self.doc.leave_type
					}), exc=not(webnotes.conn.get_value("Leave Type", self.doc.leave_type, "allow_negative") or None))

	def validate_leave_overlap(self):
		if not self.doc.name:
			self.doc.name = "New Leave Application"

		for d in frappe.conn.sql("""select name, leave_type, posting_date, 
			from_date, to_date from `tabLeave Application` where 
			employee=%(employee)s and docstatus<2 and status in ("Open", "Approved") 
			and (from_date between %(from_date)s and %(to_date)s 
				or to_date between %(from_date)s and %(to_date)s 
				or %(from_date)s between from_date and to_date) 
			and name != %(name)s""", self.doc.fields, as_dict = 1):

			throw("""Employee : %s has already applied for %s between %s and %s on %s. \
				Please refer Leave Application : \
				<a href=\"#Form/Leave Application/%s\">%s</a>""" % (self.doc.employee, 
				cstr(d['leave_type']), formatdate(d['from_date']), formatdate(d['to_date']), 
				formatdate(d['posting_date']), d['name'], d['name']), exc=OverlapError)

	def validate_max_days(self):
		max_days = frappe.conn.sql("select max_days_allowed from `tabLeave Type` where name = '%s'" %(self.doc.leave_type))
		max_days = max_days and flt(max_days[0][0]) or 0
		if max_days and self.doc.total_leave_days > max_days:
			throw("{cannot} {leave_type} {more} {days} {msg}".format(**{
				"cannot": _("Sorry! You cannot apply for"),
				"leave_type": self.doc.leave_type,
				"more": _("for more than"),
				"days": max_days,
				"msg": _("days")
			}))

	def validate_leave_approver(self):
		employee = frappe.bean("Employee", self.doc.employee)
		leave_approvers = [l.leave_approver for l in 
			employee.doclist.get({"parentfield": "employee_leave_approvers"})]

		if len(leave_approvers) and self.doc.leave_approver not in leave_approvers:
			throw(("[" + _("For Employee") + ' "' + self.doc.employee + '"] ' 
				+ _("Leave Approver can be one of") + ": " 
				+ comma_or(leave_approvers)), exc=InvalidLeaveApproverError)

		elif self.doc.leave_approver and not frappe.conn.sql("""select name from `tabUserRole` 
			where parent=%s and role='Leave Approver'""", self.doc.leave_approver):
				throw(get_fullname(self.doc.leave_approver) + ": " \
					+ _("does not have role 'Leave Approver'"), exc=InvalidLeaveApproverError)

		elif self.doc.docstatus==1 and len(leave_approvers) and self.doc.leave_approver!=frappe.session.user:
			throw(_("Only the selected Leave Approver can submit this Leave Application"),
				exc=LeaveApproverIdentityError)

	def notify_employee(self, status):
		employee = frappe.doc("Employee", self.doc.employee)
		if not employee.user_id:
			return

		def _get_message(url=False):
			if url:
				name = get_url_to_form(self.doc.doctype, self.doc.name)
			else:
				name = self.doc.name

			return (_("Leave Application") + ": %s - %s") % (name, _(status))

		self.notify({
			# for post in messages
			"message": _get_message(url=True),
			"message_to": employee.user_id,
			"subject": _get_message(),
		})

	def notify_leave_approver(self):
		employee = frappe.doc("Employee", self.doc.employee)

		def _get_message(url=False):
			name = self.doc.name
			employee_name = cstr(employee.employee_name)
			if url:
				name = get_url_to_form(self.doc.doctype, self.doc.name)
				employee_name = get_url_to_form("Employee", self.doc.employee, label=employee_name)
			
			return (_("New Leave Application") + ": %s - " + _("Employee") + ": %s") % (name, employee_name)

		self.notify({
			# for post in messages
			"message": _get_message(url=True),
			"message_to": self.doc.leave_approver,
			
			# for email
			"subject": _get_message()
		})

	def notify(self, args):
		args = frappe._dict(args)
		from frappe.core.page.messages.messages import post
		post({"txt": args.message, "contact": args.message_to, "subject": args.subject,
			"notify": cint(self.doc.follow_via_email)})

@webnotes.whitelist()
def get_leave_balance(employee, leave_type, period):	
	leave_all = frappe.conn.sql("""select total_leaves_allocated 
		from `tabLeave Allocation` where employee=%s and leave_type=%s
		and period=%s and docstatus=1""", (employee, 
			leave_type, period))

	leave_all = leave_all and flt(leave_all[0][0]) or 0

	leave_app = frappe.conn.sql("""select SUM(total_leave_days) 
		from `tabLeave Application` where employee=%s and leave_type=%s and period=%s 
		and status="Approved" and docstatus=1""", (employee, leave_type, period))
	leave_app = leave_app and flt(leave_app[0][0]) or 0

	ret = {'leave_balance': leave_all - leave_app}
	return ret

def is_lwp(leave_type):
	lwp = frappe.conn.sql("select is_lwp from `tabLeave Type` where name = %s", leave_type)
	return lwp and cint(lwp[0][0]) or 0

@frappe.whitelist()
def get_events(start, end):
	events = []
	employee = frappe.conn.get_default("employee", frappe.session.user)
	company = frappe.conn.get_default("company", frappe.session.user)

	from frappe.widgets.reportview import build_match_conditions
	match_conditions = build_match_conditions("Leave Application")

	# show department leaves for employee
	if "Employee" in frappe.get_roles():
		add_department_leaves(events, start, end, employee, company)

	add_leaves(events, start, end, employee, company, match_conditions)
	
	add_block_dates(events, start, end, employee, company)
	add_holidays(events, start, end, employee, company)

	return events

def add_department_leaves(events, start, end, employee, company):
	department = frappe.conn.get_value("Employee", employee, "department")
	if not department:
		return

	# department leaves
	department_employees = frappe.conn.sql_list("""select name from tabEmployee where department=%s
		and company=%s""", (department, company))

	match_conditions = "employee in (\"%s\")" % '", "'.join(department_employees)
	add_leaves(events, start, end, employee, company, match_conditions=match_conditions)

def add_leaves(events, start, end, employee, company, match_conditions=None):
	query = """select name, from_date, to_date, employee_name, half_day, 
		status, employee, docstatus
		from `tabLeave Application` where
		(from_date between %s and %s or to_date between %s and %s)
		and docstatus < 2
		and status!="Rejected" """
	if match_conditions:
		query += " and " + match_conditions

	for d in frappe.conn.sql(query, (start, end, start, end), as_dict=True):
		e = {
			"name": d.name,
			"doctype": "Leave Application",
			"from_date": d.from_date,
			"to_date": d.to_date,
			"status": d.status,
			"title": cstr(d.employee_name) + \
				(d.half_day and _(" (Half Day)") or ""),
			"docstatus": d.docstatus
		}
		if e not in events:
			events.append(e)

def add_block_dates(events, start, end, employee, company):
	# block days
	from erpnext.hr.doctype.leave_block_list.leave_block_list import get_applicable_block_dates

	cnt = 0
	block_dates = get_applicable_block_dates(start, end, employee, company, all_lists=True)

	for block_date in block_dates:
		events.append({
			"doctype": "Leave Block List Date",
			"from_date": block_date.block_date,
			"title": _("Leave Blocked") + ": " + block_date.reason,
			"name": "_" + str(cnt),
		})
		cnt+=1

def add_holidays(events, start, end, employee, company):
	applicable_holiday_list = frappe.conn.get_value("Employee", employee, "holiday_list")
	if not applicable_holiday_list:
		return

	for holiday in frappe.conn.sql("""select name, holiday_date, description
		from `tabHoliday` where parent=%s and holiday_date between %s and %s""", 
		(applicable_holiday_list, start, end), as_dict=True):
			events.append({
				"doctype": "Holiday",
				"from_date": holiday.holiday_date,
				"title": _("Holiday") + ": " + cstr(holiday.description),
				"name": holiday.name
			})

@frappe.whitelist()
def query_for_permitted_employees(doctype, txt, searchfield, start, page_len, filters):
	txt = "%" + cstr(txt) + "%"

	if "Leave Approver" in frappe.user.get_roles():
		condition = """and (exists(select ela.name from `tabEmployee Leave Approver` ela
				where ela.parent=`tabEmployee`.name and ela.leave_approver= "%s") or 
			not exists(select ela.name from `tabEmployee Leave Approver` ela 
				where ela.parent=`tabEmployee`.name)
			or user_id = "%s")""" % (frappe.session.user, frappe.session.user)
	else:
		from frappe.widgets.reportview import build_match_conditions
		condition = build_match_conditions("Employee")
		condition = ("and " + condition) if condition else ""

	return frappe.conn.sql("""select name, employee_name from `tabEmployee`
		where status='Active' and docstatus<2 and
		(`%s` like %s or employee_name like %s) %s
		order by
		case when name like %s then 0 else 1 end,
		case when employee_name like %s then 0 else 1 end,
		name limit %s, %s""" % tuple([searchfield] + ["%s"]*2 + [condition] + ["%s"]*4), 
		(txt, txt, txt, txt, start, page_len))