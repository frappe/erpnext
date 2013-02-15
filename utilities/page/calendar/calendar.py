from __future__ import unicode_literals

import webnotes
from webnotes import _

@webnotes.whitelist()
def get_events(start, end, employee=None, company=None):
	roles = webnotes.get_roles()
	events = webnotes.conn.sql("""select name as `id`, subject as title, 
		starts_on as `start`, ends_on as `end`, "Event" as doctype, owner,
		all_day as allDay, event_type 
		from tabEvent where (
			(starts_on between %s and %s)
			or (ends_on between %s and %s)
		)
		and (event_type='Public' or owner=%s
		or exists(select * from `tabEvent User` where 
			`tabEvent User`.parent=tabEvent.name and person=%s)
		or exists(select * from `tabEvent Role` where 
			`tabEvent Role`.parent=tabEvent.name 
			and `tabEvent Role`.role in ('%s')))""" % ('%s', '%s', '%s', '%s', '%s', '%s', 
			"', '".join(roles)), (start, end, start, end,
			webnotes.session.user, webnotes.session.user), as_dict=1)
			

	if employee:
		add_block_dates(events, start, end, employee, company)
		add_department_leaves(events, start, end, employee, company)

	return events

def add_department_leaves(events, start, end, employee, company):
	department = webnotes.conn.get_value("Employee", employee, "department")
	
	if not department:
		return
	
	# department leaves
	department_employees = webnotes.conn.sql_list("select name from tabEmployee where department=%s", 
		department)
	
	for d in webnotes.conn.sql("""select name, from_date, to_date, employee_name, half_day, 
		status, employee
		from `tabLeave Application` where
		(from_date between %s and %s or to_date between %s and %s)
		and docstatus < 2
		and status!="Rejected"
		and employee in ('%s')""" % ("%s", "%s", "%s", "%s", "', '".join(department_employees)), 
			(start, end, start, end), as_dict=True):
			events.append({
				"id": d.name,
				"employee": d.employee,
				"doctype": "Leave Application",
				"start": d.from_date,
				"end": d.to_date,
				"allDay": True,
				"status": d.status,
				"title": _("Leave by") + " " +  d.employee_name + \
					(d.half_day and _(" (Half Day)") or "")
			})
	

def add_block_dates(events, start, end, employee, company):
	# block days
	from hr.doctype.leave_block_list.leave_block_list import get_applicable_block_dates

	cnt = 0
	block_dates = get_applicable_block_dates(start, end, employee, company, all_lists=True)

	for block_date in block_dates:
		events.append({
			"doctype": "Leave Block List Date",
			"start": block_date.block_date,
			"title": _("Leave Blocked") + ": " + block_date.reason,
			"id": "_" + str(cnt),
			"allDay": True
		})
		cnt+=1
	

@webnotes.whitelist()
def update_event(name, start, end):
	webnotes.conn.sql("""update tabEvent set starts_on=%s, ends_on=%s where 
		name=%s""", (start, end, name))
	