# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, json

from frappe.utils import getdate, today
from frappe.model import db_exists
from frappe.model.bean import copy_doclist
from frappe import msgprint


class DocType:
	def __init__(self,doc,doclist=[]):
		self.doc = doc
		self.doclist = doclist
	
	def get_project_details(self):
		return {
			"project": self.doc.project
		}
		
	def get_customer_details(self):
		cust = frappe.conn.sql("select customer_name from `tabCustomer` where name=%s", self.doc.customer)
		if cust:
			ret = {'customer_name': cust and cust[0][0] or ''}
			return ret
	
	def validate(self):
		if self.doc.exp_start_date and self.doc.exp_end_date and getdate(self.doc.exp_start_date) > getdate(self.doc.exp_end_date):
			msgprint("'Expected Start Date' can not be greater than 'Expected End Date'")
			raise Exception
		
		if self.doc.act_start_date and self.doc.act_end_date and getdate(self.doc.act_start_date) > getdate(self.doc.act_end_date):
			msgprint("'Actual Start Date' can not be greater than 'Actual End Date'")
			raise Exception
			
		self.update_status()

	def update_status(self):
		status = frappe.conn.get_value("Task", self.doc.name, "status")
		if self.doc.status=="Working" and status !="Working" and not self.doc.act_start_date:
			self.doc.act_start_date = today()
			
		if self.doc.status=="Closed" and status != "Closed" and not self.doc.act_end_date:
			self.doc.act_end_date = today()
			
	def on_update(self):
		"""update percent complete in project"""
		if self.doc.project:
			project = frappe.bean("Project", self.doc.project)
			project.run_method("update_percent_complete")

@frappe.whitelist()
def get_events(start, end, filters=None):
	from frappe.widgets.reportview import build_match_conditions
	if not frappe.has_permission("Task"):
		frappe.msgprint(_("No Permission"), raise_exception=1)

	conditions = build_match_conditions("Task")
	conditions and (" and " + conditions) or ""
	
	if filters:
		filters = json.loads(filters)
		for key in filters:
			if filters[key]:
				conditions += " and " + key + ' = "' + filters[key].replace('"', '\"') + '"'
	
	data = frappe.conn.sql("""select name, exp_start_date, exp_end_date, 
		subject, status, project from `tabTask`
		where ((exp_start_date between '%(start)s' and '%(end)s') \
			or (exp_end_date between '%(start)s' and '%(end)s'))
		%(conditions)s""" % {
			"start": start,
			"end": end,
			"conditions": conditions
		}, as_dict=True, update={"allDay": 0})

	return data

def get_project(doctype, txt, searchfield, start, page_len, filters):
	from erpnext.controllers.queries import get_match_cond
	return frappe.conn.sql(""" select name from `tabProject`
			where %(key)s like "%(txt)s"
				%(mcond)s
			order by name 
			limit %(start)s, %(page_len)s """ % {'key': searchfield, 
			'txt': "%%%s%%" % txt, 'mcond':get_match_cond(doctype, searchfield),
			'start': start, 'page_len': page_len})