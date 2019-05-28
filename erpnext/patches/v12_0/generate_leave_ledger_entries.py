# Copyright (c) 2018, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
    """ Generates leave ledger entries for leave allocation/application/encashment
        for last allocation """
    frappe.reload_doc("HR","doctype", "Leave Ledger Entry")
    if frappe.db.a_row_exists("Leave Ledger Entry"):
        return

    allocation_list = get_allocation_records()
    generate_allocation_ledger_entries(allocation_list)
    generate_application_leave_ledger_entries(allocation_list)
    generate_encashment_leave_ledger_entries(allocation_list)

def generate_allocation_ledger_entries(allocation_list):
    ''' fix ledger entries for missing leave allocation transaction '''
    from erpnext.hr.doctype.leave_allocation.leave_allocation import LeaveAllocation

    for allocation in allocation_list:
        if not frappe.db.exists("Leave Ledger Entry", {'transaction_type': 'Leave Allocation',
            'transaction_name': allocation.name}):
            LeaveAllocation.create_leave_ledger_entry(allocation)

def generate_application_leave_ledger_entries(allocation_list):
    ''' fix ledger entries for missing leave application transaction '''
    from erpnext.hr.doctype.leave_application.leave_application import LeaveApplication

    leave_applications = get_leaves_application_records(allocation_list)

    for record in leave_applications:
        if not frappe.db.exists("Leave Ledger Entry", {'transaction_type': 'Leave Application',
            'transaction_name': record.name}):
            LeaveApplication.create_leave_ledger_entry(record)

def generate_encashment_leave_ledger_entries(allocation_list):
    ''' fix ledger entries for missing leave encashment transaction '''
    from erpnext.hr.doctype.leave_encashment.leave_encashment import LeaveEncashment

    leave_encashments = get_leave_encashment_records(allocation_list)

    for record in leave_encashments:
        if not frappe.db.exists("Leave Ledger Entry", {'transaction_type': 'Leave Encashment',
            'transaction_name': record.name}):
            LeaveEncashment.create_leave_ledger_entry(record)

def get_allocation_records():
    return frappe.db.sql("""
        SELECT
            DISTINCT name,
            employee,
            leave_type,
            new_leaves_allocated,
            carry_forwarded_leaves,
            from_date,
            to_date,
            carry_forward,
            RANK() OVER(PARTITION BY employee, leave_type ORDER BY to_date DESC) as allocation
        FROM `tabLeave Allocation`
        WHERE
            allocation=1
    """, as_dict=1)

def get_leaves_application_records(allocation_list):
    leave_applications = []
    for allocation in allocation_list:
        leave_applications.append(frappe.db.sql("""
            SELECT
                DISTINCT name,
                employee,
                leave_type,
                total_leave_days,
                from_date,
                to_date
            FROM `tabLeave Application`
            WHERE
                from_date >= %s
                leave_type = %s
                employee = %s
        """, (allocation.from_date, allocation.leave_type, allocation.employee)))
    return leave_applications

def get_leave_encashment_records(allocation_list):
    leave_encashments = []
    for allocation in allocation_list:
        leave_encashments.append(frappe.db.sql("""
            SELECT
                DISTINCT name,
                employee,
                leave_type,
                encashable_days,
                from_date,
                to_date
            FROM `tabLeave Encashment`
            WHERE
                leave_type = %s
                employee = %s
        """, (allocation.leave_type, allocation.employee)))
    return leave_encashments