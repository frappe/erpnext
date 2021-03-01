# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, cint, getdate, get_datetime
from frappe import _
from calendar import monthrange


day_abbr = [
	"Mon",
	"Tue",
	"Wed",
	"Thu",
	"Fri",
	"Sat",
	"Sun"
]

month_abbr = [
	"Jan",
	"Feb",
	"Mar",
	"Apr",
	"May",
	"Jun",
	"Jul",
	"Aug",
	"Sep",
	"Oct",
	"Nov",
	"Dec"
]

def execute(filters=None):
	if not filters: filters = {}

	if filters.hide_year_field == 1:
		filters.year = get_datetime().year

	conditions, filters = get_conditions(filters)
	columns, days = get_columns(filters)
	att_map = get_attendance_list(conditions, filters)

	if filters.group_by:
		emp_map, group_by_parameters = get_employee_details(filters.group_by, filters.company)
		holiday_list = []
		for parameter in group_by_parameters:
			h_list = [emp_map[parameter][d]["holiday_list"] for d in emp_map[parameter] if emp_map[parameter][d]["holiday_list"]]
			holiday_list += h_list
	else:
		emp_map = get_employee_details(filters.group_by, filters.company)
		holiday_list = [emp_map[d]["holiday_list"] for d in emp_map if emp_map[d]["holiday_list"]]

	default_holiday_list = frappe.get_cached_value('Company',  filters.get("company"),  "default_holiday_list")
	holiday_list.append(default_holiday_list)
	holiday_list = list(set(holiday_list))
	holiday_map = get_holiday(holiday_list, filters["from_date"], filters['to_date'])

	data = []

	leave_list = None
	if filters.summarized_view:
		leave_types = frappe.db.sql("""select name from `tabLeave Type`""", as_list=True)
		leave_list = [d[0] + ":Float:120" for d in leave_types]
		columns.extend(leave_list)
		columns.extend([_("Total Late Entries") + ":Float:120", _("Total Early Exits") + ":Float:120"])

	if filters.group_by:
		emp_att_map = {}
		for parameter in group_by_parameters:
			data.append([ "<b>"+ parameter + "</b>"])
			record, aaa = add_data(emp_map[parameter], att_map, holiday_map, filters, default_holiday_list, leave_list=leave_list)
			emp_att_map.update(aaa)
			data += record
	else:
		record, emp_att_map = add_data(emp_map, att_map, holiday_map, filters, default_holiday_list, leave_list=leave_list)
		data += record

	chart_data = get_chart_data(emp_att_map, days)

	return columns, data, None, chart_data

def get_chart_data(emp_att_map, days):
	labels = []
	datasets = [
		{"name": "Absent", "values": []},
		{"name": "Present", "values": []},
		{"name": "Leave", "values": []},
	]

	att_abbr_map = get_attendance_status_abbr_map(get_abbr_map=1)
	half_day_leave_abbr, full_day_leave_abbr = get_leave_type_abbr(get_abbr=1)

	for idx, day in enumerate(days, start=0):
		labels.append(day.replace("::100", ""))
		total_absent_on_day = 0
		total_leave_on_day = 0
		total_present_on_day = 0
		total_holiday = 0
		for emp in emp_att_map.keys():
			if emp_att_map[emp][idx]:
				abbr = emp_att_map[emp][idx].split(" + ")

				if len(abbr) == 1 and  abbr[0] not in ["<b>WO</b>", "<b>H</b>"]:
					if abbr[0] in full_day_leave_abbr or abbr[0] == "L":
						total_leave_on_day +=1
					elif att_abbr_map[abbr[0]]["is_present"]:
						total_present_on_day += 1
					else:
						total_absent_on_day += 1

				#means half day having two attendance on same day
				if len(abbr) == 2:
					if abbr[0] in half_day_leave_abbr:
						total_leave_on_day +=0.5

					if att_abbr_map[abbr[1]]["is_present"]:
						total_present_on_day += 0.5
					else:
						total_absent_on_day += 0.5


		datasets[0]["values"].append(total_absent_on_day)
		datasets[1]["values"].append(total_present_on_day)
		datasets[2]["values"].append(total_leave_on_day)


	chart = {
		"data": {
			'labels': labels,
			'datasets': datasets
		}
	}

	chart["type"] = "line"

	return chart

