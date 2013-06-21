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
from webnotes.utils import add_days, add_months, cstr, getdate
from webnotes import _

def get_columns(filters, trans):
	validate_filters(filters)
	
	# get conditions for based_on filter cond
	based_on_details = based_wise_colums_query(filters.get("based_on"), trans)
	# get conditions for periodic filter cond
	period_cols, period_select = period_wise_colums_query(filters, trans)
	# get conditions for grouping filter cond
	group_by_cols = group_wise_column(filters.get("group_by"))

	columns = based_on_details["based_on_cols"] + period_cols + ["Total(Qty):Float:120", "Total(Amt):Currency:120"]
	if group_by_cols:	
		columns = based_on_details["based_on_cols"] + group_by_cols + period_cols + \
			["Total(Qty):Float:120", "Total(Amt):Currency:120"] 

	conditions = {"based_on_select": based_on_details["based_on_select"], "period_wise_select": period_select, 
		"columns": columns, "group_by": based_on_details["based_on_group_by"], "grbc": group_by_cols, "trans": trans,
		"addl_tables": based_on_details["addl_tables"]}

	return conditions

def validate_filters(filters):
	for f in ["Fiscal Year", "Based On", "Period", "Company"]:
		if not filters.get(f.lower().replace(" ", "_")):
			webnotes.msgprint(f + _(" is mandatory"), raise_exception=1)
	
	if filters.get("based_on") == filters.get("group_by"):
		webnotes.msgprint("'Based On' and 'Group By' can not be same", raise_exception=1)

def get_data(filters, conditions):
	data = []
	inc, cond= '',''
	query_details =  conditions["based_on_select"] + conditions["period_wise_select"]
	
	if conditions["based_on_select"] in ["t1.project_name,", "t2.project_name,"]:
		cond = 'and '+ conditions["based_on_select"][:-1] +' IS Not NULL'

	if filters.get("group_by"):
		sel_col = ''
		ind = conditions["columns"].index(conditions["grbc"][0])

		if filters.get("group_by") == 'Item':
			sel_col = 't2.item_code'
		elif filters.get("group_by") == 'Customer':
			sel_col = 't1.customer'
		elif filters.get("group_by") == 'Supplier':
			sel_col = 't1.supplier'

		if filters.get('based_on') in ['Item','Customer','Supplier']:
			inc = 2
		else :
			inc = 1
		data1 = webnotes.conn.sql(""" select %s from `tab%s` t1, `tab%s Item` t2 %s
					where t2.parent = t1.name and t1.company = %s and t1.fiscal_year = %s and 
					t1.docstatus = 1 %s 
					group by %s 
				""" % (query_details,  conditions["trans"],  conditions["trans"], conditions["addl_tables"], "%s", 
					"%s", cond, conditions["group_by"]), (filters.get("company"), 
					filters["fiscal_year"]),as_list=1)

		for d in range(len(data1)):
			#to add blanck column
			dt = data1[d]
			dt.insert(ind,'')  
			data.append(dt)

			#to get distinct value of col specified by group_by in filter
			row = webnotes.conn.sql("""select DISTINCT(%s) from `tab%s` t1, `tab%s Item` t2 %s
						where t2.parent = t1.name and t1.company = %s and t1.fiscal_year = %s 
						and t1.docstatus = 1 and %s = %s 
					""" % 
					(sel_col,  conditions["trans"],  conditions["trans"], conditions["addl_tables"], 
						"%s", "%s", conditions["group_by"], "%s"),
					(filters.get("company"), filters.get("fiscal_year"), data1[d][0]), as_list=1)

			for i in range(len(row)):
				des = ['' for q in range(len(conditions["columns"]))]
				
				#get data for group_by filter 
				row1 = webnotes.conn.sql(""" select %s , %s from `tab%s` t1, `tab%s Item` t2 %s
							where t2.parent = t1.name and t1.company = %s and t1.fiscal_year = %s 
							and t1.docstatus = 1 and %s = %s and %s = %s 
						""" % 
						(sel_col, conditions["period_wise_select"], conditions["trans"], 
						 	conditions["trans"], conditions["addl_tables"], "%s", "%s", sel_col, 
							"%s", conditions["group_by"], "%s"), 
						(filters.get("company"), filters.get("fiscal_year"), row[i][0], 
							data1[d][0]), as_list=1)

				des[ind] = row[i]
				for j in range(1,len(conditions["columns"])-inc):	
					des[j+inc] = row1[0][j]
					
				data.append(des)
	else:
		data = webnotes.conn.sql(""" select %s from `tab%s` t1, `tab%s Item` t2 %s
					where t2.parent = t1.name and t1.company = %s and t1.fiscal_year = %s and 
					t1.docstatus = 1 %s 
					group by %s	
				""" % 
				(query_details, conditions["trans"], conditions["trans"], conditions["addl_tables"], 
					"%s", "%s", cond,conditions["group_by"]), 
				(filters.get("company"), filters.get("fiscal_year")), as_list=1)

	return data

def get_mon(dt):
	return getdate(dt).strftime("%b")

def period_wise_colums_query(filters, trans):
	query_details = ''
	pwc = []
	bet_dates = get_period_date_ranges(filters.get("period"), filters.get("fiscal_year"))

	if trans in ['Purchase Receipt', 'Delivery Note', 'Purchase Invoice', 'Sales Invoice']:
		trans_date = 'posting_date'
	else:
		trans_date = 'transaction_date'
	
	if filters.get("period") != 'Yearly':
		for dt in bet_dates:
			get_period_wise_columns(dt, filters.get("period"), pwc)
			query_details = get_period_wise_query(dt, trans_date, query_details)
	else:
		pwc = [filters.get("fiscal_year") + " (Qty):Float:120", 
			filters.get("fiscal_year") + " (Amt):Currency:120"]
		query_details = " SUM(t2.qty), SUM(t1.grand_total),"

	query_details += 'SUM(t2.qty), SUM(t1.grand_total)'
	return pwc, query_details

