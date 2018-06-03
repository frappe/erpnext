# encoding: utf-8
# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import formatdate, getdate, flt, add_days
from datetime import datetime
from frappe.utils import cint, cstr, date_diff, flt, formatdate, getdate, get_link_to_form, \
	comma_or, get_fullname, add_years, add_months, add_days, nowdate
from erpnext.hr.doctype.leave_application.leave_application import get_monthly_accumulated_leave
import datetime
# import operator
import re
from datetime import date
from dateutil.relativedelta import relativedelta


def execute(filters=None):
	columns, data = get_columns(filters), get_data(filters)
	return columns, data

def get_columns(filters):
	return [
		_("Employee") + ":Link/Employee:150",
		_("Employee Name") + "::150",
		# _("Annual Leave AB") + "::150",
		_("Annual Leave - اجازة اعتيادية") + "::150",
		_("Compensatory off - تعويضية") + "::150",
		_("Death - وفاة") + "::150",
		_("Educational - تعليمية") + "::150",
		_("emergency -اضطرارية") + "::150",
		_("Hajj leave - حج") + "::150",
		_("Marriage - زواج") + "::150",
		_("New Born - مولود جديد") + "::150",
		_("Sick Leave - مرضية") + "::150"

		]



# def get_conditions(filters):
# 	conditions = ""

# 	if filters.get("asset_category"): conditions += " and asset_category= '{0}' ".format(filters.get("asset_category"))

# 	# if filters.get("employee"): conditions += " and employee = %(employee)s"

# 	# if filters.get("from_date"): conditions += " and date_of_joining>=%(from_date)s"
# 	# if filters.get("to_date"): conditions += " and date_of_joining<=%(to_date)s"

# 	return conditions


