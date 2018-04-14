# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import flt, getdate

from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.model.document import Document
from erpnext.hr.utils import set_employee_name

class Appraisal(Document):
    def validate(self):
        if not self.status:
            self.status = "Draft"
        if hasattr(self,"workflow_state"):
            if self.workflow_state:
                if "Rejected" in self.workflow_state:
                    self.docstatus = 1
                    self.docstatus = 2

        set_employee_name(self)
        self.validate_dates()
        self.validate_existing_appraisal()
        self.calculate_total()
        self.validate_emp()


    def validate_emp(self):
        if self.employee:
            employee_user = frappe.get_value("Employee", filters={"name": self.employee}, fieldname="user_id")
            if self.get('__islocal') and employee_user:
                if u'CEO' in frappe.get_roles(employee_user):
                    self.workflow_state = "Created By CEO"
                elif u'Director' in frappe.get_roles(employee_user):
                    self.workflow_state = "Created By Director"
                elif u'Manager' in frappe.get_roles(employee_user):
                    self.workflow_state = "Created By Manager"
                elif u'Line Manager' in frappe.get_roles(employee_user):
                    self.workflow_state = "Created By Line Manager"
                elif u'Employee' in frappe.get_roles(employee_user):
                    self.workflow_state = "Pending"

            if not employee_user and self.get('__islocal'):
                self.workflow_state = "Pending"

    def get_employee_name(self):
        self.employee_name = frappe.db.get_value("Employee", self.employee, "employee_name")
        return self.employee_name

    def validate_dates(self):
        if getdate(self.start_date) > getdate(self.end_date):
            frappe.throw(_("End Date can not be less than Start Date"))

    def validate_existing_appraisal(self):
        chk = frappe.db.sql("""select name from `tabAppraisal` where employee=%s
            and (status='Submitted' or status='Completed')
            and ((start_date>=%s and start_date<=%s)
            or (end_date>=%s and end_date<=%s))""",
            (self.employee,self.start_date,self.end_date,self.start_date,self.end_date))
        if chk:
            frappe.throw(_("Appraisal {0} created for Employee {1} in the given date range").format(chk[0][0], self.employee_name))

    def calculate_total(self):
        total, total_w  = 0, 0
        for d in self.get('goals'):
            if d.score:
                d.score_earned = flt(d.score)
                # d.score_earned = flt(d.score) * flt(d.per_weightage) * 2 / 100
                total = total + d.score_earned
            total_w += flt(d.per_weightage)

        for d in self.get('quality_of_work_goals'):
            if d.score:
                d.score_earned = flt(d.score)
                # d.score_earned = flt(d.score) * flt(d.per_weightage) * 2 / 100
                total = total + d.score_earned
            total_w += flt(d.per_weightage)

        for d in self.get('work_habits_goals'):
            if d.score:
                d.score_earned = flt(d.score)
                # d.score_earned = flt(d.score) * flt(d.per_weightage) * 2 / 100
                total = total + d.score_earned
            total_w += flt(d.per_weightage)

        for d in self.get('job_knowledge_goals'):
            if d.score:
                d.score_earned = flt(d.score)
                # d.score_earned = flt(d.score) * flt(d.per_weightage) * 2 / 100
                total = total + d.score_earned
            total_w += flt(d.per_weightage)

        for d in self.get('interpersonal_relations_goals'):
            if d.score:
                d.score_earned = flt(d.score)
                # d.score_earned = flt(d.score) * flt(d.per_weightage) * 2 / 100
                total = total + d.score_earned
            total_w += flt(d.per_weightage)

        for d in self.get('leadership_goals'):
            if d.score:
                d.score_earned = flt(d.score)
                # d.score_earned = flt(d.score) * flt(d.per_weightage) * 2 / 100
                total = total + d.score_earned
            total_w += flt(d.per_weightage)

        if int(total_w) != 100:
            frappe.throw(_("Total weightage assigned should be 100%. It is {0}").format(str(total_w) + "%"))

        if frappe.db.get_value("Employee", self.employee, "user_id") != \
                frappe.session.user and total == 0:
            frappe.throw(_("Total cannot be zero"))

        self.total_score = total


        if self.total_score >= 95 and self.total_score <= 100 :
            self.attribute = "Outstanding"
        elif self.total_score >= 90 and self.total_score <= 94 :
            self.attribute = "Exceeds Requirements"
        elif self.total_score >= 80 and self.total_score <= 89 :
            self.attribute = "Meets Requirements"
        elif self.total_score >= 70 and self.total_score <= 79 :
            self.attribute = "Need Improvement"
        elif self.total_score >= 0 and self.total_score <= 69 :
            self.attribute = "Unsatisfactory"
        

    def on_submit(self):
        frappe.db.set(self, 'status', 'Submitted')

    def on_cancel(self):
        frappe.db.set(self, 'status', 'Cancelled')

@frappe.whitelist()
def fetch_appraisal_template(source_name, target_doc=None):
    target_doc = get_mapped_doc("Appraisal Template", source_name, {
        "Appraisal Template": {
            "doctype": "Appraisal",
        },
        "Appraisal Template Goal": {
            "doctype": "Appraisal Goal",
        }
    }, target_doc)


    target_doc = get_mapped_doc("Appraisal Template", source_name, {
        "Appraisal Template": {
            "doctype": "Appraisal",
        },
        "Appraisal Template Goal Quality of Work": {
            "doctype": "Appraisal Goal Quality of Work",
        }
    }, target_doc)


    target_doc = get_mapped_doc("Appraisal Template", source_name, {
        "Appraisal Template": {
            "doctype": "Appraisal",
        },
        "Appraisal Template Goal Work Habits": {
            "doctype": "Appraisal Goal Work Habits",
        }
    }, target_doc)


    target_doc = get_mapped_doc("Appraisal Template", source_name, {
        "Appraisal Template": {
            "doctype": "Appraisal",
        },
        "Appraisal Template Goal Job Knowledge": {
            "doctype": "Appraisal Goal Job Knowledge",
        }
    }, target_doc)


    target_doc = get_mapped_doc("Appraisal Template", source_name, {
        "Appraisal Template": {
            "doctype": "Appraisal",
        },
        "Appraisal Template Goal Interpersonal relations": {
            "doctype": "Appraisal Goal Interpersonal relations",
        }
    }, target_doc)


    target_doc = get_mapped_doc("Appraisal Template", source_name, {
        "Appraisal Template": {
            "doctype": "Appraisal",
        },
        "Appraisal Template Goal Leadership": {
            "doctype": "Appraisal Goal Leadership",
        }
    }, target_doc)

    return target_doc

