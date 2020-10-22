from __future__ import unicode_literals
import frappe

def execute():

    frappe.reload_doc("HR", "doctype", 'Attendance Status')
    frappe.reload_doc("HR", "doctype", 'Leave Application')
    frappe.reload_doc("HR", "doctype", 'Attendance')

    statuses = {
        "Present": "P",
        "Absent": "A",
        "Work From Home": "WFH",
        "Half Day": "HD",
        "On Leave": "L"
    }

    for status in statuses.keys():
        if not frappe.db.exists("Attendance Status", status):
            att_status = frappe.new_doc("Attendance Status")
            att_status.name = status
            att_status.abbr = statuses[status]

            if status == "Half Day":
                att_status.is_half_day = 1
                att_status.applicable_for_employee_checkins = 1
                att_status.applicable_for_leave_application = 1
                att_status.applicable_for_attendance_request = 1
            elif status == "On Leave":
                att_status.is_leave = 1
                att_status.applicable_for_leave_application = 1
            elif status in ["Work From Home", "Present"]:
                att_status.is_present = 1
                if status == "Present":
                    att_status.applicable_for_employee_checkins = 1

            att_status.save()

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

