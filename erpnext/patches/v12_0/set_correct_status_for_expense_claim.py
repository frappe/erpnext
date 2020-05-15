# Copyright (c) 2020, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

def execute():

    frappe.reload_doc("hr", "doctype", "expense_claim")
    
    frappe.db.sql("""
        update `tabExpense Claim`
        set status = 'Paid'
        where total_advance_amount + total_amount_reimbursed = total_sanctioned_amount + total_taxes_and_charges
    """)
