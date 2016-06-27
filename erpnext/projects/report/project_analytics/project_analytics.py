# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from datetime import timedelta
from frappe.utils import flt, getdate, cint

def execute(filters=None):
	if not filters: filters = {}
	
	get_week_range(filters)

	validate_filters(filters)
	
	project_list = get_project_list(filters)

	entries = get_entries_project(filters,project_list)

	data = []
	data.extend(entries or [])
	columns = get_columns(filters)

	return columns, data

def validate_filters(filters):
	
	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date"))

def get_employees(filters, worked_on):
	"""Get a list of dict {"employee_id": employee_id, "employee_name": employee_name, "hours": hours}"""
	employees_list = []

	additional_conditions = build_conditions(filters, worked_on, filters.employee, activity_type='')
	
	from_date = filters.from_date
	to_date = filters.to_date

	if filters.week_range:
		from_date, to_date = frappe.db.get_value("Week Range", filters.week_range, ["start_date","end_date"])
	
	for d in frappe.db.sql("""select employee,employee_name, sum(hours) as hours
				from `tabTime Log` where docstatus<2
				{additional_conditions}
				and (employee_name is not null or employee_name !='')
				group by employee,employee_name
				order by employee_name""".format(additional_conditions=additional_conditions),
				{"start": from_date, "end": to_date, "employee": filters.employee,"activity": filters.activity, "worked_on": worked_on}, as_dict=1):
		employees = frappe._dict({
			"employee_id": d.employee,
                	"employee_name": d.employee_name,
			"hours": d.hours
    		})
		employees_list.append(employees)

	return employees_list

def get_activity(filters, employee, worked_on):
	activity_list = []
	
	additional_conditions = build_conditions(filters, worked_on, employee, filters.activity)
	
	from_date = filters.from_date
	to_date = filters.to_date
	
	if filters.week_range:
		from_date, to_date = frappe.db.get_value("Week Range", filters.week_range, ["start_date","end_date"])
	
	for d in frappe.db.sql("""select activity_type as row_labels,sum(hours) as hours from `tabTime Log` 
				where docstatus<2
				{additional_conditions}
				group by activity_type
				order by activity_type""".format(additional_conditions=additional_conditions), 
				{"start": from_date, "end": to_date, "employee": employee, "activity": filters.activity, "worked_on": worked_on}, as_dict=1):
		activities = frappe._dict({
			"activity_type": d.row_labels,
			"hours": d.hours
    		})
		activity_list.append(activities)

	return activity_list

def get_date_list(filters, employee, activity, worked_on):
	date_list = []
	
	additional_conditions = build_conditions(filters, worked_on, employee, activity)
	
	from_date = filters.from_date
	to_date = filters.to_date
	
	if filters.week_range:
		from_date, to_date = frappe.db.get_value("Week Range", filters.week_range, ["start_date","end_date"])
	
	for d in frappe.db.sql("""select date_worked as row_labels,sum(hours) as hours from `tabTime Log` 
				where docstatus<2
				{additional_conditions}
				and activity_type = %(activity)s
				group by date_worked
				order by date_worked""".format(additional_conditions=additional_conditions), 
				{"start":from_date, "end":to_date, "employee": employee, "worked_on": worked_on, "activity": activity}, as_dict=1):
		date_worked = frappe._dict({
			"date_worked": d.row_labels,
			"hours": d.hours
    		})
		date_list.append(date_worked)

	return date_list

def get_tlname_list(filters, employee, activity, worked_on, date_worked):
	name_list = []
	
	additional_conditions = build_conditions(filters, worked_on, employee, activity)

	from_date = filters.from_date
	to_date = filters.to_date
	
	if filters.week_range:
		from_date, to_date = frappe.db.get_value("Week Range", filters.week_range, ["start_date","end_date"])

	for d in frappe.db.sql("""select name as row_labels,sum(hours) as hours from `tabTime Log` 
				where docstatus<2
				{additional_conditions}
				and activity_type = %(activity)s and date_worked = %(date_worked)s
				group by name
				order by name""".format(additional_conditions=additional_conditions),
				{"start":from_date, "end":to_date, "employee": employee, "worked_on": worked_on, "activity": activity, "date_worked": date_worked}, as_dict=1):
		tl_name = frappe._dict({
			"tl_name": d.row_labels,
			"hours": d.hours
    		})
		name_list.append(tl_name)

	return name_list

