# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import datetime

class ProjectUpdate(Document):
    pass

@frappe.whitelist()
def current_day_time(doc,method):
    doc.date = frappe.utils.today()
    doc.time = frappe.utils.now_datetime().strftime('%H:%M:%S')
#pending code
# @frappe.whitelist()
# def add_communication(doc,method):
#
#     data = []
#     add_communication = frappe.db.sql("""SELECT `tabProject User`.user,`tabProject Update`.name,`tabProject Update`.progress FROM `tabProject User` INNER JOIN `tabProject Update` ON `tabProject Update`.project = `tabProject User`.parent WHERE `tabProject Update`.project = %s""",doc.project)
#     for ac in add_communication:
#         email = ac[0]
#         name = ac[1]
#         progress = ac[2]
#     data.append(email)
#     print(data)
#     if len(data)>0:
#         for datas in data:
#             print datas
#             frappe.sendmail(
#                 recipients=datas,
#                 subject=frappe._(name),
#                 header=[frappe._("Project Update Status"), 'blue'],
#                 message="Progress: " + progress
#             )
#         doc = frappe.get_doc({
#             "doctype": "Communication",
#             "subject": name,
#             "reference_doctype": "Project Update",
#             "comment_type": "Created"
#         })
#         doc.insert()
#         doc.save()
#     else:
#         pass

@frappe.whitelist()
def daily_reminder():
    name_project = frappe.db.sql("""SELECT name FROM `tabProject`""")
    for name_projects in name_project:
        data_project =  frappe.db.sql("""SELECT `tabProject`.project_name,`tabProject`.frequency,`tabProject`.expected_start_date,`tabProject`.expected_end_date,`tabProject`.percent_complete FROM `tabProject` WHERE `tabProject`.project_name = %s """,name_projects)
        for datas in data_project:
            project_name = datas[0]
            frequency = datas[1]
            date_start = datas[2]
            date_end = datas [3]
            progress = datas [4]
            update = frappe.db.sql("""SELECT name,date,time,progress FROM `tabProject Update` WHERE `tabProject Update`.project = %s""",project_name)
        email_sending(project_name,frequency,date_start,date_end,progress,update)

def email_sending( project_name,frequency,date_start,date_end,progress,update):
    date_start = date_start.strftime("%Y-%m-%d")
    date_end = date_end.strftime("%Y-%m-%d")

    holiday = frappe.db.sql("""SELECT holiday_date FROM `tabHoliday` where holiday_date = CURDATE();""")
    msg = "<p>Project Name:" + " " + project_name + "</p><p>Project Name: " + " " + frequency + "</p><p>Update Reminder:" + " " + date_start + "</p><p>Expected Date End:" + " " + date_end + "</p><p>Percent Progress:" + " " + str(progress) + "</p><p>Number of Updates:" + " " + str(len(update)) + "</p>"
    msg += """</u></b></p><table class='table table-bordered'><tr>
                <th>Project ID</th><th>Date Updated</th><th>Time Updated</th><th>Project Status</th>"""
    for updates in update:
        msg += "<tr><td>" + str(updates[0]) + "</td><td>" + str(updates[1]) + "</td><td>" + str(updates[2]) + "</td><td>" + str(updates[3]) + "</td></tr>"

    msg += "</table>"
    if len(holiday) == 0:
        email = frappe.db.sql("""SELECT user from `tabProject User` WHERE parent = %s;""", project_name)
    	for emails in email:
    		frappe.sendmail(recipients=emails,subject=frappe._(project_name + ' ' + 'Summary'),message = msg)
    else:
    	pass

