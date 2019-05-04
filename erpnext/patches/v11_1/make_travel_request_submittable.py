# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
    a = frappe.get_list("Travel Request", 
                        filters={"created": ["<", frappe.utils.add_days(frappe.utils.datetime.datetime.now(), -30)]}) #Get Travel Requests which are older than 30 days 
    for travel_request in a:
        try:
            req = frappe.get_doc('Travel Request', travel_request)
            req.submit()
        except Exception:
            print(tr)
