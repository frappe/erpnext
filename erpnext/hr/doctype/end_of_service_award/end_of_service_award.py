# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import json
import math
from frappe.utils import cint, cstr, date_diff, flt, formatdate, getdate, get_link_to_form, \
    comma_or, get_fullname, add_years, add_months, add_days, nowdate

class EndofServiceAward(Document):

    def validate(self):
        if self.workflow_state:
            if "Rejected" in self.workflow_state:
                self.docstatus = 1
                self.docstatus = 2
        # frappe.throw(str(self.months))

    # def get_salary(self,employee):

    #   result =frappe.db.sql("select net_pay from `tabSalary Slip` where employee='{0}' order by creation desc limit 1".format(employee))
    #   if result:
    #       return result[0][0]
    #   else:
    #       frappe.throw("لا يوجد قسيمة راتب لهذا الموظف")



    def get_salary(self,employee):
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

@frappe.whitelist()
def get_award(start_date, end_date, salary, toc, reason):

    # doc = json.loads(EOS_doc)
    start = start_date
    end = end_date
    ret_dict = {}

    if getdate(end) < getdate(start):
        frappe.throw("تاريخ نهاية العمل يجب أن يكون أكبر من تاريخ بداية العمل")
    else:
        diffDays = date_diff(end, start)
        years = math.floor(diffDays / 365)
        daysrem = diffDays - (years * 365)
        months = math.floor(daysrem / 30.416)
        days = math.ceil(daysrem - (months * 30.416))
        ret_dict = {"days":days, "months":months, "years":years}
    # salary = doc['salary']
    years = int(years) + (int(months) / 12) + (int(days) / 365)
    # reason = doc['reason']

    if not reason:
        frappe.throw("برجاء اختيار سبب انتهاء العلاقة العمالية")
    else:
        if toc == "Contractor":
            if reason == "فسخ العقد من قبل صاحب العمل لأحد الحالات الواردة في المادة (80)" or reason == "فسخ العقد من قبل العامل أو ترك العامل العمل لغير الحالات الواردة في المادة (81)":
                ret_dict["award"] = "لا يستحق العامل مكافأة نهاية خدمة"
            else:
                firstPeriod, secondPeriod = 0
                if years > 5:
                    firstPeriod = 5
                    secondPeriod = years - 5
                else:
                    firstPeriod = years
                result = (firstPeriod * salary * 0.5) + (secondPeriod * salary)
                ret_dict["award"] = result
        elif toc == "Full-time":

            if reason == "فسخ العقد من قبل صاحب العمل لأحد الحالات الواردة في المادة (80)" or reason == "ترك العامل العمل دون تقديم استقالة لغير الحالات الواردة في المادة (81)":
                ret_dict["award"] = "لا يستحق العامل مكافأة نهاية خدمة"
            elif reason == "استقالة العامل":
                if years < 2:
                    result = 'لا يستحق العامل مكافأة نهاية خدمة'
                elif years <= 5:
                    result = (1 / 6) *  salary * years
                elif years <= 10:
                    result = ((1 / 3) *  salary * 5) + ((2 / 3) *  salary * (years - 5))
                else:
                    result = (0.5 *  salary * 5) + ( salary * (years - 5))
                ret_dict["award"] = result
            else:
                if years <= 5:
                    result = 0.5 *  salary * years
                else:
                    result = (0.5 *  salary * 5) + salary * (years - 5)
                ret_dict["award"] = result
               
    return ret_dict
        
        


def get_permission_query_conditions(user):
    if not user: user = frappe.session.user
    employees = frappe.get_list("Employee", fields=["name"], filters={'user_id': user}, ignore_permissions=True)
    if employees:
        query = ""
        employee = frappe.get_doc('Employee', {'name': employees[0].name})
        
        if u'Employee' in frappe.get_roles(user):
            if query != "":
                query+=" or "
            query+=""" employee = '{0}'""".format(employee.name)
        return query
