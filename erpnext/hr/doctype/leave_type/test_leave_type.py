# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals

import frappe
from frappe import _

test_records = frappe.get_test_records('Leave Type')

def create_leave_type(**args):
    args = frappe._dict(args)
    if frappe.db.exists("Leave Type", args.leave_type_name):
        return frappe.get_doc("Leave Type", args.leave_type_name)
    leave_type = frappe.get_doc({
        "doctype": "Leave Type",
        "leave_type_name": args.leave_type_name or "_Test Leave Type",
        "include_holiday": args.include_holidays or 1,
        "allow_encashment": args.allow_encashment or 0,
        "is_earned_leave": args.is_earned_leave or 0,
        "is_lwp": args.is_lwp or 0,
        "is_carry_forward": args.is_carry_forward or 0,
        "expire_carry_forwarded_leaves_after_days": args.expire_carry_forwarded_leaves_after_days or 0,
        "encashment_threshold_days": args.encashment_threshold_days or 5,
        "earning_component": "Leave Encashment"
    })
    return leave_type