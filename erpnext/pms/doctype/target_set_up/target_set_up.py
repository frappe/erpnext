# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
# developed by Birendra on 01/02/2021
from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

class TargetSetUp(Document):
    def validate(self):
        self.check_target()
        self.check_duplicate_entry()
        self.state_workflow()
        
    def on_submit(self):
        self.validate_calendar()

    def state_workflow(self):
        if self.workflow_state == "Approved" or self.workflow_state == "Rejected":
            if frappe.session.user != self.approver :
                # frappe.msgprint(format(frappe.session.user))
                frappe.throw("<b>{}</b> can only Approve/Reject this document".format(self.approver_name))
        
        if self.workflow_state == "Waiting Approval":
            if frappe.session.user == self.approver :
                frappe.throw("<b>{}</b> can only Apply this document".format(self.employee_name))
    
    # def get_supervisor_user_id(self):
    #     # get supervisor user id
    #     supervisor_user_id = frappe.db.get_value('Employee', {'employee':self.supervisor_id}, ['user_id'])
    #     self.sup_user_id = supervisor_user_id
        
    def validate_calendar(self):
        # check whether pms is active for target setup
        if not frappe.db.exists("PMS Calendar",{"name": self.pms_calendar,"docstatus": 1,
                    "target_start_date":("<=",self.date),"target_end_date":(">=",self.date)}):
            frappe.throw(_('Target Set Up for PMS Calendar <b>{}</b> is not open').format(self.pms_calendar))

    def check_duplicate_entry(self):
        # check duplicate entry for particular employee
        if frappe.db.exists("Target Set Up", {'employee': self.employee, 'pms_calendar': self.pms_calendar, 'docstatus': 1}):
            frappe.throw(_('You have already set the Target for PMS Calendar <b>{}</b>'.format(self.pms_calendar)))

    def check_target(self):
        # validate target
        if frappe.db.exists("PMS Group",{"group_name":self.pms_group,"required_to_set_target":1}):
            if not self.target_item:
                frappe.throw(_('You need to <b>Set The Target</b>'))
            total_target_weightage = 0
            # total weightage must be 100
            for i, t in enumerate(self.target_item):
                if flt(t.quality) < 0 or flt(t.quantity) < 0 or flt(t.weightage) < 0:
                    frappe.throw(_("Negative value is not allowed in Target Item at Row {}".format(i+1)))
                total_target_weightage += flt(t.weightage)

            if flt(total_target_weightage) != 100:
                frappe.throw(_('<b>Sum of Weightage in Target Item must be 100</b>'))

        if not self.competency:
            frappe.throw(_('Competency cannot be empty'))

    def get_competency(self):
        # fetch employee category based on employee designation
        employee_category = frappe.db.sql("""
				SELECT 
					ec.employee_category 
				FROM 
					`tabEmployee Category` ec 
				INNER JOIN 
					`tabEmployee Category Group` ecg
				ON 
					ec.name = ecg.parent 
				WHERE 
					ecg.designation = '{}'
		""".format(self.designation), as_dict=True)
        if not employee_category:
            frappe.throw(
                _('Your designation <b>{0}</b> is not defined in the Employee Category'.format(self.designation)))

        # get competency applicable to particular category
        data = frappe.db.sql("""
			SELECT 
				wc.competency,wc.weightage
			FROM 
				`tabWork Competency` wc 
			INNER JOIN
				`tabWork Competency Item` wci 
			ON 
				wc.name = wci.parent 
			WHERE	
				wci.applicable = 1 
			AND 
				wci.employee_category = '{0}' 
            ORDER BY 
                wc.competency
		""".format(employee_category[0].employee_category), as_dict=True)
        # frappe.msgprint(format(data))
        if not data:
            frappe.throw(_('There are no Work Competency defined'))
        # set competency item values
        self.set('competency', [])
        for d in data:
            row = self.append('competency', {})
            row.update(d)

def get_permission_query_conditions(user):
    # restrick user from accessing this doctype
	if not user: user = frappe.session.user
	user_roles = frappe.get_roles(user)

	if user == "Administrator":
		return
	if "HR User" in user_roles or "HR Manager" in user_roles:
		return

	return """(
		`tabTarget Set Up`.owner = '{user}'
		or
		exists(select 1
				from `tabEmployee`
				where `tabEmployee`.name = `tabTarget Set Up`.employee
				and `tabEmployee`.user_id = '{user}')
		or
		(`tabTarget Set Up`.approver = '{user}' and `tabTarget Set Up`.workflow_state not in ('Draft', 'Rejected'))
	)""".format(user=user)