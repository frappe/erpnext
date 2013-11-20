# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import flt, cstr
from webnotes import msgprint, _

def execute(filters=None):
	if not filters: filters = {}
	
	salary_slips = get_salary_slips(filters)
	columns, earning_types, ded_types = get_columns(salary_slips)
	ss_earning_map = get_ss_earning_map(salary_slips)
	ss_ded_map = get_ss_ded_map(salary_slips)
	
	
	data = []
	for ss in salary_slips:
		row = [ss.employee, ss.employee_name, ss.branch, ss.department, ss.designation, 
			ss.company, ss.month, ss.leave_withut_pay, ss.payment_days]
			
		for e in earning_types:
			row.append(ss_earning_map.get(ss.name, {}).get(e))
			
		row += [ss.arrear_amount, ss.leave_encashment_amount, ss.gross_pay]
		
		for d in ded_types:
			row.append(ss_ded_map.get(ss.name, {}).get(d))
		
		row += [ss.total_deduction, ss.net_pay]
		
		data.append(row)
	
	return columns, data
	
def get_columns(salary_slips):
	columns = [
		"Employee:Link/Employee:120", "Employee Name::140", "Branch:Link/Branch:120", 
		"Department:Link/Department:120", "Designation:Link/Designation:120",
		 "Company:Link/Company:120", "Month::80", "Leave Without pay:Float:130", 
		"Payment Days:Float:120"
	]
	
	earning_types = webnotes.conn.sql_list("""select distinct e_type from `tabSalary Slip Earning`
		where ifnull(e_modified_amount, 0) != 0 and parent in (%s)""" % 
		(', '.join(['%s']*len(salary_slips))), tuple([d.name for d in salary_slips]))
		
	ded_types = webnotes.conn.sql_list("""select distinct d_type from `tabSalary Slip Deduction`
		where ifnull(d_modified_amount, 0) != 0 and parent in (%s)""" % 
		(', '.join(['%s']*len(salary_slips))), tuple([d.name for d in salary_slips]))
		
	columns = columns + [(e + ":Link/Earning Type:120") for e in earning_types] + \
		["Arrear Amount:Currency:120", "Leave Encashment Amount:Currency:150", 
		"Gross Pay:Currency:120"] + [(d + ":Link/Deduction Type:120") for d in ded_types] + \
		["Total Deduction:Currency:120", "Net Pay:Currency:120"]

	return columns, earning_types, ded_types
	
def get_salary_slips(filters):
	conditions, filters = get_conditions(filters)
	salary_slips = webnotes.conn.sql("""select * from `tabSalary Slip` where docstatus = 1 %s""" % 
		conditions, filters, as_dict=1)
	
	if not salary_slips:
		msgprint(_("No salary slip found for month: ") + cstr(filters.get("month")) + 
			_(" and year: ") + cstr(filters.get("fiscal_year")), raise_exception=1)
	
	return salary_slips
	
def get_conditions(filters):
	conditions = ""
	if filters.get("month"):
		month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", 
			"Dec"].index(filters["month"]) + 1
		filters["month"] = month
		conditions += " and month = %(month)s"
	
	if filters.get("fiscal_year"): conditions += " and fiscal_year = %(fiscal_year)s"
	if filters.get("company"): conditions += " and company = %(company)s"
	if filters.get("employee"): conditions += " and employee = %(employee)s"
	
	return conditions, filters
	
def get_ss_earning_map(salary_slips):
	ss_earnings = webnotes.conn.sql("""select parent, e_type, e_modified_amount 
		from `tabSalary Slip Earning` where parent in (%s)""" %
		(', '.join(['%s']*len(salary_slips))), tuple([d.name for d in salary_slips]), as_dict=1)
	
	ss_earning_map = {}
	for d in ss_earnings:
		ss_earning_map.setdefault(d.parent, webnotes._dict()).setdefault(d.e_type, [])
		ss_earning_map[d.parent][d.e_type] = flt(d.e_modified_amount)
	
	return ss_earning_map

def get_ss_ded_map(salary_slips):
	ss_deductions = webnotes.conn.sql("""select parent, d_type, d_modified_amount 
		from `tabSalary Slip Deduction` where parent in (%s)""" %
		(', '.join(['%s']*len(salary_slips))), tuple([d.name for d in salary_slips]), as_dict=1)
	
	ss_ded_map = {}
	for d in ss_deductions:
		ss_ded_map.setdefault(d.parent, webnotes._dict()).setdefault(d.d_type, [])
		ss_ded_map[d.parent][d.e_type] = flt(d.d_modified_amount)
	
	return ss_ded_map