def get_project_list(filters):
	"""Get a list of dict {"project": project, "hours": hours}"""
	projects_list = []
	
	additional_conditions = build_conditions(filters, worked_on='',employee='',activity_type='')
	
	from_date = filters.from_date
	to_date = filters.to_date
	
	if filters.week_range:
		from_date, to_date = frappe.db.get_value("Week Range", filters.week_range, ["start_date","end_date"])

	
	if filters.get("worked_on") and frappe.db.exists("Issue", filters.worked_on[0:9]):
		filters.worked_on = filters.worked_on[0:9]

	for d in frappe.db.sql("""select project as worked_on, sum(hours) as hours from `tabTime Log`
					where docstatus<2 {additional_conditions}
					and (support_ticket='' or support_ticket is NULL)
					and (project is not Null and project !='')
					group by project
				union 
				select support_ticket as worked_on, sum(hours) as hours from `tabTime Log`
					where docstatus<2 {additional_conditions}
					and (support_ticket !='' and support_ticket is not NULL)
					group by support_ticket
				union
				select if(if(support_ticket='' or support_ticket is NULL,project,support_ticket) is NULL or
					if(support_ticket='' or support_ticket is NULL,project,support_ticket)='', 'No Project/Issue Associated',
					if(support_ticket='' or support_ticket is NULL,project,support_ticket))  as worked_on, sum(hours) as hours from `tabTime Log`
					where docstatus<2 {additional_conditions}
					and (support_ticket='' or support_ticket is NULL)
					and (project is Null or project ='')
					group by if(if(support_ticket='' or support_ticket is NULL,project,support_ticket) is NULL or
					if(support_ticket='' or support_ticket is NULL,project,support_ticket)='', 'No Project/Issue Associated',
					if(support_ticket='' or support_ticket is NULL,project,support_ticket)) """.format(additional_conditions=additional_conditions), 
				{"start":from_date,"end":to_date, "employee": filters.employee, "activity": filters.activity, "worked_on": filters.worked_on}, as_dict=1):
		
		if frappe.db.exists("Issue", d.worked_on):
			subject = frappe.db.get_value("Issue",d.worked_on,"subject")
			showing_label = d.worked_on + " " + subject
			type = 'Issue'
		elif d.worked_on == 'No Project/Issue Associated':
			showing_label = d.worked_on
			type = 'No Project/Issue'
		else:
			showing_label = d.worked_on
			type = 'Project'

		projects = frappe._dict({
			"showing_label": showing_label, 
			"worked_on": d.worked_on,
                	"hours": d.hours,
			"type": type
    		})
		projects_list.append(projects)

	return projects_list

def get_columns(filters):
	
	columns = [{
		"fieldname": "row_labels",
		"label": _("Row Labels"),
		"fieldtype": "Link",
		"options": "Time Log",
		"width": 400
		},
		{
		"fieldname": "hours",
		"label": _("Sum of Hours"),
		"fieldtype": "Float",
		"width": 150
		}]
	
	return columns