def get_data(filters):
	data =[]
	# conditions = get_conditions(filters)
	li_list=frappe.db.sql(""" select DISTINCT employee, employee_name, from_date, leave_type from `tabLeave Allocation` order by creation desc """,as_dict=1)

	for leave in li_list:
		remain_annual = frappe.db.sql(""" select (select total_leaves_allocated from `tabLeave Allocation` where employee='{0}' and leave_type = 'Annual Leave - اجازة اعتيادية' and docstatus =1 order by creation desc limit 1 ) - ( select SUM(total_leave_days) from `tabLeave Application` where employee='{0}' and leave_type='Annual Leave - اجازة اعتيادية' and docstatus=1  )""".format(leave.employee))
		max_annual = frappe.db.sql(""" select total_leaves_allocated from `tabLeave Allocation` where employee='{0}' and leave_type = 'Annual Leave - اجازة اعتيادية' and docstatus =1 order by creation desc limit 1 """.format(leave.employee))
		used_annual = frappe.db.sql(""" select SUM(total_leave_days) from `tabLeave Application` where employee='{0}' and leave_type='Annual Leave - اجازة اعتيادية' and docstatus=1 """.format(leave.employee))
		
		annual_ab = get_monthly_accumulated_leave(leave.from_date, nowdate(), leave.leave_type, leave.employee, for_report=True)

		remain_compensatory = frappe.db.sql(""" select (select total_leaves_allocated from `tabLeave Allocation` where employee='{0}' and leave_type = 'Compensatory off - تعويضية' and docstatus =1 order by creation desc limit 1 ) - ( select SUM(total_leave_days) from `tabLeave Application` where employee='{0}' and leave_type='Compensatory off - تعويضية' and docstatus=1  )""".format(leave.employee))
		max_compensatory = frappe.db.sql(""" select total_leaves_allocated from `tabLeave Allocation` where employee='{0}' and leave_type = 'Compensatory off - تعويضية' and docstatus =1 order by creation desc limit 1 """.format(leave.employee))
		used_compensatory = frappe.db.sql(""" select SUM(total_leave_days) from `tabLeave Application` where employee='{0}' and leave_type='Compensatory off - تعويضية' and docstatus=1 """.format(leave.employee))
		
		remain_educational= frappe.db.sql(""" select (select total_leaves_allocated from `tabLeave Allocation` where employee='{0}' and leave_type = 'Educational - تعليمية' and docstatus =1 order by creation desc limit 1 ) - ( select SUM(total_leave_days) from `tabLeave Application` where employee='{0}' and leave_type='Educational - تعليمية' and docstatus=1  )""".format(leave.employee))
		max_educational = frappe.db.sql(""" select total_leaves_allocated from `tabLeave Allocation` where employee='{0}' and leave_type = 'Educational - تعليمية' and docstatus =1 order by creation desc limit 1 """.format(leave.employee))
		used_educational= frappe.db.sql(""" select SUM(total_leave_days) from `tabLeave Application` where employee='{0}' and leave_type='Educational - تعليمية' and docstatus=1 """.format(leave.employee))
		
		remain_emergency = frappe.db.sql(""" select (select total_leaves_allocated from `tabLeave Allocation` where employee='{0}' and leave_type = 'emergency -اضطرارية' and docstatus =1 order by creation desc limit 1 ) - ( select SUM(total_leave_days) from `tabLeave Application` where employee='{0}' and leave_type='emergency -اضطرارية' and docstatus=1  )""".format(leave.employee))
		max_emergency = frappe.db.sql(""" select total_leaves_allocated from `tabLeave Allocation` where employee='{0}' and leave_type = 'emergency -اضطرارية' and docstatus =1 order by creation desc limit 1 """.format(leave.employee))
		used_emergency = frappe.db.sql(""" select SUM(total_leave_days) from `tabLeave Application` where employee='{0}' and leave_type='emergency -اضطرارية' and docstatus=1 """.format(leave.employee))
		
		remain_death = frappe.db.sql(""" select (select total_leaves_allocated from `tabLeave Allocation` where employee='{0}' and leave_type = 'Death - وفاة' and docstatus =1 order by creation desc limit 1 ) - ( select SUM(total_leave_days) from `tabLeave Application` where employee='{0}' and leave_type='Death - وفاة' and docstatus=1  )""".format(leave.employee))
		max_death = frappe.db.sql(""" select total_leaves_allocated from `tabLeave Allocation` where employee='{0}' and leave_type = 'Death - وفاة' and docstatus =1 order by creation desc limit 1 """.format(leave.employee))
		used_death = frappe.db.sql(""" select SUM(total_leave_days) from `tabLeave Application` where employee='{0}' and leave_type='Death - وفاة' and docstatus=1 """.format(leave.employee))
		
		remain_hajj = frappe.db.sql(""" select (select total_leaves_allocated from `tabLeave Allocation` where employee='{0}' and leave_type = 'Hajj leave - حج' and docstatus =1 order by creation desc limit 1 ) - ( select SUM(total_leave_days) from `tabLeave Application` where employee='{0}' and leave_type='Hajj leave - حج' and docstatus=1  )""".format(leave.employee))
		max_hajj  = frappe.db.sql(""" select total_leaves_allocated from `tabLeave Allocation` where employee='{0}' and leave_type = 'Hajj leave - حج' and docstatus =1 order by creation desc limit 1 """.format(leave.employee))
		used_hajj  = frappe.db.sql(""" select SUM(total_leave_days) from `tabLeave Application` where employee='{0}' and leave_type='Hajj leave - حج' and docstatus=1 """.format(leave.employee))
		
		remain_marriage = frappe.db.sql(""" select (select total_leaves_allocated from `tabLeave Allocation` where employee='{0}' and leave_type = 'Marriage - زواج' and docstatus =1 order by creation desc limit 1 ) - ( select SUM(total_leave_days) from `tabLeave Application` where employee='{0}' and leave_type='Marriage - زواج' and docstatus=1  )""".format(leave.employee))
		max_marriage  = frappe.db.sql(""" select total_leaves_allocated from `tabLeave Allocation` where employee='{0}' and leave_type = 'Marriage - زواج' and docstatus =1 order by creation desc limit 1 """.format(leave.employee))
		used_marriage  = frappe.db.sql(""" select SUM(total_leave_days) from `tabLeave Application` where employee='{0}' and leave_type='Marriage - زواج' and docstatus=1 """.format(leave.employee))
		
		remain_newborn = frappe.db.sql(""" select (select total_leaves_allocated from `tabLeave Allocation` where employee='{0}' and leave_type = 'New Born - مولود جديد' and docstatus =1 order by creation desc limit 1 ) - ( select SUM(total_leave_days) from `tabLeave Application` where employee='{0}' and leave_type='New Born - مولود جديد' and docstatus=1  )""".format(leave.employee))
		max_newborn = frappe.db.sql(""" select total_leaves_allocated from `tabLeave Allocation` where employee='{0}' and leave_type = 'New Born - مولود جديد' and docstatus =1 order by creation desc limit 1 """.format(leave.employee))
		used_newborn = frappe.db.sql(""" select SUM(total_leave_days) from `tabLeave Application` where employee='{0}' and leave_type='New Born - مولود جديد' and docstatus=1 """.format(leave.employee))
		
		remain_sick = frappe.db.sql(""" select (select total_leaves_allocated from `tabLeave Allocation` where employee='{0}' and leave_type = 'Sick Leave - مرضية' and docstatus =1 order by creation desc limit 1 ) - ( select SUM(total_leave_days) from `tabLeave Application` where employee='{0}' and leave_type='Sick Leave - مرضية' and docstatus=1  )""".format(leave.employee))
		max_sick = frappe.db.sql(""" select total_leaves_allocated from `tabLeave Allocation` where employee='{0}' and leave_type = 'Sick Leave - مرضية' and docstatus =1 order by creation desc limit 1 """.format(leave.employee))
		used_sick = frappe.db.sql(""" select SUM(total_leave_days) from `tabLeave Application` where employee='{0}' and leave_type='Sick Leave - مرضية' and docstatus=1 """.format(leave.employee))

	

		row = [
		leave.employee,
		leave.employee_name,
		annual_ab if annual_ab else 0,
		remain_annual if used_annual[0][0] else max_annual,
		remain_compensatory if used_compensatory[0][0] else max_compensatory,
		remain_death if used_death[0][0] else max_death,
		remain_educational if used_educational[0][0] else max_educational,
        remain_emergency if used_emergency[0][0] else max_emergency,
        remain_hajj if used_hajj[0][0] else max_hajj,
        remain_marriage if used_marriage[0][0] else max_marriage,
        remain_newborn if used_newborn[0][0] else max_newborn,
        remain_sick if used_sick[0][0] else max_sick,
    	]
		data.append(row)
		

	return data


