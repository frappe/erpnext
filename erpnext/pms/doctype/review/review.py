# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
# developed by Birendra on 15/02/2021

from __future__ import unicode_literals
from frappe import _
import frappe
from frappe.model.document import Document

class Review(Document):
    def validate(self):
        self.check_duplicate_entry()
        self.check_target()
        self.state_workflow()

    def on_submit(self):
        self.validate_calendar()
    
    def state_workflow(self):
        if self.workflow_state == "Approved" or self.workflow_state == "Rejected":
            if frappe.session.user != self.approver:
                frappe.throw("<b>{}</b> can only Approve/Reject this document".format(self.approver_name))
    
    def validate_calendar(self):
        # check whether pms is active for target setup
        if not frappe.db.exists("PMS Calendar",{"name": self.pms_calendar,"docstatus": 1,
                    "review_start_date":("<=",self.date),"review_end_date":(">=",self.date)}):
            frappe.throw(_('Review for PMS Calendar <b>{}</b> is not open').format(self.pms_calendar))

    def check_duplicate_entry(self):
        # check duplicate entry for particular employee
        if frappe.db.exists("Review", {'employee': self.employee, 'pms_calendar': self.pms_calendar, 'docstatus': 1}):
            frappe.throw(_('You have already reviewed the current Fiscal Year PMS <b>{}</b>'.format(self.pms_calendar)))

    def check_target(self):
        # validate target
        if self.required_to_set_target:
            if not self.review_target_item:
                frappe.throw(_('You need to <b>Get The Target</b>'))
        if not self.review_competency_item:
            frappe.throw(_('You need to <b>Get The Competency</b>'))
            
    def get_target(self):
        # get Target
        data = frappe.db.sql("""
			SELECT 
				pte.performance_target,
                pte.quality,
                pte.quantity,
                pte.timeline,
                pte.weightage,
                pte.background
			FROM 
				`tabTarget Set Up` ts 
			INNER JOIN
			    `tabPerformance Target Evaluation` pte
			ON
			     ts.name = pte.parent			
			WHERE			
				ts.employee = '{}' 
            AND
                ts.docstatus = 1 
            AND 
                ts.pms_calendar = '{}' 
		""".format(self.employee,self.pms_calendar), as_dict=True)

        if not data:
            frappe.throw(_('There are no Targets defined for Your ID <b>{}</b>'.format(self.employee)))

        self.set('review_target_item', [])
        for d in data:
            row = self.append('review_target_item', {'parentfield':self.name})
            row.update(d)

    def get_competency(self):
        data = frappe.db.sql("""
			SELECT 
				pte.competency,
                pte.weightage
			FROM 
				`tabTarget Set Up` ts 
			INNER JOIN
			    `tabCompetency Item` pte
			ON
			     ts.name = pte.parent 		
			WHERE			
				ts.employee = '{}' and ts.docstatus = 1 
            AND 
                ts.pms_calendar = '{}' 
            ORDER BY 
                pte.competency
		""".format(self.employee,self.pms_calendar), as_dict=True)
        if not data:
            frappe.throw(_('There are no Competency defined for your ID <b>{}</b>'.format(self.employee)))

        self.set('review_competency_item', [])
        for d in data:
            row = self.append('review_competency_item', {'parentfield':self.name})
            # row.competency = d.competency
            row.update(d)
        # return data
        
def get_permission_query_conditions(user):
    # restrick user from accessing this doctype
	if not user: user = frappe.session.user
	user_roles = frappe.get_roles(user)

	if user == "Administrator":
		return
	if "HR User" in user_roles or "HR Manager" in user_roles:
		return

	return """(
		`tabReview`.owner = '{user}'
		or
		exists(select 1
				from `tabEmployee`
				where `tabEmployee`.name = `tabReview`.employee
				and `tabEmployee`.user_id = '{user}')
		or
		(`tabReview`.approver = '{user}' and `tabReview`.workflow_state not in ('Draft', 'Rejected'))
	)""".format(user=user)