def add_data(employee_map, att_map, holiday_map, filters, default_holiday_list, leave_list=None):
	record = []
	emp_att_map = {}
	for emp in employee_map:
		emp_det = employee_map.get(emp)
		if not emp_det or emp not in att_map:
			continue
		row = []
		if filters.group_by:
			row += [" "]
		row += [emp, emp_det.employee_name]
		emp_status_map = []

		to_date = getdate(filters["to_date"])
		from_date =getdate(filters["from_date"])

		keys = get_days_columns(to_date, from_date, get_att_map_key=True)
		status_map = get_attendance_status_abbr_map()
		total_p = total_a = total_l = total_h = total_um= 0.0

		for day in keys:
			attendance_detail = att_map.get(emp).get(day)
			emp_holiday_list = emp_det.holiday_list if emp_det.holiday_list else default_holiday_list
			status = None
			status = get_status(attendance_detail, holiday_map, emp_holiday_list, day)

			leave_abbr_map = get_leave_type_abbr()
			abbr = ""
			if status:
				abbr = get_abbr(status, status_map, leave_abbr_map, attendance_detail)

			emp_status_map.append(abbr)

			if filters.summarized_view:
				count = get_totals(status, status_map, attendance_detail)
				total_p += count[0]; total_l += count[1]; total_a += count[2]; total_h += count[3]; total_um += count[4]

		if not filters.summarized_view:
			row += emp_status_map
		if filters.summarized_view:
			row += [total_p, total_l, total_a, total_h, total_um]

		conditions, filters = get_conditions(filters)
		if not filters.get("employee"):
			filters.update({"employee": emp})
			conditions += " and employee = %(employee)s"
		elif not filters.get("employee") == emp:
			filters.update({"employee": emp})

		if filters.summarized_view:
			get_leave_type_and_total_leave_taken(row, conditions, filters, emp, leave_list=leave_list)
			get_late_entry_and_earl_exit_count(row, conditions, filters)

		emp_att_map[emp] = emp_status_map
		record.append(row)
	return record, emp_att_map

def get_late_entry_and_earl_exit_count(row, conditions, filters):
	time_default_counts = frappe.db.sql("""select (select count(*) from `tabAttendance` where \
		late_entry = 1 %s) as late_entry_count, (select count(*) from tabAttendance where \
		early_exit = 1 %s) as early_exit_count""" % (conditions, conditions), filters)

	row.extend([time_default_counts[0][0],time_default_counts[0][1]])

def get_leave_type_and_total_leave_taken(row, conditions, filters, emp, leave_list=None):
	leave_details = frappe.db.sql("""select leave_type, status, count(*) as count from `tabAttendance`\
		where leave_type is not NULL %s group by leave_type, status""" % conditions, filters, as_dict=1)

	leaves = {}
	for d in leave_details:
		if d.status == "Half Day":
			d.count = d.count * 0.5
		if d.leave_type in leaves:
			leaves[d.leave_type] += d.count
		else:
			leaves[d.leave_type] = d.count


	for d in leave_list:
		d = d.replace(":Float:120", "")
		print(d)
		if d in leaves:
			row.append(leaves[d])
		else:
			row.append("0.0")

def get_totals(status, status_map, attendance_detail):

	present = absent = leave = holiday = unmarked= 0.0
	if status and attendance_detail:
		if status in ["Weekly Off", "Holiday"]:
			holiday += 1
		if status_map[status]['is_present']:
			present += 1
		elif status_map[status]['is_leave']:
			leave += 1
		elif status_map[status]['is_half_day']:
			leave += 0.5
			remaining_half_day_status = attendance_detail[2]
			if status_map[remaining_half_day_status]["is_present"]:
				present += 0.5
			else:
				absent += 0.5
		else:
			absent +=  1
	else:
		unmarked += 1

	return [present, leave, absent, holiday, unmarked]

