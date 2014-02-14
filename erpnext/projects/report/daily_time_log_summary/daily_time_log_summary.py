# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import flt

def execute(filters=None):
	if not filters:
		filters = {}
	elif filters.get("to_date"):
		filters["to_date"] = filters.get("to_date") + "24:00:00"
	
	columns = ["Time Log:Link/Time Log:120", "Employee::150", "From Datetime::140", 
		"To Datetime::140", "Hours::70", "Activity Type::120", "Task:Link/Task:150", 
		"Task Subject::180", "Project:Link/Project:120", "Status::70"]
			
	profile_map = get_profile_map()
	task_map = get_task_map()
		
	conditions = build_conditions(filters)
	time_logs = webnotes.conn.sql("""select * from `tabTime Log` 
		where docstatus < 2 %s order by owner asc""" % (conditions, ), filters, as_dict=1)

	if time_logs:
		profiles = [time_logs[0].owner]
		
	data = []	
	total_hours = total_employee_hours = count = 0
	for tl in time_logs:
		if tl.owner not in profiles:
			profiles.append(tl.owner)
			data.append(["", "", "", "Total", total_employee_hours, "", "", "", "", ""])
			total_employee_hours = 0
			
		data.append([tl.name, profile_map[tl.owner], tl.from_time, tl.to_time, tl.hours, 
				tl.activity_type, tl.task, task_map.get(tl.task), tl.project, tl.status])
			
		count += 1
		total_hours += flt(tl.hours)
		total_employee_hours += flt(tl.hours)
		
		if count == len(time_logs):
			data.append(["", "", "", "Total Hours", total_employee_hours, "", "", "", "", ""])

	if total_hours:
		data.append(["", "", "", "Grand Total", total_hours, "", "", "", "", ""])
		
	return columns, data
	
def get_profile_map():
	profiles = webnotes.conn.sql("""select name, 
		concat(first_name, if(last_name, (' ' + last_name), '')) as fullname 
		from tabProfile""", as_dict=1)
	profile_map = {}
	for p in profiles:
		profile_map.setdefault(p.name, []).append(p.fullname)
		
	return profile_map
	
def get_task_map():
	tasks = webnotes.conn.sql("""select name, subject from tabTask""", as_dict=1)
	task_map = {}
	for t in tasks:
		task_map.setdefault(t.name, []).append(t.subject)
		
	return task_map
	
def build_conditions(filters):
	conditions = ""			
	if filters.get("from_date"):
		conditions += " and from_time >= %(from_date)s"
	if filters.get("to_date"):
		conditions += " and to_time <= %(to_date)s"
	
	from webnotes.widgets.reportview import build_match_conditions
	match_conditions = build_match_conditions("Time Log")
	if match_conditions:
		conditions += " and %s" % match_conditions
		
	return conditions