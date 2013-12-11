# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import cstr, add_days, date_diff
from webnotes import msgprint, _
from webnotes.utils.datautils import UnicodeWriter

# doclist = None
doclist = webnotes.local('uploadattendance_doclist')

class DocType():
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist

@webnotes.whitelist()
def get_template():
	if not webnotes.has_permission("Attendance", "create"):
		raise webnotes.PermissionError
	
	args = webnotes.local.form_dict
	webnotes.local.uploadattendance_doclist = webnotes.model.doctype.get("Attendance")

	w = UnicodeWriter()
	w = add_header(w)
	
	w = add_data(w, args)

	# write out response as a type csv
	webnotes.response['result'] = cstr(w.getvalue())
	webnotes.response['type'] = 'csv'
	webnotes.response['doctype'] = "Attendance"
	
def getdocfield(fieldname):
	"""get docfield from doclist of doctype"""
	l = [d for d in doclist if d.doctype=='DocField' and d.fieldname==fieldname]
	return l and l[0] or None

def add_header(w):
	status = ", ".join(getdocfield("status").options.strip().split("\n"))
	w.writerow(["Notes:"])
	w.writerow(["Please do not change the template headings"])
	w.writerow(["Status should be one of these values: " + status])
	w.writerow(["If you are overwriting existing attendance records, 'ID' column mandatory"])
	w.writerow(["ID", "Employee", "Employee Name", "Date", "Status", 
		"Fiscal Year", "Company", "Naming Series"])
	return w
	
def add_data(w, args):
	from accounts.utils import get_fiscal_year
	
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
				get_fiscal_year(date)[0], employee.company, 
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
	employees = webnotes.conn.sql("""select name, employee_name, company 
		from tabEmployee where docstatus < 2 and status = 'Active'""", as_dict=1)
	return employees
	
def get_existing_attendance_records(args):
	attendance = webnotes.conn.sql("""select name, att_date, employee, status, naming_series 
		from `tabAttendance` where att_date between %s and %s and docstatus < 2""", 
		(args["from_date"], args["to_date"]), as_dict=1)
		
	existing_attendance = {}
	for att in attendance:
		existing_attendance[tuple([att.att_date, att.employee])] = att
	
	return existing_attendance
	
def get_naming_series():
	series = getdocfield("naming_series").options.strip().split("\n")
	if not series:
		msgprint("""Please create naming series for Attendance \
			through Setup -> Numbering Series.""", raise_exception=1)
	return series[0]


@webnotes.whitelist()
def upload():
	if not webnotes.has_permission("Attendance", "create"):
		raise webnotes.PermissionError
	
	from webnotes.utils.datautils import read_csv_content_from_uploaded_file
	from webnotes.modules import scrub
	
	rows = read_csv_content_from_uploaded_file()
	if not rows:
		msg = [_("Please select a csv file")]
		return {"messages": msg, "error": msg}
	columns = [scrub(f) for f in rows[4]]
	columns[0] = "name"
	columns[3] = "att_date"
	ret = []
	error = False
	
	from webnotes.utils.datautils import check_record, import_doc
	doctype_dl = webnotes.get_doctype("Attendance")
	
	for i, row in enumerate(rows[5:]):
		if not row: continue
		row_idx = i + 5
		d = webnotes._dict(zip(columns, row))
		d["doctype"] = "Attendance"
		if d.name:
			d["docstatus"] = webnotes.conn.get_value("Attendance", d.name, "docstatus")
			
		try:
			check_record(d, doctype_dl=doctype_dl)
			ret.append(import_doc(d, "Attendance", 1, row_idx, submit=True))
		except Exception, e:
			error = True
			ret.append('Error for row (#%d) %s : %s' % (row_idx, 
				len(row)>1 and row[1] or "", cstr(e)))
			webnotes.errprint(webnotes.getTraceback())

	if error:
		webnotes.conn.rollback()		
	else:
		webnotes.conn.commit()
	return {"messages": ret, "error": error}
