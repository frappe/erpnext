# Copyright (c) 2023, viral patel and contributors
# For license information, please see license.txt

# import frappe

import frappe
from frappe import _
from frappe.utils import flt, time_diff_in_hours


def execute(filters=None):
    columns, data = [], []
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data



def get_columns(filters):
    columns = [
        {
            "label": _("Project"),
            "fieldtype": "Link",
            "fieldname": "project",
            "options": "Project",
            "width": 200,
        },
        {
            "label": _("Employee ID"),
            "fieldtype": "Link",
            "fieldname": "employee",
            "options": "Employee",
            "width": 300,
        },
        {
            "label": _("Employee Name"),
            "fieldtype": "data",
            "fieldname": "employee_name",
            "hidden": 1,
            "width": 200,
        },
        {
            "label": _("Timesheet"),
            "fieldtype": "Link",
            "fieldname": "timesheet",
            "options": "Timesheet",
            "width": 150,
        },
    ]
    if filters.get('show_timesheet_detail'):
        columns += [
             {
            "label": _("Activity Type"),
            "fieldtype": "Link",
            "options":"Activity Type",
            "fieldname": "activity_type",
            "width": 200,
            },
        ]
    columns += [
        {"label": _("Working Hours"), "fieldtype": "Float", "fieldname": "total_hours", "width": 150},
        {
            "label": _("Billable Hours"),
            "fieldtype": "Float",
            "fieldname": "total_billable_hours",
            "width": 150,
        },
        {"label": _("Billing Amount"), "fieldtype": "Currency", "fieldname": "amount", "width": 150},
    ]
    if filters.get('show_timesheet_detail'):
        columns += [

        {
            "label": _("From Time"),
            "fieldtype": "Datetime",
            "fieldname": "from_time",
            "width": 200,
        },
        {
            "label": _("to Time"),
            "fieldtype": "Datetime",
            "fieldname": "to_time",
            "width": 200,
        },
        {
            "label": _("Task"),
            "fieldtype": "Datetime",
            "options":"Task",
            "fieldname": "task",
            "width": 200,
        }

        ]
    return columns


def get_data(filters):
    data = []
    if filters.from_date > filters.to_date:
        frappe.msgprint(_("From Date can not be greater than To Date"))
        return data
    
    condition =""
    if filters.get('include_draft_timesheets'):
        condition += "t.docstatus != 2"
    else:
        condition += "t.docstatus = 1"
    if filters.get('from_date') and filters.get("to_date"):
        condition += f" and t.start_date >= '{filters.get('from_date')}'"
        condition += f" and t.end_date <= '{filters.get('to_date')}'"

    record_filters = [
        ["start_date", "<=", filters.to_date],
        ["end_date", ">=", filters.from_date],
    ]
    if not filters.get("include_draft_timesheets"):
        record_filters.append(["docstatus", "=", 1])
    else:
        record_filters.append(["docstatus", "!=", 2])
    if filters.get('project'):
        record_filters.append(["parent_project", "=", str(filters.get('project'))])
    if filters.get('employee'):
        record_filters.append(["employee", "=", filters.get('employee')])
    timesheets = frappe.get_all(
        "Timesheet", filters=record_filters, fields=["employee", "employee_name", "name" , "parent_project"]
    )

    timesheets_map = {}
    timesheets_list = []
    for row in timesheets:
        timesheets_map[row.name] = row
        timesheets_list.append(row.name)

    if not timesheets_list:
        return []
    condition = ''
    condition += "parent in {} ".format(
                "(" + ", ".join([f'"{l}"' for l in timesheets_list]) + ")")
    if filters.get('project'):
        condition += f"and project = '{filters.get('project')}'"

    timesheet_detail = frappe.db.sql(f"""Select parent , project , billing_hours  , from_time , to_time , hours , billing_rate, is_billable,
                                     activity_type , task 
                                  From `tabTimesheet Detail` 
                                  Where {condition}""",as_dict = 1)

 
    for row in timesheet_detail:
        if timesheets_map.get(row.parent):
            row.update(timesheets_map.get(row.parent))
    
    from itertools import groupby
    
    def key_func(k):
        return k['name']
   
    INFO = sorted(timesheet_detail, key=key_func)
    
    
    for key, value in groupby(INFO, key_func):
        total_hours = 0
        total_billing_hours = 0
        total_amount = 0

        for row in list(value):

            from_time, to_time = filters.from_date, filters.to_date

            if str(row.to_time) < from_time or str(row.from_time) > to_time:
                continue

            if str(row.from_time) > from_time:
                from_time = row.from_time

            if str(row.to_time) < to_time:
                to_time = row.to_time

            activity_duration, billing_duration = get_billable_and_total_duration(row, from_time, to_time)
            
            if not filters.get('show_timesheet_detail'):
                total_hours += activity_duration
                total_billing_hours += billing_duration
                total_amount += billing_duration * flt(row.billing_rate)
                
            if filters.get('show_timesheet_detail'):
                data.append({
                    "project": row.get('project'),
                    "employee": row.get('employee'),
                    "employee_name": row.get('employee_name'),
                    "timesheet": row.get('name'),
                    "total_billable_hours": billing_duration,
                    "total_hours": activity_duration,
                    "amount": billing_duration * flt(row.billing_rate),
                    "from_time":from_time,
                    "to_time":to_time,
                    "activity_type":row.activity_type,
                    "task":row.task
                })
                
        if total_hours:
            data.append(
                {
                    "project": row.get('project'),
                    "employee": row.get('employee'),
                    "employee_name": row.get('employee_name'),
                    "timesheet": row.get('name'),
                    "total_billable_hours": total_billing_hours,
                    "total_hours": total_hours,
                    "amount": total_amount,
                }
            )

    return data

def get_billable_and_total_duration(activity, start_time, end_time):
    precision = frappe.get_precision("Timesheet Detail", "hours")
    activity_duration = time_diff_in_hours(end_time, start_time)
    billing_duration = 0.0
    if activity.is_billable:
        billing_duration = activity.billing_hours
        if activity_duration != activity.billing_hours:
            billing_duration = activity_duration * activity.billing_hours / activity.hours
    return flt(activity_duration, precision), flt(billing_duration, precision)