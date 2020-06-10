from __future__ import unicode_literals
import frappe
from frappe.model.utils.rename_field import update_reports, update_users_report_view_settings, update_property_setters

def execute():
	if "att_date" not in frappe.db.get_table_columns("Attendance"):
		return
	frappe.reload_doc("hr", "doctype", "attendance")
	frappe.db.sql("""update `tabAttendance` 
	 		set attendance_date = att_date
			where attendance_date is null or attendance_date = '0000-00-00'""")
	
	update_reports("Attendance", "att_date", "attendance_date")
	update_users_report_view_settings("Attendance", "att_date", "attendance_date")
	update_property_setters("Attendance", "att_date", "attendance_date")
