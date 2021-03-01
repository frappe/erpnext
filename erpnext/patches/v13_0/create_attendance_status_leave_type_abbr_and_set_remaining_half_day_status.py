from __future__ import unicode_literals
import frappe
from erpnext.hr.utils import create_standard_attendance_status

def execute():

    frappe.reload_doc("HR", "doctype", "Attendance Status")
    frappe.reload_doc("HR", "doctype", "Leave Application")
    frappe.reload_doc("HR", "doctype", "Attendance")
    frappe.reload_doc("HR", "doctype", "Leave Type")

    create_standard_attendance_status()

    #create default Abbr for Leave type

    for leave_type in frappe.get_all("Leave Type"):
        full_day_abbr = ""
        half_day_abbr = ""
        # create abbr like CL and CLHD for casual leave
        for words in leave_type.name.split():
            if len(full_day_abbr) > 5:
                break

            full_day_abbr += words[0].upper()

            if len(half_day_abbr) < 3:
                half_day_abbr += words[0].upper()

        half_day_abbr +="HD"

        frappe.db.set_value("Leave Type", leave_type.name, "full_day_abbr", full_day_abbr)
        frappe.db.set_value("Leave Type", leave_type.name, "half_day_abbr", half_day_abbr)

    #setting default status to present for old records
    frappe.db.sql("Update `tabAttendance` set remaining_half_day_status = 'Present' where status = 'Half Day' ")
    frappe.db.sql("Update `tabLeave Application` set remaining_half_day_status = 'Present' where half_day = 1 ")
