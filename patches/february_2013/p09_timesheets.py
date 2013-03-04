import webnotes

def execute():
	# convert timesheet details to time logs
	for name in webnotes.conn.sql_list("""select name from tabTimesheet"""):
		ts = webnotes.bean("Timesheet", name)
		for tsd in ts.doclist.get({"doctype":"Timesheet Detail"}):
			tl = webnotes.bean({
				"doctype": "Time Log",
				"status": "Draft",
				"from_time": ts.doc.timesheet_date + " " + tsd.act_start_time,
				"to_time": ts.doc.timesheet_date + " " + tsd.act_end_time,
				"activity_type": tsd.activity_type,
				"task": tsd.task_id,
				"project": tsd.project_name,
				"note": ts.doc.notes,
				"file_list": ts.doc.file_list,
				"_user_tags": ts.doc._user_tags
			})
			tl.insert()