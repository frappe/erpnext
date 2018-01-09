# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class BusinessTripExceptionalApproval(Document):
    def validate(self):
        if hasattr(self,"workflow_state"):
            if self.workflow_state:
                if "Rejected" in self.workflow_state:
                    self.docstatus = 1
                    self.docstatus = 2


    def on_submit(self):
        employee = frappe.get_doc('Employee', {'name': self.employee})
        if employee:
            if self.status=='Pending':
                frappe.throw(_("Please change the status before sumbit"))
            else:
                if self.status =="Approved":
                    # state = 'Approved By Employee'
                    if u'CEO' in frappe.get_roles(employee.user_id):
                        state = "Approved By CEO"
                    elif u'Director' in frappe.get_roles(employee.user_id) and self.days<4:
                        state = "Approve By Director"
                    elif u'Director' in frappe.get_roles(employee.user_id) and self.days>4:
                        state = "Approved By Director"
                    elif u'Manager' in frappe.get_roles(employee.user_id):
                        state = "Approved by Manager"
                    elif u'Line Manager' in frappe.get_roles(employee.user_id):
                        state = "Approved By Line Manager"
                    elif u'Employee' in frappe.get_roles(employee.user_id):
                        state = "Approved By Employee"
                else:
                    state = 'Rejected By Employee'

                doc = frappe.get_doc('Business Trip', self.business_trip )
                doc.workflow_state = state
                doc.save(ignore_permissions=True)
    

    def get_user_id(self,employee):
        session_user = frappe.session.user
        cur_user=frappe.db.sql("select user_id from `tabEmployee` where name='{0}'".format(employee))
        if cur_user:
            return session_user,cur_user[0][0]