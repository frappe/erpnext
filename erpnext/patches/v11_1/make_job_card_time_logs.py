# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe


def execute():
    frappe.reload_doc('manufacturing', 'doctype', 'job_card_time_log')

    if (frappe.db.table_exists("Job Card")
        and frappe.get_meta("Job Card").has_field("actual_start_date")):
        time_logs = []
        for d in frappe.get_all('Job Card',
            fields = ["actual_start_date", "actual_end_date", "time_in_mins", "name", "for_quantity"],
            filters = {'docstatus': ("<", 2)}):
            if d.actual_start_date:
                time_logs.append([d.actual_start_date, d.actual_end_date, d.time_in_mins,
                    d.for_quantity, d.name, 'Job Card', 'time_logs', frappe.generate_hash("", 10)])

        if time_logs:
            frappe.db.sql(""" INSERT INTO
                `tabJob Card Time Log`
                    (from_time, to_time, time_in_mins, completed_qty, parent, parenttype, parentfield, name)
                values {values}
            """.format(values = ','.join(['%s'] * len(time_logs))), tuple(time_logs))

        frappe.reload_doc('manufacturing', 'doctype', 'job_card')
        frappe.db.sql(""" update `tabJob Card` set total_completed_qty = for_quantity,
            total_time_in_mins = time_in_mins where docstatus < 2 """)
