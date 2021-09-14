# Copyright (c) 2019, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe


def execute():
    if "leave_policy" in frappe.db.get_table_columns("Employee"):
        employees_with_leave_policy = frappe.db.sql("SELECT name, leave_policy FROM `tabEmployee` WHERE leave_policy IS NOT NULL and leave_policy != ''", as_dict = 1)

        employee_with_assignment = []
        leave_policy =[]

        #for employee

        for employee in employees_with_leave_policy:
            alloc = frappe.db.exists("Leave Allocation", {"employee":employee.name, "leave_policy": employee.leave_policy, "docstatus": 1})
            if not alloc:
                create_assignment(employee.name, employee.leave_policy)

            employee_with_assignment.append(employee.name)
            leave_policy.append(employee.leave_policy)


    if "default_leave_policy" in frappe.db.get_table_columns("Employee"):
        employee_grade_with_leave_policy = frappe.db.sql("SELECT name, default_leave_policy FROM `tabEmployee Grade` WHERE default_leave_policy IS NOT NULL and default_leave_policy!=''", as_dict = 1)

        #for whole employee Grade

        for grade in employee_grade_with_leave_policy:
            employees = get_employee_with_grade(grade.name)
            for employee in employees:

                if employee not in employee_with_assignment: #Will ensure no duplicate
                    alloc = frappe.db.exists("Leave Allocation", {"employee":employee.name, "leave_policy": grade.default_leave_policy, "docstatus": 1})
                    if not alloc:
                        create_assignment(employee.name, grade.default_leave_policy)
                    leave_policy.append(grade.default_leave_policy)

    #for old Leave allocation and leave policy from allocation, which may got updated in employee grade.
    leave_allocations = frappe.db.sql("SELECT leave_policy, leave_period, employee FROM `tabLeave Allocation` WHERE leave_policy IS NOT NULL and leave_policy != '' and docstatus = 1 ", as_dict = 1)

    for allocation in leave_allocations:
        if allocation.leave_policy not in leave_policy:
            create_assignment(allocation.employee, allocation.leave_policy, leave_period=allocation.leave_period,
                allocation_exists=True)

def create_assignment(employee, leave_policy, leave_period=None, allocation_exists = False):

    filters = {"employee":employee, "leave_policy": leave_policy}
    if leave_period:
        filters["leave_period"] = leave_period

    frappe.reload_doc('hr', 'doctype', 'leave_policy_assignment')

    if not frappe.db.exists("Leave Policy Assignment" , filters):
        lpa = frappe.new_doc("Leave Policy Assignment")
        lpa.employee = employee
        lpa.leave_policy = leave_policy

        lpa.flags.ignore_mandatory = True
        if allocation_exists:
            lpa.assignment_based_on = 'Leave Period'
            lpa.leave_period = leave_period
            lpa.leaves_allocated = 1

        lpa.save()
        if allocation_exists:
            lpa.submit()
            #Updating old Leave Allocation
            frappe.db.sql("Update `tabLeave Allocation` set leave_policy_assignment = %s", lpa.name)


def get_employee_with_grade(grade):
    return frappe.get_list("Employee", filters = {"grade": grade})
