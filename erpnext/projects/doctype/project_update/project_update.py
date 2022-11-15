# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class ProjectUpdate(Document):
    pass

@frappe.whitelist()
def daily_reminder():
    projects = frappe.get_all("Project",
        ["name", "project_name", "frequency", "expected_start_date", "expected_end_date", "percent_complete"])
    for project in projects:
        draft = frappe.db.sql("""
            SELECT count(docstatus)
            FROM `tabProject Update`
            WHERE project = %s AND docstatus = 0
        """, project.name)
        number_of_drafts = draft[0][0] if draft else 0

        update = frappe.db.sql("""
            SELECT name, date, time, progress, progress_details
            FROM `tabProject Update`
            WHERE project = %s AND date = DATE_ADD(CURDATE(), INTERVAL -1 DAY)
        """, project.name)

        email_sending(project.name, project.project_name or project.name, project.frequency,
            project.expected_date_start, project.expected_end_date,
            project.percent_complete, number_of_drafts, update)

def email_sending(project, project_name,frequency,date_start,date_end,progress,number_of_drafts,update):

    holiday = frappe.db.sql("""SELECT holiday_date FROM `tabHoliday` where holiday_date = CURDATE();""")
    msg = "<p>Project Name: " + project_name + "</p><p>Frequency: " + " " + frequency + "</p><p>Update Reminder:" + " " + str(date_start) + "</p><p>Expected Date End:" + " " + str(date_end) + "</p><p>Percent Progress:" + " " + str(progress) + "</p><p>Number of Updates:" + " " + str(len(update)) + "</p>" + "</p><p>Number of drafts:" + " " + str(number_of_drafts) + "</p>"
    msg += """</u></b></p><table class='table table-bordered'><tr>
                <th>Project ID</th><th>Date Updated</th><th>Time Updated</th><th>Project Status</th><th>Notes</th>"""
    for updates in update:
        msg += "<tr><td>" + str(updates[0]) + "</td><td>" + str(updates[1]) + "</td><td>" + str(updates[2]) + "</td><td>" + str(updates[3]) + "</td>" + "</td><td>" + str(updates[4]) + "</td></tr>"

    msg += "</table>"
    if len(holiday) == 0:
        email = frappe.db.sql("""SELECT user from `tabProject User` WHERE parent = %s;""", project)
        for emails in email:
            frappe.sendmail(recipients=emails,subject=frappe._(project_name + ' ' + 'Summary'),message = msg)
    else:
        pass
