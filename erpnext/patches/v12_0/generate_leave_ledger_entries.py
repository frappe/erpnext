# Copyright (c) 2018, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import getdate

def execute():
    """ Generates leave ledger entries for leave allocation/application/encashment
        for last allocation """
    frappe.reload_doc("HR", "doctype", "Leave Ledger Entry")
    frappe.reload_doc("HR", "doctype", "Leave Encashment")
    if frappe.db.a_row_exists("Leave Ledger Entry"):
        return

    generate_allocation_ledger_entries()
    generate_application_leave_ledger_entries()
    generate_encashment_leave_ledger_entries()

def generate_allocation_ledger_entries():
    ''' fix ledger entries for missing leave allocation transaction '''
    allocation_list = get_allocation_records()

    for allocation in allocation_list:
        if not frappe.db.exists("Leave Ledger Entry", {'transaction_type': 'Leave Allocation', 'transaction_name': allocation.name}):
            allocation.update(dict(doctype="Leave Allocation"))
            allocation_obj = frappe.get_doc(allocation)
            allocation_obj.create_leave_ledger_entry()
            if allocation.to_date <= getdate():
                allocation_obj.expire_allocation()


def generate_application_leave_ledger_entries():
    ''' fix ledger entries for missing leave application transaction '''
    leave_applications = get_leaves_application_records()

    for application in leave_applications:
        if not frappe.db.exists("Leave Ledger Entry", {'transaction_type': 'Leave Application', 'transaction_name': application.name}):
            application.update(dict(doctype="Leave Application"))
            frappe.get_doc(application).create_leave_ledger_entry()

def generate_encashment_leave_ledger_entries():
    ''' fix ledger entries for missing leave encashment transaction '''
    leave_encashments = get_leave_encashment_records()

    for encashment in leave_encashments:
        if not frappe.db.exists("Leave Ledger Entry", {'transaction_type': 'Leave Encashment', 'transaction_name': encashment.name}):
            encashment.update(dict(doctype="Leave Encashment"))
            frappe.get_doc(encashment).create_leave_ledger_entry()

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
            carry_forward
        FROM `tabLeave Allocation`
        WHERE
            docstatus=1
        ORDER BY to_date ASC
    """, as_dict=1)

def get_leaves_application_records():
    return frappe.db.sql("""
            SELECT
                DISTINCT name,
                employee,
                leave_type,
                total_leave_days,
                from_date,
                to_date
            FROM `tabLeave Application`
            WHERE
                docstatus=1
        """, as_dict=1)

def get_leave_encashment_records():
    return frappe.db.sql("""
            SELECT
                DISTINCT name,
                employee,
                leave_type,
                encashable_days,
                encashment_date
            FROM `tabLeave Encashment`
            WHERE
                docstatus=1
        """, as_dict=1)