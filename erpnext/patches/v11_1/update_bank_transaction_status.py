# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe


def execute():
    frappe.reload_doc("accounts", "doctype", "bank_transaction")

    bank_transaction_fields = frappe.get_meta("Bank Transaction").get_valid_columns()

    if 'debit' in bank_transaction_fields:
        frappe.db.sql(""" UPDATE `tabBank Transaction`
            SET status = 'Reconciled'
            WHERE
                status = 'Settled' and (debit = allocated_amount or credit = allocated_amount)
                and ifnull(allocated_amount, 0) > 0
        """)

    elif 'deposit' in bank_transaction_fields:
        frappe.db.sql(""" UPDATE `tabBank Transaction`
            SET status = 'Reconciled'
            WHERE
                status = 'Settled' and (deposit = allocated_amount or withdrawal = allocated_amount)
                and ifnull(allocated_amount, 0) > 0
        """)
