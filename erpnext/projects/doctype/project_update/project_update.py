# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class ProjectUpdate(Document):
    pass

@frappe.whitelist()
def daily_reminder():
    project = frappe.db.sql("""SELECT `tabProject`.project_name,`tabProject`.frequency,`tabProject`.expected_start_date,`tabProject`.expected_end_date,`tabProject`.percent_complete FROM `tabProject`;""")
    for projects in project:
        project_name = projects[0]
        frequency = projects[1]
        date_start = projects[2]
        date_end = projects [3]
        progress = projects [4]
        draft = frappe.db.sql("""SELECT count(docstatus) from `tabProject Update` WHERE `tabProject Update`.project = %s AND `tabProject Update`.docstatus = 0;""",project_name)
        for drafts in draft:
            number_of_drafts = drafts[0]
        update = frappe.db.sql("""SELECT name,date,time,progress,progress_details FROM `tabProject Update` WHERE `tabProject Update`.project = %s AND date = DATE_ADD(CURDATE(), INTERVAL -1 DAY);""",project_name)
        email_sending(project_name,frequency,date_start,date_end,progress,number_of_drafts,update)

def email_sending(project_name,frequency,date_start,date_end,progress,number_of_drafts,update):

    holiday = frappe.db.sql("""SELECT holiday_date FROM `tabHoliday` where holiday_date = CURDATE();""")
    msg = "<p>Project Name: " + project_name + "</p><p>Frequency: " + " " + frequency + "</p><p>Update Reminder:" + " " + str(date_start) + "</p><p>Expected Date End:" + " " + str(date_end) + "</p><p>Percent Progress:" + " " + str(progress) + "</p><p>Number of Updates:" + " " + str(len(update)) + "</p>" + "</p><p>Number of drafts:" + " " + str(number_of_drafts) + "</p>"
    msg += """</u></b></p><table class='table table-bordered'><tr>
                <th>Project ID</th><th>Date Updated</th><th>Time Updated</th><th>Project Status</th><th>Notes</th>"""
    for updates in update:
        msg += "<tr><td>" + str(updates[0]) + "</td><td>" + str(updates[1]) + "</td><td>" + str(updates[2]) + "</td><td>" + str(updates[3]) + "</td>" + "</td><td>" + str(updates[4]) + "</td></tr>"

    msg += "</table>"
    if len(holiday) == 0:
        email = frappe.db.sql("""SELECT user from `tabProject User` WHERE parent = %s;""", project_name)
        for emails in email:
            frappe.sendmail(recipients=emails,subject=frappe._(project_name + ' ' + 'Summary'),message = msg)
    else:
    	pass