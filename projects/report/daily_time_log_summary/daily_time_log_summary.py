from __future__ import unicode_literals
import webnotes

def execute(filters=None):
	if not filters: filters = {}
	columns = ["Employee::150", "From Datetime::120", "To Datetime::120", "Hours::70", "Task::150",
		"Project:Link/Project:120", "Status::70"]
			
	profile_map = get_profile_map()
		
	conditions = build_conditions(filters)
	time_logs = webnotes.conn.sql("""select * from `tabTime Log` 
		where docstatus < 2 %s order by owner asc""" % (conditions,), filters, as_dict=1)
	
	data = []
	profiles = [time_logs[0].owner]
		
	for tl in time_logs:
		
		if tl.owner not in profiles:
			profiles.append(tl.owner)
			data.append([])

		data.append([profile_map[tl.owner], tl.from_time, tl.to_time, tl.hours, 
				tl.task, tl.project, tl.status])		
		
	return columns, data
	
def get_profile_map():
	profiles = webnotes.conn.sql("""select name, 
		concat(first_name, if(last_name, (' ' + last_name), '')) as fullname 
		from tabProfile""", as_dict=1)
	profile_map = {}
	for p in profiles:
		profile_map.setdefault(p.name, []).append(p.fullname)
		
	return profile_map
	
def build_conditions(filters):
	conditions = ""			
	if filters.get("from_date"):
		conditions += " and from_time >= %(from_date)s"
	if filters.get("to_date"):
		conditions += " and to_time <= %(to_date)s"
		
	return conditions