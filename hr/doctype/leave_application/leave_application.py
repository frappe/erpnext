# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes import _

from webnotes.utils import cint, cstr, date_diff, flt, formatdate, getdate, get_url_to_form, \
	comma_or, get_fullname
from webnotes import msgprint

class LeaveDayBlockedError(webnotes.ValidationError): pass
class OverlapError(webnotes.ValidationError): pass
class InvalidLeaveApproverError(webnotes.ValidationError): pass
	
from webnotes.model.controller import DocListController
class DocType(DocListController):
	def setup(self):
		if webnotes.conn.exists(self.doc.doctype, self.doc.name):
			self.previous_doc = webnotes.doc(self.doc.doctype, self.doc.name)
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
			webnotes.msgprint("""Only Leave Applications with status 'Approved' can be Submitted.""",
				raise_exception=True)

		# notify leave applier about approval
		self.notify_employee(self.doc.status)
				
	def on_cancel(self):
		# notify leave applier about cancellation
		self.notify_employee("cancelled")

	def show_block_day_warning(self):
		from hr.doctype.leave_block_list.leave_block_list import get_applicable_block_dates		

		block_dates = get_applicable_block_dates(self.doc.from_date, self.doc.to_date, 
			self.doc.employee, self.doc.company, all_lists=True)
			
		if block_dates:
			webnotes.msgprint(_("Warning: Leave application contains following block dates") + ":")
			for d in block_dates:
				webnotes.msgprint(formatdate(d.block_date) + ": " + d.reason)

	def validate_block_days(self):
		from hr.doctype.leave_block_list.leave_block_list import get_applicable_block_dates

		block_dates = get_applicable_block_dates(self.doc.from_date, self.doc.to_date, 
			self.doc.employee, self.doc.company)
			
		if block_dates:
			if self.doc.status == "Approved":
				webnotes.msgprint(_("Cannot approve leave as you are not authorized to approve leaves on Block Dates."))
				raise LeaveDayBlockedError
			
	def get_holidays(self):
		tot_hol = webnotes.conn.sql("""select count(*) from `tabHoliday` h1, `tabHoliday List` h2, `tabEmployee` e1 
			where e1.name = %s and h1.parent = h2.name and e1.holiday_list = h2.name 
			and h1.holiday_date between %s and %s""", (self.doc.employee, self.doc.from_date, self.doc.to_date))
		if not tot_hol:
			tot_hol = webnotes.conn.sql("""select count(*) from `tabHoliday` h1, `tabHoliday List` h2 
				where h1.parent = h2.name and h1.holiday_date between %s and %s
				and ifnull(h2.is_default,0) = 1 and h2.fiscal_year = %s""",
				(self.doc.from_date, self.doc.to_date, self.doc.fiscal_year))
		return tot_hol and flt(tot_hol[0][0]) or 0

	def get_total_leave_days(self):
		"""Calculates total leave days based on input and holidays"""
		ret = {'total_leave_days' : 0.5}
		if not self.doc.half_day:
			tot_days = date_diff(self.doc.to_date, self.doc.from_date) + 1
			holidays = self.get_holidays()
			ret = {
				'total_leave_days' : flt(tot_days)-flt(holidays)
			}
		return ret

	def validate_to_date(self):
		if self.doc.from_date and self.doc.to_date and \
				(getdate(self.doc.to_date) < getdate(self.doc.from_date)):
			msgprint("To date cannot be before from date")
			raise Exception
			
	def validate_balance_leaves(self):
		if self.doc.from_date and self.doc.to_date:
			self.doc.total_leave_days = self.get_total_leave_days()["total_leave_days"]
			
			if self.doc.total_leave_days == 0:
				msgprint(_("Hurray! The day(s) on which you are applying for leave \
					coincide with holiday(s). You need not apply for leave."),
					raise_exception=1)
			
			if not is_lwp(self.doc.leave_type):
				self.doc.leave_balance = get_leave_balance(self.doc.employee,
					self.doc.leave_type, self.doc.fiscal_year)["leave_balance"]

				if self.doc.status != "Rejected" \
						and self.doc.leave_balance - self.doc.total_leave_days < 0:
					#check if this leave type allow the remaining balance to be in negative. If yes then warn the user and continue to save else warn the user and don't save.
					msgprint("There is not enough leave balance for Leave Type: %s" % \
						(self.doc.leave_type,), 
						raise_exception=not(webnotes.conn.get_value("Leave Type", self.doc.leave_type,"allow_negative") or None))
					
	def validate_leave_overlap(self):
		if not self.doc.name:
			self.doc.name = "New Leave Application"
			
		for d in webnotes.conn.sql("""select name, leave_type, posting_date, 
			from_date, to_date 
			from `tabLeave Application` 
			where 
			employee = %(employee)s
			and docstatus < 2
			and status in ("Open", "Approved")
			and (from_date between %(from_date)s and %(to_date)s 
				or to_date between %(from_date)s and %(to_date)s
				or %(from_date)s between from_date and to_date)
			and name != %(name)s""", self.doc.fields, as_dict = 1):
 
			msgprint("Employee : %s has already applied for %s between %s and %s on %s. Please refer Leave Application : <a href=\"#Form/Leave Application/%s\">%s</a>" % (self.doc.employee, cstr(d['leave_type']), formatdate(d['from_date']), formatdate(d['to_date']), formatdate(d['posting_date']), d['name'], d['name']), raise_exception = OverlapError)

	def validate_max_days(self):
		max_days = webnotes.conn.sql("select max_days_allowed from `tabLeave Type` where name = '%s'" %(self.doc.leave_type))
		max_days = max_days and flt(max_days[0][0]) or 0
		if max_days and self.doc.total_leave_days > max_days:
			msgprint("Sorry ! You cannot apply for %s for more than %s days" % (self.doc.leave_type, max_days))
			raise Exception
			
	def validate_leave_approver(self):
		employee = webnotes.bean("Employee", self.doc.employee)
		leave_approvers = [l.leave_approver for l in 
			employee.doclist.get({"parentfield": "employee_leave_approvers"})]

		if len(leave_approvers) and self.doc.leave_approver not in leave_approvers:
			msgprint(("[" + _("For Employee") + ' "' + self.doc.employee + '"] ' 
				+ _("Leave Approver can be one of") + ": "
				+ comma_or(leave_approvers)), raise_exception=InvalidLeaveApproverError)
		
		elif self.doc.leave_approver and not webnotes.conn.sql("""select name from `tabUserRole` 
			where parent=%s and role='Leave Approver'""", self.doc.leave_approver):
				msgprint(get_fullname(self.doc.leave_approver) + ": " \
					+ _("does not have role 'Leave Approver'"), raise_exception=InvalidLeaveApproverError)
			
	def notify_employee(self, status):
		employee = webnotes.doc("Employee", self.doc.employee)
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
		employee = webnotes.doc("Employee", self.doc.employee)
		
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
		args = webnotes._dict(args)
		from core.page.messages.messages import post
		post({"txt": args.message, "contact": args.message_to, "subject": args.subject,
			"notify": cint(self.doc.follow_via_email)})

