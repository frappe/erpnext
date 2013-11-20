# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes

def execute():
	# convert timesheet details to time logs
	webnotes.reload_doc("projects", "doctype", "time_log")
	
	# copy custom fields
	custom_map = {"Timesheet":[], "Timesheet Detail":[]}
	for custom_field in webnotes.conn.sql("""select * from `tabCustom Field` where 
		dt in ('Timesheet', 'Timesheet Detail')""", as_dict=True):
		custom_map[custom_field.dt].append(custom_field.fieldname)
		custom_field.doctype = "Custom Field"
		custom_field.dt = "Time Log"
		custom_field.insert_after = None
		try:
			cf = webnotes.bean(custom_field).insert()
		except Exception, e:
			# duplicate custom field
			pass
	
	for name in webnotes.conn.sql_list("""select name from tabTimesheet"""):
		ts = webnotes.bean("Timesheet", name)
		
		for tsd in ts.doclist.get({"doctype":"Timesheet Detail"}):
			if not webnotes.conn.exists("Project", tsd.project_name):
				tsd.project_name = None
			if not webnotes.conn.exists("Task", tsd.task_id):
				tsd.task_id = None
				
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
				"_user_tags": ts.doc._user_tags,
				"owner": ts.doc.owner,
				"creation": ts.doc.creation,
				"modified_by": ts.doc.modified_by
			})
			
			for key in custom_map["Timesheet"]:
				tl.doc.fields[key] = ts.doc.fields.get(key)

			for key in custom_map["Timesheet Detail"]:
				tl.doc.fields[key] = tsd.fields.get(key)
			
			tl.make_controller()
			tl.controller.set_status()
			tl.controller.calculate_total_hours()
			tl.doc.insert()
