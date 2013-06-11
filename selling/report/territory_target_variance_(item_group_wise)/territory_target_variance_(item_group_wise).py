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
import calendar
from webnotes import msgprint
from webnotes.utils import cint, cstr, add_months

def execute(filters=None):
	if not filters: filters = {}
	
	columns = get_columns(filters)

	data = []
	
	return columns, data
	
def get_columns(filters):
	"""return columns based on filters"""
	
	if not filters.get("period"):
		msgprint("Please select the Period", raise_exception=1)

	mo = cint(cstr(webnotes.conn.get_value("Fiscal Year", filters["fiscal_year"], "year_start_date")).split("-")[1])
	period_months = []
	if (filters["period"] == "Monthly" or "Yearly"):
		for x in range(0,12):
			period_months.append(mo)
			if (mo!=12):
				mo += 1
			else:
				mo = 1

	columns = ["Territory:Link/Territory:80"] + ["Item Group:Link/Item Group:80"]

	period = []

	if (filters["period"] == "Monthly" or "Yearly"):
		for i in (0,12):
			period.append("Target (" + "i" + ")::80")
			period.append("Achieved (" + "i" + ")::80")
			period.append("Variance (" + "i" + ")::80")

	columns = columns + [(p) for p in period] + \
		["Total Target::80"] + ["Total Achieved::80"] + ["Total Variance::80"]

	return columns

def get_conditions(filters):
	conditions = ""
	
	if filters.get("fiscal_year"):
		conditions += " and posting_date <= '%s'" % filters["fiscal_year"]
	else:
		webnotes.msgprint("Please enter Fiscal Year", raise_exception=1)
	
	if filters.get("target_on"):
		conditions += " and posting_date <= '%s'" % filters["target_on"]
	else:
		webnotes.msgprint("Please select Target On", raise_exception=1)

	return conditions


#get territory details
def get_territory_details(filters):
	conditions = get_conditions(filters)
	return webnotes.conn.sql("""select item_code, batch_no, warehouse, 
		posting_date, actual_qty 
		from `tabStock Ledger Entry` 
		where ifnull(is_cancelled, 'No') = 'No' %s order by item_code, warehouse""" %
		conditions, as_dict=1)

def get_month_abbr(month_number):
	return 0