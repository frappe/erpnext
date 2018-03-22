# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt, cstr
from frappe import msgprint, _
from erpnext.hr.doctype.salary_structure.salary_structure import make_salary_slip

def execute(filters=None):
	if not filters: filters = {}

	salary_structure = get_ss(filters)
	columns, earning_types, ded_types = get_columns(salary_structure)
	ss_earning_map = get_ss_earning_map(salary_structure)
	ss_ded_map = get_ss_ded_map(salary_structure)

	print "sssssssssssssssssssssssssssssssssssssssss"
	print ss_earning_map
	print "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
	print ss_ded_map
	print "sssssssssssssssssssssssssssssssssssssssss"

	data = []
	for ss in salary_structure:
		row = [ ss.employee, ss.employee_name, ss.department, ss.designation]
		gross =0 
		for e in earning_types:
			row.append(ss_earning_map.get(ss.name, {}).get(e))
			try : gross += ss_earning_map.get(ss.name, {}).get(e)
			except: pass
		
		row += [ gross]

		#~ for d in ded_types:
			#~ row.append(ss_ded_map.get(ss.name, {}).get(d))

		#~ row += [ss.total_deduction, ss.net_pay]

		data.append(row)

			
	

	total_col= [""]*len(columns)

	for row in data:
		for i, col in enumerate(row):
			if i >3:
				total_col[i] = flt(total_col[i]) + flt(col)
			
	for i, col in enumerate(total_col):
		if i >3:
			total_col[i] = flt(total_col[i],2)


	total_col[0]='Totals'
		
	data.append(total_col)

	return columns, data

def get_columns(salary_structure):
	columns = [_("Employee") + ":Link/Employee:120", _("Employee Name") + "::140", 
		_("Department") + ":Link/Department:120", _("Designation") + ":Link/Designation:120",
	]

	salary_components = {_("Earning"): [], _("Deduction"): []}

	for component in frappe.db.sql("""select distinct sd.salary_component, sc.type
		from `tabSalary Detail` sd, `tabSalary Component` sc
		where sc.name=sd.salary_component and sd.salary_component != "Overtime"  and sd.parent in 
		(select name from `tabSalary Structure` where is_active = "Yes") order by sd.salary_component """ , as_dict=1):
		salary_components[_(component.type)].append(component.salary_component)

	columns = columns + [(e + ":Currency:120") for e in salary_components[_("Earning")]] + \
		[ _("Gross Pay") + ":Currency:120"]

	return columns, salary_components[_("Earning")], salary_components[_("Deduction")]

def get_ss(filters):
	conditions, filters = get_conditions(filters)
	salary_structure = frappe.db.sql("""select ss.employee,ss.employee_name,ss.parent as name ,ss.parent,emp.designation,emp.department from `tabSalary Structure Employee` as ss
		join `tabEmployee` as emp 
		on ss.employee = emp.name 
		where ss.parent in (select name from `tabSalary Structure` where is_active = "Yes") 
		order by ss.employee""", as_dict=1)

	if not salary_structure:
		frappe.throw(_("No salary strcu found between {0} and {1}"))

	return salary_structure
		

def get_conditions(filters):
	conditions = ""
	if filters.get("from_date"): conditions += " and start_date >= %(from_date)s"
	if filters.get("to_date"): conditions += " and end_date <= %(to_date)s"
	if filters.get("company"): conditions += " and company = %(company)s"
	if filters.get("employee"): conditions += " and employee = %(employee)s"

	return conditions, filters

def get_ss_earning_map(salary_structure):
		
	ss_earnings = frappe.db.sql("""select parent, salary_component, amount
		from `tabSalary Detail` where parent in (%s)""" %
		(', '.join(['%s']*len(salary_structure))), tuple([d.parent for d in salary_structure]), as_dict=1)
	ss = {}
	all_er = []
	i=0
	for s in salary_structure:
		print i
		salar_slip = frappe.new_doc("Salary Slip")
		ss[s.parent]= make_salary_slip(s.parent,salar_slip, employee = s.employee)
		i+=1
		ssd = {}
		for row in salar_slip.get("earnings"): 
			all_er.append({"parent":s.parent,"salary_component":row.salary_component ,"amount":row.amount})
	
	ss_earning_map = {}	
	for d in all_er:
		ss_earning_map.setdefault(d["parent"], frappe._dict()).setdefault(d["salary_component"], [])
		ss_earning_map[d["parent"]][d["salary_component"]] = flt(d["amount"])

	return ss_earning_map

def get_ss_ded_map(salary_structure):
	ss_deductions = frappe.db.sql("""select parent, salary_component, amount
		from `tabSalary Detail` where parent in (%s)""" %
		(', '.join(['%s']*len(salary_structure))), tuple([d.parent for d in salary_structure]), as_dict=1)

	ss = {}
	all_er = []
	i=0
	for s in salary_structure:
		print i
		salar_slip = frappe.new_doc("Salary Slip")
		ss[s.parent]= make_salary_slip(s.parent,salar_slip, employee = s.employee)
		i+=1
		ssd = {}
		for row in salar_slip.get("deductions"): 
			all_er.append({"parent":s.parent,"salary_component":row.salary_component ,"amount":row.amount})

	ss_ded_map = {}
	for d in all_er:
		ss_ded_map.setdefault(d["parent"], frappe._dict()).setdefault(d["salary_component"], [])
		ss_ded_map[d["parent"]][d["salary_component"]] = flt(d["amount"])

	return ss_ded_map








