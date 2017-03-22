# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS LLP and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

@frappe.whitelist()
def get_appointments(date, physician=None, dept=None):
    if not date:
        frappe.throw("Please select Date")
    if not dept and not physician:
        frappe.throw("Please select Physician or Department")

    if physician:
        return frappe.db.sql("select name, patient, physician, token, appointment_time, status from tabAppointment where status not in ('Cancelled', 'Closed') and physician='{0}' and appointment_date='{1}' order by appointment_time""".format(physician, date), as_dict=1)
    else:
        return frappe.db.sql("select name, patient, physician, token, appointment_time, status from tabAppointment where status not in ('Cancelled', 'Closed') and department='{0}' and appointment_date='{1}' order by appointment_time""".format(dept, date), as_dict=1)
