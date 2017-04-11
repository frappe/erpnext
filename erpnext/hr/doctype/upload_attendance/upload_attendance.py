# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, add_days, date_diff
from frappe import _
from frappe.utils.csvutils import UnicodeWriter
from frappe.model.document import Document

class UploadAttendance(Document):
	pass

@frappe.whitelist()
def get_template():
	if not frappe.has_permission("Attendance", "create"):
		raise frappe.PermissionError

	args = frappe.local.form_dict

	w = UnicodeWriter()
	w = add_header(w)

	w = add_data(w, args)

	# write out response as a type csv
	frappe.response['result'] = cstr(w.getvalue())
	frappe.response['type'] = 'csv'
	frappe.response['doctype'] = "Attendance"

def add_header(w):
	status = ", ".join((frappe.get_meta("Attendance").get_field("status").options or "").strip().split("\n"))
	w.writerow(["Notes:"])
	w.writerow(["Please do not change the template headings"])
	w.writerow(["Status should be one of these values: " + status])
	w.writerow(["If you are overwriting existing attendance records, 'ID' column mandatory"])
	w.writerow(["ID", "Employee", "Employee Name", "Date", "Status", "Leave Type",
		 "Company", "Naming Series"])
	return w

def add_data(w, args):
	dates = get_dates(args)
	employees = get_active_employees()
	existing_attendance_records = get_existing_attendance_records(args)
	for date in dates:
		for employee in employees:
			existing_attendance = {}
			if existing_attendance_records \
				and tuple([date, employee.name]) in existing_attendance_records:
					existing_attendance = existing_attendance_records[tuple([date, employee.name])]
			row = [
				existing_attendance and existing_attendance.name or "",
				employee.name, employee.employee_name, date,
				existing_attendance and existing_attendance.status or "",
				existing_attendance and existing_attendance.leave_type or "", employee.company,
				existing_attendance and existing_attendance.naming_series or get_naming_series(),
			]
			w.writerow(row)
	return w

def get_dates(args):
	"""get list of dates in between from date and to date"""
	no_of_days = date_diff(add_days(args["to_date"], 1), args["from_date"])
	dates = [add_days(args["from_date"], i) for i in range(0, no_of_days)]
	return dates

def get_active_employees():
	employees = frappe.db.sql("""select name, employee_name, company
		from tabEmployee where docstatus < 2 and status = 'Active'""", as_dict=1)
	return employees

def get_existing_attendance_records(args):
	attendance = frappe.db.sql("""select name, attendance_date, employee, status, leave_type, naming_series
		from `tabAttendance` where attendance_date between %s and %s and docstatus < 2""",
		(args["from_date"], args["to_date"]), as_dict=1)

	existing_attendance = {}
	for att in attendance:
		existing_attendance[tuple([att.attendance_date, att.employee])] = att

	return existing_attendance

def get_naming_series():
	series = frappe.get_meta("Attendance").get_field("naming_series").options.strip().split("\n")
	if not series:
		frappe.throw(_("Please setup numbering series for Attendance via Setup > Numbering Series"))
	return series[0]


@frappe.whitelist()
def upload():
	if not frappe.has_permission("Attendance", "create"):
		raise frappe.PermissionError

	from frappe.utils.csvutils import read_csv_content_from_uploaded_file
	from frappe.modules import scrub

	rows = read_csv_content_from_uploaded_file()
	rows = filter(lambda x: x and any(x), rows)
	if not rows:
		msg = [_("Please select a csv file")]
		return {"messages": msg, "error": msg}
	columns = [scrub(f) for f in rows[4]]
	columns[0] = "name"
	columns[3] = "attendance_date"
	ret = []
	error = False

	from frappe.utils.csvutils import check_record, import_doc

	for i, row in enumerate(rows[5:]):
		if not row: continue
		row_idx = i + 5
		d = frappe._dict(zip(columns, row))
		d["doctype"] = "Attendance"
		if d.name:
			d["docstatus"] = frappe.db.get_value("Attendance", d.name, "docstatus")

		try:
			check_record(d)
			ret.append(import_doc(d, "Attendance", 1, row_idx, submit=True))
		except Exception, e:
			error = True
			ret.append('Error for row (#%d) %s : %s' % (row_idx,
				len(row)>1 and row[1] or "", cstr(e)))
			frappe.errprint(frappe.get_traceback())

	if error:
		frappe.db.rollback()
	else:
		frappe.db.commit()
	return {"messages": ret, "error": error}
