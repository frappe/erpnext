# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	if not filters:
		filters = {}
	columns, data = [], []
	data =  get_data(filters)
	if not data:
		return columns, data
	columns = get_columns(data)
	return columns, data

def get_data(filters):
	conditions, filters = get_conditions(filters)
	# data = frappe.db.sql("""
	# 	SELECT e.name, e.employee_name, e.passport_number, e.company_email, e.date_of_birth, e.cell_number, e.reports_to, e.reports_to_name,
	# 	e.department, e.division, e.section, e.employment_type, e.employee_group, e.grade, e.designation, e.employment_status, e.date_of_joining, e.status, e.increment_cycle, e.promotion_cycle, e.promotion_due_date, e.date_of_retirement, e.blood_group, ee.school_univ, ee.qualification, ee.level, ee.year_of_passing, ee.class_per, ee.maj_opt_subj
	# 	FROM `tabEmployee` e, `tabEmployee Education` as ee 
	# 	WHERE ee.parent = e.name
	# 	AND department is not null %s			
	# 	"""%conditions, filters)

	data = frappe.db.sql("""
		SELECT e.name, e.employee_name, e.passport_number, e.company_email, e.date_of_birth, e.cell_number, e.reports_to, e.reports_to_name,
		e.department, e.division, e.section, e.employment_type, e.employee_group, e.grade, e.designation, e.employment_status, e.date_of_joining, e.status, e.increment_cycle, e.promotion_cycle, e.promotion_due_date, e.date_of_retirement, e.blood_group
		FROM `tabEmployee` e
		WHERE e.department is not null %s			
		"""%conditions, filters)

	return data

def get_conditions(filters):
	conditions = ''
	if filters.get("employee"):
		conditions += " and e.name = %(employee)s"
	if filters.get("department"):
		conditions += " and e.department = %(department)s"
	if filters.get("division"):
		conditions += " and e.division = %(division)s"
	return conditions, filters

def get_columns(data):
	columns =  [
		_("Employee ID") + ":Link/Employee:120",
		_("Employee Name") + ":Data:120",
		_("CID") + ":Data:100",
		_("Email ID") + ":Data:200",
		_("Date of Birth") + ":Data:100",
		_("Mobile No.") + ":Data:100",
		_("Supervisor ID") + ":Link/Employee:120",
		_("Supervisor") + ":Data:120",
		_("Department") + ":Link/Department:120",
		_("Division") + ":Link/Division:120",
		_("Section") + ":Link/Section:120", 
		_("Employee Type") + ":Data:120", 
		_("Employee Group") + ":Data:120", 
		_("Grade") + ":Data:60", 
		_("Designation") + ":Data:120", 
		_("Employment Status") + ":Data:80",  
		_("Date of Joining") + ":Data:100", 
		_("Status") + ":Data:100", 
		_("Increment Cycle") + ":Data:100", 
		_("Promotion Cycle") + ":Data:100", 
		_("Promotion Due Date") + ":Data:100", 
		_("Date of Retirement") + ":Data:100",
		_("Blood Group") + ":Data:40",
		# _("School/University") + ":Data:120",
		# _("Qualification") + ":Data:120",
		# _("Level") + ":Data:100",
		# _("Year of Passing") + ":Data:80",
		# _("Class/Percentage") + ":Data:80",
		# _("Major") + ":Data:100",
    ]
	return columns