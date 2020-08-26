# Copyright (c) 2019, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe

def execute():
    employees_with_leave_policy = frappe.db.sql("SELECT name, leave_policy FROM `tabEmployee` WHERE leave_policy IS NOT NULL", as_dict = 1)

    for employee in employees_with_leave_policy:
        print(employee.name)
        if not frappe.db.exists("Leave Allocation", {"employee":employee.name, "leave_policy": employee.leave_policy, "docstatus": 1}):
            create_assignment(employee.name, employee.leave_policy)


    employee_grade_with_leave_policy = frappe.db.sql("SELECT name, default_leave_policy FROM `tabEmployee Grade` WHERE default_leave_policy IS NOT NULL", as_dict = 1)

    for grade in employee_grade_with_leave_policy:
        employees = get_employee_with_grade(grade.name)
        print(employees)
        for employee in employees:
            alloc = frappe.db.exists("Leave Allocation", {"employee":employee.name, "leave_policy": grade.default_leave_policy, "docstatus": 1})
            if not alloc:
                create_assignment(employee.name, grade.default_leave_policy)

def create_assignment(employee, leave_policy):
    lpa = frappe.new_doc("Leave Policy Assignment")
    lpa.employee = employee
    lpa.leave_policy = leave_policy

    lpa.flags.ignore_mandatory = True
    lpa.save()

def get_employee_with_grade(garde):
    return frappe.get_list("Employee", filters = {"grade": grade})



