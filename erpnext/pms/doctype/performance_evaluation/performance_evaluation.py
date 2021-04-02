# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
# developed by Birendra on 01/03/2021

from __future__ import unicode_literals
from frappe import _
import frappe
from frappe.model.document import Document
from frappe.utils import flt

class PerformanceEvaluation(Document):
    def validate(self):
        self.check_duplicate_entry()
        self.check_target()
        self.validate_rating()
        self.state_workflow()
        self.calculate_final_score()

    def on_submit(self):
        self.validate_calendar()
    
    def state_workflow(self):
        if self.workflow_state == "Approved" or self.workflow_state == "Rejected":
            # user_id = frappe.db.get_value('Employee', {'employee':self.supervisor_id}, ['user_id'])
            if frappe.session.user != self.approver :
                frappe.throw("<b>{}</b> can only Approve/Reject this document".format(self.approver_name))

    def calculate_final_score(self):
        part_a = 0
        part_b = 0

        weightage_for_target, weightage_for_competency = frappe.db.get_value('PMS Group', {'name':self.pms_group}, ['weightage_for_target', 'weightage_for_competency'])
        
        if weightage_for_target:
            part_a = flt(self.a_sup_rating_total) / flt(self.a_total_weightage ) * 100
            part_a = flt(part_a) / 100 * flt(weightage_for_target)
            self.part_a_score = part_a

        if weightage_for_competency:
            part_b = flt(self.b_sup_rating_total) / flt(self.b_total_weightage) * 100
            part_b = flt(part_b) / 100 * flt(weightage_for_competency)
            self.part_b_score = part_b
        
        self.final_score = self.part_a_score + self.part_b_score
        
        self.overall_rating = frappe.db.get_value('Overall Rating', {'lower_range':('<=',self.final_score),'upper_range':('>=',self.final_score)}, 'name')
        
    def check_target(self):
        # validate target
        if self.required_to_set_target:
            if not self.evaluate_target_item:
                frappe.throw(_('You need to <b>Get The Target</b>'))
        if not self.evaluate_competency_item:
            frappe.throw(_('You need to <b>Get The Competency</b>'))
            
    def validate_rating(self):
        # make sure rating should not excess weightage
        a_total_weightage = 0
        supervisor_rating_total = 0
        # target total score
        
        for i, v in enumerate(self.evaluate_target_item):
            if v.self_rating > v.weightage :
                frappe.throw("Rating for <b>Target</b> cannot be greater than weightage at Row <b>{}</b>".format(i+1))
            if v.self_rating <= 0:
                frappe.throw("Self Rating for <b>Target</b> cannot be less than or equal to <b>0</b> at Row <b>{}</b>".format(i+1))
            if  v.supervisor_rating <= 0 and frappe.session.user == self.approver:
                frappe.throw("Supervisor Rating for <b>Target</b> cannot be less than or equal to <b>0</b> at Row <b>{}</b>".format(i+1))
                
            a_total_weightage += v.weightage
            supervisor_rating_total += v.supervisor_rating
        self.a_total_weightage = a_total_weightage
        s_total_weightage = 0
        sup_rating_total = 0
        # achievement total add along with target total
        for k, a in enumerate(self.achievements_items):
            if a.self_rating > a.weightage or a.supervisor_rating > a.weightage:
                frappe.throw("Rating for <b>Achievement</b> cannot be greater than weightage at Row <b>{}</b>".format(k+1))
            if a.self_rating <= 0 :
                frappe.throw("Rating for <b>Achievement</b> cannot be less than or equal to <b>0</b> at Row <b>{}</b>".format(k+1))
            if  a.supervisor_rating <= 0 and frappe.session.user == self.approver:
                frappe.throw("Supervisor Rating for <b>Achievement</b> cannot be less than or equal to <b>0</b> at Row <b>{}</b>".format(k+1))
                
            sup_rating_total += a.supervisor_rating
    
        self.a_sup_rating_total = supervisor_rating_total + sup_rating_total

        b_total_weightage = 0
        b_sup_rating_total = 0
        # competency total
        for j, c in enumerate(self.evaluate_competency_item):
            if c.self_rating > c.weightage or c.supervisor_rating > c.weightage:
                frappe.throw("Rating for <b>Competency</b> cannot be greater than weightage at Row <b>{}</b>".format(j+1))
            if c.self_rating <= 0 :
                frappe.throw("Rating for <b>Competency</b> cannot be less than or equal to <b>0</b> at Row <b>{}</b>".format(j+1))
            if  c.supervisor_rating <= 0 and frappe.session.user == self.approver:
                frappe.throw("Supervisor Rating for <b>Competency</b> cannot be less than or equal to <b>0</b> at Row <b>{}</b>".format(j+1))
                
            b_total_weightage += c.weightage
            b_sup_rating_total += c.supervisor_rating
            
        self.b_total_weightage = b_total_weightage
        self.b_sup_rating_total = b_sup_rating_total

    def validate_calendar(self):
        # check whether pms is active for target setup
        if not frappe.db.exists("PMS Calendar", {"name": self.pms_calendar, "docstatus": 1, "evaluation_start_date": ("<=", self.date), "evaluation_end_date": (">=", self.date)}):
            frappe.throw(
                _('Evaluation for PMS Calendar <b>{}</b> is not open').format(self.pms_calendar))

    def check_duplicate_entry(self):
        # check duplicate entry for particular employee
        if frappe.db.exists("Performance Evaluation", {'employee': self.employee, 'pms_calendar': self.pms_calendar, 'docstatus': 1}):
            frappe.throw(
                _('You have already evaluated the current Fiscal Year PMS <b>{}</b>'.format(self.pms_calendar)))

    def get_target(self):
        data = frappe.db.sql("""
			SELECT 
			    rti.performance_target,
                rti.quality,
                rti.quantity,
                rti.timeline,
                rti.weightage,
                rti.background,
                rti.appraisees_remarks,
                rti.appraisers_remark
			FROM 
				`tabReview` r 
			INNER JOIN
			    `tabReview Target Item` rti
			ON
			     r.name =  rti.parent			
			WHERE			
				r.employee = '{}' 
            AND
                r.docstatus = 1 
            AND 
                r.pms_calendar = '{}'""".format(self.employee, self.pms_calendar), as_dict=True)
        if not data:
            frappe.throw(_('There are no Targets defined for Your ID <b>{}</b>'.format(self.employee)))
        self.set('evaluate_target_item', [])
        for d in data:
            row = self.append('evaluate_target_item', {})
            row.update(d)

    def get_competency(self):
        data = frappe.db.sql("""
		SELECT
			rci.competency,
			rci.weightage,
            rci.appraisees_remark,
            rci.appraisers_remark
		FROM
			`tabReview` r
		INNER JOIN
			`tabReview Competency Item` rci
		ON
			r.name = rci.parent
		WHERE
			r.employee = '{}' 
        AND
            r.docstatus = 1
		AND
			r.pms_calendar = '{}'
		ORDER BY
			rci.competency""".format(self.employee, self.pms_calendar), as_dict=True)
        if not data:
            frappe.throw(_('There are no Competencies defined for Your ID <b>{}</b>'.format(self.employee)))

        self.set('evaluate_competency_item', [])
        for d in data:
            row = self.append('evaluate_competency_item', {})
            row.update(d)

    def get_additional_achievements(self):
        data = frappe.db.sql("""
            SELECT 
                aa.additional_achievements,
                aa.weightage,
                aa.appraisees_remarks,
                aa.own_initiativedirected,
                aa.appraisers_remarks
            FROM 
                `tabReview` r 
            INNER JOIN
                `tabAdditional Achievements` aa
            ON 
                r.name = aa.parent 
            WHERE
			    r.employee = '{}' 
            AND
                r.docstatus = 1
            AND
                r.pms_calendar = '{}'
            """.format(self.employee, self.pms_calendar), as_dict=True)
        if data:
            self.set('achievements_items', [])
            for d in data:
                row = self.append('achievements_items', {})
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
		`tabPerformance Evaluation`.owner = '{user}'
		or
		exists(select 1
				from `tabEmployee`
				where `tabEmployee`.name = `tabPerformance Evaluation`.employee
				and `tabEmployee`.user_id = '{user}')
		or
		(`tabPerformance Evaluation`.approver = '{user}' and `tabPerformance Evaluation`.workflow_state not in ('Draft', 'Rejected'))
	)""".format(user=user)