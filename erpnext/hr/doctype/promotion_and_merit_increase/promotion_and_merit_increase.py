# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from __future__ import unicode_literals
import frappe
from frappe import _
# import json
from frappe.utils import cint
from frappe.utils import flt, getdate, add_days, get_last_day, get_first_day, nowdate, add_months
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from erpnext.hr.doctype.salary_structure.salary_structure import make_salary_slip
class PromotionandMeritIncrease(Document):

    def validate(self):
        self.check_total_points()
        self.validate_dates()
        self.validate_contest()
        self.validate_emp()
        if hasattr(self,"workflow_state"):
            if self.workflow_state:
                if "Rejected" in self.workflow_state:
                    self.docstatus = 1
                    self.docstatus = 2

    def validate_emp(self):
        if self.get('__islocal'):
            if u'CEO' in frappe.get_roles(frappe.session.user):
                self.workflow_state = "Created By CEO"
            elif u'Director' in frappe.get_roles(frappe.session.user):
                self.workflow_state = "Created By Director"
            elif u'Manager' in frappe.get_roles(frappe.session.user):
                self.workflow_state = "Created By Manager"
            elif u'Line Manager' in frappe.get_roles(frappe.session.user):
                self.workflow_state = "Created By Line Manager"
            elif u'Employee' in frappe.get_roles(frappe.session.user):
                self.workflow_state = "Pending"

    def get_basic_salary(self):
        components_data = self.get_salary_slip_data()
        if components_data and components_data["earnings"]:
            for component in components_data["earnings"]:
                if component.salary_component == "Basic":
                    return component.amount

        # grade = frappe.db.sql("select base from tabGrade where name=(select grade from tabEmployee where employee='{0}')".format(self.employee))
        # if grade:
        #     return grade[0][0]

    # def update_newbase(self):
    #     ngrade = frappe.db.sql("select base from tabGrade where name='{0}'".format(self.new_grade))
    #     if ngrade:
    #         return ngrade[0][0]
    
    # def get_salary_slip_info(self):
    #     st_name = frappe.db.sql("""select name,parent,base from `tabSalary Structure Employee`
    #         where employee=%s order by modified desc limit 1""",self.employee,as_dict=True)

    #     if st_name:         
    #         struct = frappe.db.sql("""select name from `tabSalary Structure` where name=%s and is_active='Yes' limit 1""",st_name[0].parent)
    #         ss = make_salary_slip(struct[0][0], employee=self.employee, as_print=False)
    #         # frappe.throw(str(ss))
    #         return frappe.as_json(ss)
    def get_salary_slip_data(self):
        data = {}
        next_month_date = getdate(add_months(nowdate(), 1))
        ss_doc = frappe.new_doc("Salary Slip")
        ss_doc.employee = self.employee
        ss_doc.start_date = get_first_day(next_month_date)
        ss_doc.end_date = get_last_day(next_month_date)
        # ss_doc.flags.ignore_validate = True
        ss_doc.save(ignore_permissions=True)
        data["earnings"] = ss_doc.get("earnings")
        data["deductions"] = ss_doc.get("deductions")
        # return ss_doc.get("deductions")
        # for s in ss_doc.get("deductions"):
        #     return s
        # for components in (ss_doc.get("deductions"), ss_doc.get("earnings")):
        #     # data[components] = {}
        #     # comps = ss_doc.get(key)
        #     # return comps
        #     for component in components:
        #         # return component
        #         data["deductions"].update(component)
        #         return data
        #     # frappe.throw(component.parentfield)
        ss_doc.delete()
        return data

    def calculate_main_basic(self):
        if self.new_grade and self.new_level:
            grade_info = frappe.db.get_values("Grade", self.new_grade, ["base", "level_percent"], as_dict=True)[0]
            from math import ceil
            level =int(self.new_level)
            base = grade_info.base
            percent = float(grade_info.level_percent)/100
            for l in range(1, level):
                base += base*percent
            return ceil(base)

    # def update_employee_salary_structure(self):
    #     emp_salary_list = frappe.get_list("Salary Structure Employee", fields=["*"], filters={"employee":self.name})
    #     if emp_salary_list:
    #         for emp_salary in emp_salary_list:
    #             emp_doc_struct = frappe.get_doc("Salary Structure Employee",emp_salary["name"])
    #             emp_doc_struct.base = self.new_base
    #             emp_doc_struct.grade = self.new_grade
    #             emp_doc_struct.level = self.new_level
    #             emp_doc_struct.save(ignore_permissions=True)

    def make_salary_structure(self):
        ss_list = frappe.db.sql("""select parent from `tabSalary Structure Employee` where 
            employee = '{0}' and parenttype = 'Salary Structure'""".format(self.employee), as_dict=True)
        for ss in ss_list:
            if ss_list:
                salary_info = self.get_salary_slip_data()
                old_ss = frappe.get_doc("Salary Structure",{"name":ss.parent,"is_active":"Yes"})
                new_ss = frappe.new_doc("Salary Structure")
                new_ss.name = make_autoname("Promotion-"+self.employee+'-.####')
                employee_info={
                "employee":self.employee,
                "grade":self.new_grade,
                "level":self.new_level,
                "from_date":self.due_date,
                "base":self.new_base
                }
                new_ss.set("earnings", old_ss.get("earnings"))
                earnings = []
                deductions = []
                for old_earnings in old_ss.get("earnings"):
                    earning={
                        "salary_component":old_earnings.salary_component,
                        "condition":old_earnings.condition,
                        "formula": old_earnings.formula,
                        "amount_based_on_formula": old_earnings.amount_based_on_formula,
                        "amount": old_earnings.amount,
                        "depends_on_lwp": old_earnings.depends_on_lwp,
                        "default_amount": old_earnings.default_amount
                    }
                    earnings.append(earnings)
                for old_deduction in old_ss.get("deductions"):
                    deduction={
                        "salary_component":old_deduction.salary_component,
                        "condition":old_deduction.condition,
                        "formula": old_deduction.formula,
                        "amount_based_on_formula": 0,
                        "amount": old_deduction.amount,
                        "depends_on_lwp": old_deduction.depends_on_lwp,
                        "default_amount": old_deduction.default_amount
                    }
                    if old_deduction.salary_component == "GOSI":
                        # new_gosi = dict(old_deduction)
                        deduction["formula"]="(B+H)*.1"
                        deduction["amount_based_on_formula"]=0
                        for component in salary_info["deductions"]:
                            if component.salary_component == "GOSI":
                                deduction["amount"] = component.amount
                    deductions.append(deduction) 
                new_ss.set("employees",[employee_info])
                new_ss.set("deductions",deductions)
                if getdate(self.due_date) > getdate(nowdate()):
                    new_ss.is_active = "No"
                new_ss.payment_account = old_ss.payment_account
                new_ss.save(ignore_permissions=True)
        # ss_list = frappe.db.sql("""select parent from `tabSalary Structure Employee` where 
        #     employee = '{0}' and parenttype = 'Salary Structure' """.format(self.employee), as_dict=True)
        # if ss_list:
        #     salary_info = self.get_salary_slip_data()
        #     for ss in ss_list:
        #         ss_doc = frappe.get_doc("Salary Structure",ss.parent)
        #         employees, deductions = ss_doc.get("employees"), ss_doc.get("deductions")
        #         if employees:
        #             for emp in employees:
        #                 if emp.employee == self.employee:
        #                     emp.base = self.new_base
        #                     emp.grade = self.new_grade
        #                     emp.level = self.new_level,
        #                     "from_date": self.due_date
        #         if deductions:
        #             for deduction in deductions:
        #                 if deduction.salary_component == "GOSI":
        #                     deduction.formula="(B+H)*.1"
        #                     deduction.amount_based_on_formula = 0
        #                     for component in salary_info["deductions"]:
        #                         deduction.amount = component.amount
        #         ss_doc.save(ignore_permissions=True) 

    def check_total_points(self):
        if self.promotion_type =="By Comparison":
            total_points = 0
            for d in self.get("goals"):
                total_points += int(d.per_weightage or 0)
            if cint(total_points) != 100:
                frappe.throw(_("Sum of points for all goals should be 100. It is {0}").format(total_points))


    def validate_contest(self):
        if self.promotion_type == "By Contest":
            if not self.contest_id or not self.contest_result :
                frappe.throw(_("Enter Contest Information"))


    def before_submit(self):
        self.validate_dates()
        self.validate_contest()

    def on_submit(self):
        self.insert_work_history()
        self.make_salary_structure()

    def insert_work_history(self):
        employee = frappe.get_doc('Employee',{'name' : self.employee})
        iwh = employee.get("internal_work_history")
        if iwh:
            from_date = add_days(iwh[-1].to_date, 1)
        else:
            from_date = employee.date_of_joining
        # salary_structer_list = frappe.get_list("Salary Structure", fields=["name"],filters ={'employee' : employee.name,'is_active':'Yes'})
        # if salary_structer_list:
        #   salary_structer = frappe.get_doc('Salary Structure Employee',{'employee' : employee.name,'is_active':'Yes'} )
        #   salary_structer.grade =self.new_grade if self.new_grade else salary_structer.grade
        #   salary_structer.main_payment =self.main_payment if self.main_payment else salary_structer.main_payment
        #   salary_structer.total_earning =self.total_earning if self.total_earning else salary_structer.total_earning
        #   salary_structer.total_deduction =self.total_deduction if self.total_deduction else salary_structer.total_deduction
        #   salary_structer.net_pay =self.net_pay if self.net_pay else salary_structer.net_pay

        #   # doc.set("packed_items", [])
        #   if self.earnings != []:
        #       salary_structer.set("earnings", [])
        #       for d in self.earnings:
        #           salary_structer.append("earnings", d)
        #   if self.deductions != [] :
        #       salary_structer.set("deductions", [])
        #       for d in self.deductions:
        #           salary_structer.append("deductions", d)

        #   salary_structer.save(ignore_permissions=True)
        # else :
        #   frappe.throw(_("Add Salary Structer for Employee")+"<a href='#List/Salary Structure'>"+_("Salary Structure")+"</a>")

        # old_jo = employee.job_opening
        # jo_list = frappe.get_list("Job Opening", fields=["name"],filters ={'name' : employee.job_opening})
        # if jo_list:
        #   jo = frappe.get_doc('Job Opening',{'name' : employee.job_opening} )
        #   jo.status ='Open'
        #   jo.save()


        old_work_start_date = employee.date_of_joining
        employee.grade = self.new_grade if self.new_grade else employee.grade
        employee.employment_type = self.new_employment_type if self.new_employment_type else employee.employment_type
        # employee.department=self.new_department if self.new_department else employee.department
        employee.designation = self.new_designation if self. new_designation else employee.designation
        employee.level=self.new_level if self.new_level else employee.level
        employee.branch=self.new_branch if self.new_branch else employee.branch
        # employee.job_opening = self.job_opening if self.job_opening else employee.job_opening
        # employee.date_of_joining= self.due_date if self.due_date else employee.date_of_joining
        # employee.work_start_date_hijri = self.due_date if self.due_date else employee.work_start_date
        # employee.scheduled_confirmation_date = self.due_date if self.due_date else employee.scheduled_confirmation_date
        # employee.scheduled_confirmation_date_hijri = self.due_date if self.due_date else employee.scheduled_confirmation_date
        employee.save()

        # jo1_list = frappe.get_list("Job Opening", fields=["name"],filters ={'name' : self.job_opening})
        # if jo1_list:
        #   jo1 = frappe.get_doc('Job Opening',{'name' : self.job_opening} )
        #   jo1.status ='Closed'
        #   jo1.save()

        old_work = frappe.new_doc(u'Employee Internal Work History',employee,u'internal_work_history')
        old_work.update(
            {
                "branch": self.branch,
                "department":  self.department,
                "designation":self.designation,
                "grade": self.grade,
                "employment_type":self.employment_type,
                "level": self.level,
                "from_date": from_date,
                "to_date": add_days(self.due_date,-1)
            }
            # {
            #   "type":"Promotion",
            #   "branch": self.branch,
            #   "department":  self.department,
            #   "designation":self.designation,
            #   "grade_old": self.grade,
            #   # "job_opening":old_jo,
            #   "employment_type":self.employment_type,
            #   "new_branch": self.new_branch,
            #   "new_level": self.new_level,
            #   "new_department":  self.new_department,
            #   "new_designation":self.new_designation,
            #   "new_grade": self.new_grade,
            #   "new_employment_type":self.new_employment_type,
            #   # "new_job_opening":self.job_opening,
            #   "work_start_date":old_work_start_date,
            #   # "from_date": employee.    _confirmation_date,
            #   "to_date": self.due_date,
            #   "administrative_decision":self.name
            # }
        )
        old_work.insert()



    def validate_dates(self):
        pass
        # if getdate(self.due_date) > getdate(self.commencement_date):
        #     frappe.throw(_("Commencement date can not be less than Due date"))

    def get_child_table(self):
        if self.new_grade:
            doc_a = frappe.get_doc("Grade",self.new_grade)
            self.main_payment = doc_a.main_payment
            # self.total_earning = doc_a.total_earning
            # self.total_deduction = doc_a.total_deduction
            # self.net_pay = doc_a.net_pay
            self.accommodation_from_company = doc_a.accommodation_from_company
            self.accomodation_percentage = doc_a.accomodation_percentage
            self.accommodation_value = doc_a.accommodation_value
            # self.accommodation_value = doc_a.accommodation_value
            self.transportation_costs = doc_a.transportation_costs
            # list1=doc_a.get("earnings")
            # list2=doc_a.get("deductions")
            # for t in list1:
            #   child = self.append('earnings', {})
            #   child.e_type = t.e_type
            #   child.depend_on_lwp = t.depend_on_lwp
            #   child.modified_value = t.modified_value
            #   child.e_percentage = t.e_percentage
            # for t in list2:
            #   child = self.append('deductions', {})
            #   child.d_type = t.d_type
            #   child.based_on_total = t.based_on_total
            #   child.d_modified_amt = t.d_modified_amt
            #   child.d_percentage = t.d_percentage
            #   child.depend_on_lwp = t.depend_on_lwp
            return "done"
        else :
            return "no grade"
