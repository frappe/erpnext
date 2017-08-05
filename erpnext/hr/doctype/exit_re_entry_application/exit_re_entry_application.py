# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class ExitReEntryApplication(Document):
	pass
	# def on_submit(self):
	# 	leave=frappe.get_doc("Leave Application",self.application_requested)
	# 	mng=frappe.db.sql("select name from tabEmployee where user_id in(select name from tabUser where name in(select parent from tabUserRole where role='Ticket Approver'))")
	# 	if mng:
	# 		manag=frappe.get_doc("Employee",mng[0][0])

	# 	if self.docstatus==1 and leave.ticket==1:
	# 		family_info= leave.get("ticket_family_members")
	# 		ticreq= frappe.get_doc({
	# 			"doctype":"Ticket Request",
	# 			"employee": leave.employee,
	# 			"application_type": "Leave Application",
	# 			"application_requested": leave.name
	# 			}).insert(ignore_permissions=True)
	# 		if family_info:
	# 			ticreq.set("family_members",family_info)
	# 			ticreq.save()


	# 		frappe.db.sql("update `tabLeave Application` set workflow_state='Approved By GR Supervisor',next_stage='Approved By Ticket Approver',approval_manager='{0}' where name='{1}'".format(manag.employee_name,self.application_requested))
		
	# 	elif self.docstatus==1:
	# 		frappe.db.sql("update `tabLeave Application` set workflow_state='Approved By GR Supervisor',next_stage='--',approval_manager='--' where name='{0}'".format(self.application_requested))

