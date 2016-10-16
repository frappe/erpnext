# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, ast
from frappe.model.document import Document
from frappe import _

class SalaryStructureEmployeeAssign(Document):
    pass


@frappe.whitelist()
def get_employees(salary_structure, company=None, employment_type=None, branch=None, department=None, designation=None):
    salry_struc_not_marked = []
    employee_list = frappe.get_list('Employee',
                                    filters={"company": company, "employment_type": employment_type, "branch": branch,
                                             "department": department, "designation": designation},
                                    fields=['employee', 'employee_name'])
    for emp in employee_list:
        if not frappe.db.exists("Salary Structure Employee", {"employee": emp.employee}):
            salry_struc_not_marked.append({"employee": emp.employee, "employee_name": emp.employee_name})

    salary_struc_marked = list({"employee": x.employee, "employee_name": x.employee_name} for x in
                               frappe.get_doc("Salary Structure", salary_structure).employees)
    return {
        "marked": salary_struc_marked,
        "unmarked": salry_struc_not_marked
    }


@frappe.whitelist()
def add_or_update(salary_structure, base, update_base_and_variable=0, variable=None, employee_add=None,
                  employee_remove=None):
    salary_strc = frappe.get_doc('Salary Structure', salary_structure)
    employees = salary_strc.as_dict().employees
    employee_remove = ast.literal_eval(employee_remove)
    for key, row in enumerate(employees):
        if row.employee in employee_remove:
            del employees[key]
        elif int(update_base_and_variable):
            row.base = base
            row.variable = variable

    for emp in ast.literal_eval(employee_add):
        employees.append({
            "employee": emp[0],
            "employee_name": emp[1],
            "base": base,
            "variable": variable
        })
    salary_strc.set('employees', employees)
    salary_strc.save()
    frappe.msgprint(_("Successfully Synced"))
