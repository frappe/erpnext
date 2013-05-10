# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
import webnotes
from webnotes.utils import flt

def execute(filters=None):
	if not filters: filters = {}
	
	columns = get_columns()
	data = get_employees(filters)
	
	return columns, data
	
def get_columns():
	return [
		"Employee:Link/Employee:120", "Date of Birth:Date:100", "Branch:Link/Branch:120", 
		"Department:Link/Department:120", "Designation:Link/Designation:120", "Gender::60", 
		"Company:Link/Company:120"
	]
	
def get_employees(filters):
	conditions = get_conditions(filters)
	return webnotes.conn.sql("""select name, date_of_birth, branch, department, designation, 
	gender, company from tabEmployee where status = 'Active' %s""" % conditions, as_list=1)
	
def get_conditions(filters):
	conditions = ""
	if filters.get("month"):
		month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", 
			"Dec"].index(filters["month"]) + 1
		conditions += " and month(date_of_birth) = '%s'" % month
	
	if filters.get("company"): conditions += " and company = '%s'" % filters["company"]
	
	return conditions