@webnotes.whitelist()
def get_leave_balance(employee, leave_type, fiscal_year):	
	leave_all = webnotes.conn.sql("""select total_leaves_allocated 
		from `tabLeave Allocation` where employee = %s and leave_type = %s
		and fiscal_year = %s and docstatus = 1""", (employee, 
			leave_type, fiscal_year))
	
	leave_all = leave_all and flt(leave_all[0][0]) or 0
	
	leave_app = webnotes.conn.sql("""select SUM(total_leave_days) 
		from `tabLeave Application` 
		where employee = %s and leave_type = %s and fiscal_year = %s
		and status="Approved" and docstatus = 1""", (employee, leave_type, fiscal_year))
	leave_app = leave_app and flt(leave_app[0][0]) or 0
	
	ret = {'leave_balance': leave_all - leave_app}
	return ret

def is_lwp(leave_type):
	lwp = webnotes.conn.sql("select is_lwp from `tabLeave Type` where name = %s", leave_type)
	return lwp and cint(lwp[0][0]) or 0
	
@webnotes.whitelist()
def get_events(start, end):
	events = []
	employee = webnotes.conn.get_default("employee", webnotes.session.user)
	company = webnotes.conn.get_default("company", webnotes.session.user)
	
	from webnotes.widgets.reportview import build_match_conditions
	match_conditions = build_match_conditions("Leave Application")
	
	# show department leaves for employee
	if "Employee" in webnotes.get_roles():
		add_department_leaves(events, start, end, employee, company)

	add_leaves(events, start, end, employee, company, match_conditions)
	
	add_block_dates(events, start, end, employee, company)
	add_holidays(events, start, end, employee, company)
	
	return events
	
def add_department_leaves(events, start, end, employee, company):
	department = webnotes.conn.get_value("Employee", employee, "department")
	
	if not department:
		return
	
	# department leaves
	department_employees = webnotes.conn.sql_list("""select name from tabEmployee where department=%s
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
	
	for d in webnotes.conn.sql(query, (start, end, start, end), as_dict=True):
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
	from hr.doctype.leave_block_list.leave_block_list import get_applicable_block_dates

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
	applicable_holiday_list = webnotes.conn.get_value("Employee", employee, "holiday_list")
	if not applicable_holiday_list:
		return
	
	for holiday in webnotes.conn.sql("""select name, holiday_date, description
		from `tabHoliday` where parent=%s and holiday_date between %s and %s""", 
		(applicable_holiday_list, start, end), as_dict=True):
			events.append({
				"doctype": "Holiday",
				"from_date": holiday.holiday_date,
				"title": _("Holiday") + ": " + cstr(holiday.description),
				"name": holiday.name
			})

@webnotes.whitelist()
def query_for_permitted_employees(doctype, txt, searchfield, start, page_len, filters):
	txt = "%" + cstr(txt) + "%"
	
	if "Leave Approver" in webnotes.user.get_roles():
		condition = """and (exists(select ela.name from `tabEmployee Leave Approver` ela
				where ela.parent=`tabEmployee`.name and ela.leave_approver= "%s") or 
			not exists(select ela.name from `tabEmployee Leave Approver` ela 
				where ela.parent=`tabEmployee`.name)
			or user_id = "%s")""" % (webnotes.session.user, webnotes.session.user)
	else:
		from webnotes.widgets.reportview import build_match_conditions
		condition = build_match_conditions("Employee")
		condition = ("and " + condition) if condition else ""
	
	return webnotes.conn.sql("""select name, employee_name from `tabEmployee`
		where status = 'Active' and docstatus < 2 and
		(`%s` like %s or employee_name like %s) %s
		order by
		case when name like %s then 0 else 1 end,
		case when employee_name like %s then 0 else 1 end,
		name limit %s, %s""" % tuple([searchfield] + ["%s"]*2 + [condition] + ["%s"]*4), 
		(txt, txt, txt, txt, start, page_len))