def get_period_wise_columns(bet_dates, period, pwc):
	if period == 'Monthly':
		pwc += [get_mon(bet_dates[0]) + " (Qty):Float:120", 
			get_mon(bet_dates[0]) + " (Amt):Currency:120"]
	else:
		pwc += [get_mon(bet_dates[0]) + "-" + get_mon(bet_dates[1]) + " (Qty):Float:120", 
			get_mon(bet_dates[0]) + "-" + get_mon(bet_dates[1]) + " (Amt):Currency:120"]

def get_period_wise_query(bet_dates, trans_date, query_details):
	query_details += """SUM(IF(t1.%(trans_date)s BETWEEN '%(sd)s' AND '%(ed)s', t2.qty, NULL)), 
					SUM(IF(t1.%(trans_date)s BETWEEN '%(sd)s' AND '%(ed)s', t1.grand_total, NULL)),
				""" % {"trans_date": trans_date, "sd": bet_dates[0],"ed": bet_dates[1]}
	return query_details

def get_period_date_ranges(period, fiscal_year):
  from dateutil.relativedelta import relativedelta

  year_start_date = webnotes.conn.get_value("Fiscal Year", fiscal_year, "year_start_date")
  increment = {
    "Monthly": 1,
    "Quarterly": 3,
    "Half-Yearly": 6,
    "Yearly": 12
  }.get(period)

  period_date_ranges = []
  for i in xrange(1, 13, increment): 
    period_end_date = year_start_date + relativedelta(months=increment, days=-1)
    period_date_ranges.append([year_start_date, period_end_date])
    year_start_date = period_end_date + relativedelta(days=1)

  return period_date_ranges

def get_period_month_ranges(period, fiscal_year):
	from dateutil.relativedelta import relativedelta
	period_month_ranges = []

	for start_date, end_date in get_period_date_ranges(period, fiscal_year):
		months_in_this_period = []
		while start_date <= end_date:
			months_in_this_period.append(start_date.strftime("%B"))
			start_date += relativedelta(months=1)
		period_month_ranges.append(months_in_this_period)

	return period_month_ranges

def based_wise_colums_query(based_on, trans):
	based_on_details = {}

	# based_on_cols, based_on_select, based_on_group_by, addl_tables
	if based_on == "Item":
		based_on_details["based_on_cols"] = ["Item:Link/Item:120", "Item Name:Data:120"]
		based_on_details["based_on_select"] = "t2.item_code, t2.item_name," 
		based_on_details["based_on_group_by"] = 't2.item_code'
		based_on_details["addl_tables"] = ''

	elif based_on == "Item Group":
		based_on_details["based_on_cols"] = ["Item Group:Link/Item Group:120"]
		based_on_details["based_on_select"] = "t2.item_group," 
		based_on_details["based_on_group_by"] = 't2.item_group'
		based_on_details["addl_tables"] = ''

	elif based_on == "Customer":
		based_on_details["based_on_cols"] = ["Customer:Link/Customer:120", "Territory:Link/Territory:120"]
		based_on_details["based_on_select"] = "t1.customer_name, t1.territory, "
		based_on_details["based_on_group_by"] = 't1.customer_name'
		based_on_details["addl_tables"] = ''

	elif based_on == "Customer Group":
		based_on_details["based_on_cols"] = ["Customer Group:Link/Customer Group"]
		based_on_details["based_on_select"] = "t1.customer_group,"
		based_on_details["based_on_group_by"] = 't1.customer_group'
		based_on_details["addl_tables"] = ''

	elif based_on == 'Supplier':
		based_on_details["based_on_cols"] = ["Supplier:Link/Supplier:120", "Supplier Type:Link/Supplier Type:140"]
		based_on_details["based_on_select"] = "t1.supplier, t3.supplier_type,"
		based_on_details["based_on_group_by"] = 't1.supplier'
		based_on_details["addl_tables"] = ',`tabSupplier` t3'
	
	elif based_on == 'Supplier Type':
		based_on_details["based_on_cols"] = ["Supplier Type:Link/Supplier Type:140"]
		based_on_details["based_on_select"] = "t3.supplier_type,"
		based_on_details["based_on_group_by"] = 't3.supplier_type'
		based_on_details["addl_tables"] =',`tabSupplier` t3'

	elif based_on == "Territory":
		based_on_details["based_on_cols"] = ["Territory:Link/Territory:120"]
		based_on_details["based_on_select"] = "t1.territory,"
		based_on_details["based_on_group_by"] = 't1.territory'
		based_on_details["addl_tables"] = ''

	elif based_on == "Project":
		if trans in ['Sales Invoice', 'Delivery Note', 'Sales Order']:
			based_on_details["based_on_cols"] = ["Project:Link/Project:120"]
			based_on_details["based_on_select"] = "t1.project_name,"
			based_on_details["based_on_group_by"] = 't1.project_name'
			based_on_details["addl_tables"] = ''
		elif trans in ['Purchase Order', 'Purchase Invoice', 'Purchase Receipt']:
			based_on_details["based_on_cols"] = ["Project:Link/Project:120"]
			based_on_details["based_on_select"] = "t2.project_name,"
			based_on_details["based_on_group_by"] = 't2.project_name'
			based_on_details["addl_tables"] = ''
		else:
			webnotes.msgprint("Project-wise data is not available for Quotation", raise_exception=1)

	return based_on_details

def group_wise_column(group_by):
	if group_by:
		return [group_by+":Link/"+group_by+":120"]
	else:
		return []