def get_abbr(status, status_map, leave_abbr_map, attendance_detail):
	abbr = ''
	abbr = status_map[status]['abbr']
	if attendance_detail:
		leave_type = attendance_detail[1]

		if status_map[status]['is_leave'] and leave_type:
			abbr = leave_abbr_map[leave_type]["full_day_abbr"]

		if status_map[status]['is_half_day'] and leave_type:
			abbr = leave_abbr_map[leave_type]["half_day_abbr"]
			remaining_half_day_status = attendance_detail[2]

			rem_half_day_abbr = status_map[remaining_half_day_status]['abbr']
			abbr += " + " + rem_half_day_abbr
	return abbr

def get_status(attendance_detail, holiday_map, emp_holiday_list, day):
	status = None
	if attendance_detail:
		status = attendance_detail[0]

	if status is None and holiday_map:
		if emp_holiday_list in holiday_map:
			for idx, ele in enumerate(holiday_map[emp_holiday_list]):
				if day == holiday_map[emp_holiday_list][idx][0]:
					if holiday_map[emp_holiday_list][idx][1]:
						status = "Weekly Off"
					else:
						status = "Holiday"

	return status

def get_attendance_status_abbr_map(get_abbr_map=0, remove_hard_coded_status = 0):
	statuses = frappe.get_all("Attendance Status", fields= ['name', 'abbr', 'is_half_day', 'is_leave', 'is_present'])
	statuses_map = {}

	if get_abbr_map:
		abbr_map = {}
		for status in statuses:
			abbr_map[status.abbr] = status
		return abbr_map

	for status in statuses:
		statuses_map[status.name] = status

	if not remove_hard_coded_status:
		statuses_map["Weekly Off"] = {'abbr': "<b>WO</b>"}
		statuses_map["Holiday"] = {'abbr': "<b>H</b>"}
	return statuses_map

def get_leave_type_abbr(get_abbr=0):
	leave_type_abbrs = frappe.get_all("Leave Type", fields= ['name', 'full_day_abbr', 'half_day_abbr'])
	leave_type_abbr_map = {}

	if get_abbr:
		full_day_abbr_list = [abbr.full_day_abbr for abbr in leave_type_abbrs]
		half_day_abbr_list = [abbr.half_day_abbr for abbr in leave_type_abbrs]
		return half_day_abbr_list, full_day_abbr_list

	for abbr in leave_type_abbrs:
		leave_type_abbr_map[abbr.name] = abbr

	return leave_type_abbr_map

def get_columns(filters):

	columns = []
	if filters.group_by:
		columns = [_(filters.group_by)+ ":Link/Branch:120"]
	columns += [
		_("Employee") + ":Link/Employee:120", _("Employee Name") + ":Data/:120"
	]

	to_date = getdate(filters["to_date"])
	from_date = getdate(filters["from_date"])

	if to_date < from_date:
		frappe.throw(_("To Date cannot be less than From Date"))
	if frappe.utils.date_diff(to_date, from_date) > 62:
		frappe.throw(_("Please select the interval period between From Date and To Date to be less than 2 months"))
	if to_date.year != from_date.year:
		frappe.throw(_("Please select the From Date and the To Date from the same Year."))
	days = get_days_columns(to_date, from_date)

	if not filters.summarized_view:
		columns += days
	if filters.summarized_view:
		columns += [_("Total Present") + ":Float:120", _("Total Leaves") + ":Float:120",  _("Total Absent") + ":Float:120", _("Total Holidays") + ":Float:120", _("Unmarked Days")+ ":Float:120"]
	return columns, days

