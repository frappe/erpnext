# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class ProjectUpdate(Document):
	pass

@frappe.whitelist()
def current_day_time(doc,method):
	doc.date = frappe.utils.today()
	doc.time = frappe.utils.now_datetime().strftime('%H:%M:%S')


@frappe.whitelist()
def daily_reminder():
	data = []
	name = "Doctor Virtual"
	email =  frappe.db.sql("""SELECT `tabProject User`.user,`tabProject`.project_name,`tabProject`.frequency,`tabProject`.expected_start_date,`tabProject`.expected_end_date,`tabProject`.percent_complete FROM `tabProject User` INNER JOIN `tabProject` ON `tabProject`.project_name = `tabProject User`.parent WHERE `tabProject`.project_name = %s """,name)
	for emails in email:
		recipients = emails[0]
		project_name = emails[1]
		frequency = emails[2]
	data.append(recipients)
	update = frappe.db.sql("""SELECT name,time,progress FROM `tabProject Update` WHERE `tabProject Update`.project = %s""",project_name)
	email_sending(data, project_name,frequency,update)


def email_sending(data,project_name,frequency,update):
	holiday = frappe.db.sql("""SELECT holiday_date FROM `tabHoliday` where holiday_date = CURDATE();""")
	print _("Project Name: {0}".format(project_name))
	print _("Project Name: {0}".format(frequency))
	for updates in update:
		id = updates[0]
		time = updates[1]
		messages = (
			_("Project Name: {0}".format(project_name)),
			_("Update Reminder: {0}".format(frequency)),
			_("{0}".format(id)),
			_("{0}".format(update))
		)
	content = """
	<p>{0}.</p>
	<p>{1}</p>
	<table class="table table-bordered">
		<th>Project ID</th><th>Time Updated</th>
	{% for updates in update %}
	<tr>
		<td>{{updates[0]}}</td><td>{{updates[1]}}</td>
	</tr>
	{% endfor %}
	</table>
	<p>{3}</p>
	<hr>
	"""
	if len(holiday) == 0:
		for datas in data:
			frappe.sendmail(recipients=datas,subject=frappe._(project_name + ' ' + 'Summary'),content=content.format(*messages))
	else:
		pass