def get_entries_project(filters,project_list):
	
	out = []
	
	grand_total = 0
	get_issue = True
	get_project = True
	issue_hours = 0
	project_hours = 0
		
	for project in project_list:
		# add to output
		if project.hours>0:
			
			grand_total = grand_total + project.hours
			
			if project.worked_on == "No Project/Issue Associated":
				row = {
					"showing_labels": 'No Project/Issue',
					"row_labels": 'No Project/Issue',
					"parent_labels": None,
					"hours": project.hours,
					"indent": 0
					}
				out.append(row)
				parent_labels = 'No Project/Issue'
			elif frappe.db.exists("Issue", project.worked_on):
				if get_issue:
					row = {
						"showing_labels": 'Issues',
						"row_labels": 'Issues',
						"parent_labels": None,
						"hours": 0,
						"indent": 0
					}
					out.append(row)
					get_issue = False
				
				issue_hours += project.hours
				parent_labels = 'Issues'
			else:
				if get_project:
					row = {
						"showing_labels": 'Projects',
						"row_labels": 'Projects',
						"parent_labels": None,
						"hours": 0,
						"indent": 0
					}
					out.append(row)
					get_project = False
				
				project_hours += project.hours
				parent_labels = 'Projects'

			row = {
				"showing_labels": project.showing_label,
				"row_labels": project.worked_on,
				"parent_labels": parent_labels,
				"hours": project.hours,
				"type": project.type,
				"indent": 1
			}
			out.append(row)

			employees_list = get_employees(filters, project.worked_on)
			for employee in employees_list:
				row = {
					"showing_labels": employee.employee_name,
					"row_labels": employee.employee_name + '' + project.worked_on,
					"parent_labels": project.worked_on,
					"hours": employee.hours,
					"indent": 2
				}
				out.append(row)
				
				activity_list = get_activity(filters,employee.employee_id,project.worked_on)
				for d in activity_list:
					row = {
						"showing_labels": d.activity_type,
						"row_labels": d.activity_type + '' + employee.employee_name + '' + project.worked_on,
						"parent_labels": employee.employee_name + '' + project.worked_on,
						"hours": d.hours,
						"indent": 3
					}
					out.append(row)
					
					date_list = get_date_list(filters,employee.employee_id,d.activity_type,project.worked_on)
					for details in date_list:
						row = {
							"showing_labels": details.date_worked.strftime("%d/%m/%Y"),
							"row_labels": details.date_worked.strftime("%d/%m/%Y") + ''+ d.activity_type + '' + employee.employee_name + '' + project.worked_on,
							"parent_labels": d.activity_type + '' + employee.employee_name + '' + project.worked_on,
							"hours": details.hours,
							"indent": 4
						}
						out.append(row)
						
						name_list = get_tlname_list(filters, employee.employee_id, d.activity_type, project.worked_on, details.date_worked)
						for name in name_list:
							row = {
								"showing_labels": name.tl_name,
								"row_labels": name.tl_name,
								"parent_labels": details.date_worked.strftime("%d/%m/%Y") + ''+ d.activity_type + '' + employee.employee_name + '' + project.worked_on,
								"hours": name.hours,
								"indent": 5
							}
							out.append(row)
	
	for d in out:
		if d['row_labels'] == "Projects":
			d['hours'] = project_hours
		if d['row_labels'] == "Issues":
			d['hours'] = issue_hours

	total_row = {"showing_labels": "Grand Total" ,"row_labels": "Grand Total", "parent_labels": None,"hours": grand_total,"indent":None}
	
 	out.append(total_row)

	return out

def build_conditions(filters, worked_on, employee, activity_type):

	conditions = "and date_worked between %(start)s and %(end)s"
	if filters.get("employee") or employee:
		conditions += " and employee = %(employee)s"
	
	if filters.get("activity") or activity_type:
		conditions += " and activity_type = %(activity)s"

	if filters.get("worked_on") or worked_on:
		
		if filters.worked_on == "No Project/Issue Associated" or worked_on == "No Project/Issue Associated":
			conditions += " and (project is null or project = '') and (support_ticket is null or support_ticket ='')"
		elif (filters.get("worked_on") and frappe.db.exists("Issue", filters.worked_on[0:9])) or frappe.db.exists("Issue", worked_on):
			conditions += " and support_ticket = %(worked_on)s"
		else:
			conditions += " and project = %(worked_on)s and (support_ticket is null or support_ticket ='')"

	return conditions

def get_week_range(filters):
	
    	frappe.db.sql("""delete from `tabWeek Range`""")
	
	frappe.db.commit()

	start_date = filters.from_date
    	end_date = filters.to_date
	
    	# from date is the previous week's monday
    	from_date = getdate(start_date) - timedelta(days=getdate(start_date).weekday())
	
	# to date is sunday     
    	to_date = from_date + timedelta(days=6)

    	period = from_date.strftime("%d-%m-%Y") + ' - ' + to_date.strftime("%d-%m-%Y")
    	
	idx =0 
	frappe.db.sql("""insert into `tabWeek Range`(name,start_date,end_date,idx) values(%s, %s, %s, %s)""",
		(period, from_date, to_date, idx))

	while to_date < getdate(end_date):
        
        	from_date = to_date + timedelta(days=1)
		to_date = from_date + timedelta(days=6)
		period = from_date.strftime("%d-%m-%Y") + ' - ' + to_date.strftime("%d-%m-%Y")
		idx = idx + 1
		
		frappe.db.sql("""insert into `tabWeek Range`(name,start_date,end_date,idx) values(%s, %s, %s, %s)""",
			(period, from_date, to_date, idx))

	frappe.db.commit()