def get_days_columns(to_date, from_date, get_att_map_key= False):
	days = []
	if to_date.month == from_date.month and to_date.year == from_date.year:
		days += _get_days_columns(from_date.day-1, to_date.day, to_date.month, to_date.year, get_att_map_key= get_att_map_key)
	elif to_date.month != from_date.month and to_date.year == from_date.year:
		start_date = from_date
		month = from_date.month - 1

		while(month < to_date.month):
			month += 1
			end = monthrange(cint(start_date.year), cint(month))[1]
			end_date = getdate(str(start_date.year) + "-" + str(month)+ "-" + str(end))
			if to_date < getdate(end_date):
				end = to_date.day

			days += _get_days_columns(start_date.day-1, end, month, start_date.year, add_month=True, get_att_map_key= get_att_map_key)

			start_date = getdate(str(start_date.year) + "-" + str(month)+ "-" + str(1))

	return days

def _get_days_columns(start_day, end_day, month, year, add_month=False, get_att_map_key= False):
	days = []
	month_name = ''
	if add_month:
		month_name = month_abbr[month - 1]
	for day in range(start_day, end_day):
		if get_att_map_key:
			days.append(str(day+1)+ "/"+str(month))
		else:
			date = str(year) + "-" + str(month)+ "-" + str(day+1)
			day_name = day_abbr[getdate(date).weekday()]
			day_name += "," if add_month else ''
			days.append(cstr(day+1)+ " " +day_name + " "+ month_name +"::100")
	return days

def get_attendance_list(conditions, filters):
	attendance_list = frappe.db.sql("""select employee,
		CONCAT(day(attendance_date),"/",month(attendance_date)) as date_of_attendance,
		status, leave_type, remaining_half_day_status from tabAttendance where docstatus = 1 {conditions} order by employee, attendance_date""".format(conditions=conditions)
		,filters, as_dict=1)

	att_map = {}
	for d in attendance_list:
		att_map.setdefault(d.employee, frappe._dict()).setdefault(str(d.date_of_attendance), "")
		att_map[d.employee][d.date_of_attendance] = [d.status, d.leave_type, d.remaining_half_day_status]

	return att_map

def get_conditions(filters):
	conditions = " and attendance_date BETWEEN %(from_date)s and %(to_date)s"

	if filters.get("company"): conditions += " and company = %(company)s"
	if filters.get("employee"): conditions += " and employee = %(employee)s"

	return conditions, filters

def get_employee_details(group_by, company):
	emp_map = {}
	query = """select name, employee_name, designation, department, branch, company,
		holiday_list from `tabEmployee` where company = %s """ % frappe.db.escape(company)

	if group_by:
		group_by = group_by.lower()
		query += " order by " + group_by + " ASC"

	employee_details = frappe.db.sql(query , as_dict=1)

	group_by_parameters = []
	if group_by:

		group_by_parameters = list(set(detail.get(group_by, "") for detail in employee_details if detail.get(group_by, "")))
		for parameter in group_by_parameters:
				emp_map[parameter] = {}


	for d in employee_details:
		if group_by and len(group_by_parameters):
			if d.get(group_by, None):

				emp_map[d.get(group_by)][d.name] = d
		else:
			emp_map[d.name] = d

	if not group_by:
		return emp_map
	else:
		return emp_map, group_by_parameters

def get_holiday(holiday_list, from_date, to_date):
	holiday_map = frappe._dict()
	for d in holiday_list:
		holiday_dates = frappe.db.sql('''select CONCAT(day(holiday_date),"/",month(holiday_date)),  weekly_off from `tabHoliday`
				where parent=%s and holiday_date BETWEEN %s and %s ''', (d, getdate(from_date), getdate(to_date)))
		if d:
			holiday_map.setdefault(d, holiday_dates)

	return holiday_map

@frappe.whitelist()
def get_attendance_years():
	year_list = frappe.db.sql_list("""select distinct YEAR(attendance_date) from tabAttendance ORDER BY YEAR(attendance_date) DESC""")
	if not year_list:
		year_list = [getdate().year]

	return "\n".join(str(year) for year in year_list)
