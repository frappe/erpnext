# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe


def execute():
    for report in ["Delayed Order Item Summary", "Delayed Order Summary"]:
        if frappe.db.exists("Report", report):
            frappe.delete_doc("Report", report)
