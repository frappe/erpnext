# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import msgprint, _
from erpnext.hr.doctype.end_of_service_award.end_of_service_award import get_award
from frappe.utils import cint, cstr, date_diff, flt, formatdate, getdate, get_link_to_form, \
    comma_or, get_fullname, add_years, add_months, add_days, nowdate, get_first_day, get_last_day

class EmployeeResignation(Document):

    def on_submit(self):
        emp = frappe.get_doc("Employee",self.employee)
        emp.status ="Left"
        emp.relieving_date =self.last_working_date
        emp.save(ignore_permissions=True)


        salary = self.get_salary()
        award_info = get_award(self.date_of_joining, self.last_working_date, salary,self.employment_type, "استقالة العامل")

        eos_award = frappe.new_doc("End of Service Award")
        eos_award.employee = self.employee
        eos_award.end_date = self.last_working_date
        eos_award.salary = salary
        eos_award.reason="استقالة العامل"
        eos_award.workflow_state="Pending"
        eos_award.days = award_info['days']
        eos_award.months = award_info['months']
        eos_award.years = award_info['years']
        eos_award.award = award_info['award']
        eos_award.insert()

    def get_salary(self):
        # award_info = get_award(self)
        # frappe.throw(str(award_info))
        start_date = get_first_day(getdate(nowdate()))
        end_date = get_last_day(getdate(nowdate()))
        doc = frappe.new_doc("Salary Slip")
        doc.salary_slip_based_on_timesheet="0"

        doc.payroll_frequency= "Monthly"
        doc.start_date= start_date
        doc.end_date= end_date
        doc.employee= self.employee
        doc.employee_name= self.employee_name
        doc.company= "Tawari"
        doc.posting_date= start_date
        
        doc.insert()


        grosspay =doc.gross_pay
        result=grosspay
        if result:
            return result
        else:
            frappe.throw("لا يوجد قسيمة راتب لهذا الموظف")
    
        

    def validate(self):

        if not self.last_working_date:
            frappe.throw("Please enter your last working date")

        if frappe.get_value('Employee Loan', filters={'employee' : self.employee,'status':'Sanctioned'}):
            name=frappe.get_value('Employee Loan', filters={'employee' : self.employee,'status':'Sanctioned'}) 
            loan_emp =frappe.get_doc("Employee Loan",name)      
            mm=loan_emp.status
            frappe.throw(self.employee+"/ "+self.employee_name+" have an active loan")

        self.validate_emp()
        if self.workflow_state:
            if "Rejected" in self.workflow_state:
                self.docstatus = 1
                self.docstatus = 2

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

        #if frappe.get_value('Financial Custody', filters={'employee' : self.employee}):
            #name=frappe.get_value('Financial Custody', filters={'employee' : self.employee}) 
            #custody =frappe.get_doc("Financial Custody",name)
            #approver=custody.reported_by
            #if approver:
                #frappe.throw(self.employee+"/ "+self.employee_name+" have an active Financial Custody approved by "+approver)

        


def get_permission_query_conditions(user):
    pass
    # if not user: user = frappe.session.user
    # employees = frappe.get_list("Employee", fields=["name"], filters={'user_id': user}, ignore_permissions=True)
    # if employees:
    #   query = ""
    #   employee = frappe.get_doc('Employee', {'name': employees[0].name})
        
    #   if u'Employee' in frappe.get_roles(user):
    #       if query != "":
    #           query+=" or "
    #       query+=""" employee = '{0}'""".format(employee.name)
    #   return query
