# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	if not filters: filters = {}
	columns = get_columns()
	data = get_employees(filters)
	chart=get_chart_data(data)

	return columns, data, None, chart

def get_columns():
	return [
		_("Employee") + ":Link/Employee:120", _("Name") + ":Data:200", _("Date of Birth")+ ":Date:100",
		_("Branch") + ":Link/Branch:120", _("Department") + ":Link/Department:120",
		_("Designation") + ":Link/Designation:120", _("Gender") + "::60", _("Company") + ":Link/Company:120"
	]

def get_employees(filters):
	conditions = get_conditions(filters)
	return frappe.db.sql("""select name, employee_name, date_of_birth,
	branch, department, designation,
	gender, company from `tabEmployee` where status = 'Active' %s""" % conditions, as_list=1)
	
def get_conditions(filters):
	conditions = ""
	if filters.get("department"): conditions += " and department = '%s'" % \
		filters["department"].replace("'", "\\'")
	return conditions

def get_chart_data(data):
	labels = [row[1] for row in data]
	
	datasets = []
	if data:
		datasets.append({
			'name': 'Employee',
			'values': [1,2,3,4,5,6,7,8]
		})
	
	chart = {
		"data": {
			'labels': labels,
			'datasets': datasets
		}
	}
	chart["type"] = "line"
	return chart