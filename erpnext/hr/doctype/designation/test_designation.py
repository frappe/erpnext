# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals


import frappe
# test_records = frappe.get_test_records('Designation')

def create_designation(**args):
    args = frappe._dict(args)
    designation = frappe.get_doc({
        "designation_name": args.designation_name or "_Test designation",
        "description": args.description or "_Test description"
    })
    designation.save()
    return designation