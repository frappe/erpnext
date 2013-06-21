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
	
	# based_on_cols, based_on_select, based_on_group_by, addl_tables
	bonc, query_bon, based, sup_tab = basedon_wise_colums_query(filters.get("based_on"), trans)
	# period_cols, period_select
	pwc, query_pwc = period_wise_colums_query(filters, trans)
	
	# group_by_cols
	grbc = group_wise_column(filters.get("group_by"))

	columns = bonc + pwc + ["TOTAL(Qty):Float:120", "TOTAL(Amt):Currency:120"]
	if grbc:	
		columns = bonc + grbc + pwc +["TOTAL(Qty):Float:120", "TOTAL(Amt):Currency:120"] 

	# conditions
	details = {"query_bon": query_bon, "query_pwc": query_pwc, "columns": columns, 
		"basedon": based, "grbc": grbc, "sup_tab": sup_tab}

	return details

def validate_filters(filters):
	for f in ["Fiscal Year", "Based On", "Period", "Company"]:
		if not filters.get(f.lower().replace(" ", "_")):
			webnotes.msgprint(f + _(" is mandatory"), raise_exception=1)
	
	if filters.get("based_on") == filters.get("group_by"):
		webnotes.msgprint("'Based On' and 'Group By' can not be same", raise_exception=1)

def get_data(filters, tab, details):
	data = []
	inc, cond= '',''
	query_details =  details["query_bon"] + details["query_pwc"]
	
	if details["query_bon"] in ["t1.project_name,", "t2.project_name,"]:
		cond = 'and '+ details["query_bon"][:-1] +' IS Not NULL'

	if filters.get("group_by"):
		sel_col = ''
		ind = details["columns"].index(details["grbc"][0])

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

		data1 = webnotes.conn.sql(""" select %s from `%s` t1, `%s` t2 %s
					where t2.parent = t1.name and t1.company = %s 
					and t1.fiscal_year = %s and t1.docstatus = 1 %s 
					group by %s 
				""" % (query_details, tab[0], tab[1], details["sup_tab"], "%s", 
					"%s", cond, details["basedon"]), (filters.get("company"), 
					filters["fiscal_year"]),
			as_list=1)

		for d in range(len(data1)):
			#to add blanck column
			dt = data1[d]
			dt.insert(ind,'')  
			data.append(dt)

			#to get distinct value of col specified by group_by in filter
			row = webnotes.conn.sql("""select DISTINCT(%s) from `%s` t1, `%s` t2 %s
						where t2.parent = t1.name and t1.company = %s and t1.fiscal_year = %s 
						and t1.docstatus = 1 and %s = %s 
					"""%(sel_col, tab[0], tab[1], details["sup_tab"], "%s", "%s", details["basedon"], "%s"),
						(filters.get("company"), filters.get("fiscal_year"), data1[d][0]), 
				as_list=1)

			for i in range(len(row)):
				des = ['' for q in range(len(details["columns"]))]
				
				#get data for each group_by filter 
				row1 = webnotes.conn.sql(""" select %s , %s from `%s` t1, `%s` t2 %s
							where t2.parent = t1.name and t1.company = %s and t1.fiscal_year = %s 
							and t1.docstatus = 1 and %s = %s and %s = %s 
						""" % (sel_col, details["query_pwc"], tab[0], tab[1], details["sup_tab"], 
							"%s", "%s", sel_col, "%s", details["basedon"], "%s"), 
							(filters.get("company"), filters.get("fiscal_year"), 
							row[i][0], data1[d][0]), as_list=1)

				des[ind] = row[i]
				for j in range(1,len(details["columns"])-inc):	
					des[j+inc] = row1[0][j]
					
				data.append(des)
	else:
		data = webnotes.conn.sql(""" select %s from `%s` t1, `%s` t2 %s
					where t2.parent = t1.name and t1.company = %s 
					and t1.fiscal_year = %s and t1.docstatus = 1 %s 
					group by %s	
				"""%(query_details, tab[0], tab[1], details["sup_tab"], "%s", 
					"%s", cond,details["basedon"]), (filters.get("company"), 
					filters.get("fiscal_year")), 
			as_list=1)

	return data

def get_mon(dt):
	return getdate(dt).strftime("%b")

def period_wise_colums_query(filters, trans):
	query_details = ''
	pwc = []
	ysd = webnotes.conn.get_value("Fiscal year", filters.get("fiscal_year"), "year_start_date")

	if trans in ['Purchase Receipt', 'Delivery Note', 'Purchase Invoice', 'Sales Invoice']:
		trans_date = 'posting_date'
	else:
		trans_date = 'transaction_date'

	if filters.get("period") == "Monthly":
		month_name = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

		for month_idx in range(ysd.month-1,len(month_name)) + range(0, ysd.month-1):
			query_details = get_monthly_conditions(month_name, month_idx, trans_date, 
				pwc, query_details)
	
	elif filters.get("period") == "Quarterly":

		first_qsd, second_qsd, third_qsd, fourth_qsd = ysd, add_months(ysd,3), add_months(ysd,6), add_months(ysd,9)
		first_qed, second_qed, third_qed, fourth_qed = add_days(add_months(first_qsd,3),-1), add_days(add_months(second_qsd,3),-1), add_days(add_months(third_qsd,3),-1), add_days(add_months(fourth_qsd,3),-1)
		bet_dates = [[first_qsd,first_qed],[second_qsd,second_qed],[third_qsd,third_qed],[fourth_qsd,fourth_qed]] 
		
		pwc = [get_mon(first_qsd)+"-"+get_mon(first_qed)+" (Qty):Float:120", get_mon(first_qsd)+"-"+get_mon(first_qed)+"(Amt):Currency:120", 
			get_mon(second_qsd)+"-"+get_mon(second_qed)+" (Qty):Float:120", get_mon(second_qsd)+"-"+get_mon(second_qed)+" (Amt):Currency:120", 
			get_mon(third_qsd)+"-"+get_mon(third_qed)+" (Qty):Float:120", get_mon(third_qsd)+"-"+get_mon(third_qed)+" (Amt):Currency:120", 
			get_mon(fourth_qsd)+"-"+get_mon(fourth_qed)+" (Qty):Float:120", get_mon(fourth_qsd)+"-"+get_mon(fourth_qed)+" (Amt):Currency:120"]

		for d in bet_dates:
			query_details += """
				SUM(IF(t1.%(trans)s BETWEEN '%(sd)s' AND '%(ed)s', t2.qty, NULL)), 
				SUM(IF(t1.%(trans)s BETWEEN '%(sd)s' AND '%(ed)s', t1.grand_total, NULL)),
			"""%{"trans": trans_date, "sd": d[0],"ed": d[1]}

	elif filters.get("period") == "Half-yearly":

		first_half_start = ysd
		first_half_end = add_days(add_months(first_half_start,6),-1)
		second_half_start = add_days(first_half_end,1)
		second_half_end = add_days(add_months(second_half_start,6),-1)

		pwc = [get_mon(first_half_start)+"-"+get_mon(first_half_end)+"(Qty):Float:120", get_mon(first_half_start)+"-"+get_mon(first_half_end)+" (Amt):Currency:120",
		 	get_mon(second_half_start)+"-"+get_mon(second_half_end)+" (Qty):Float:120",	get_mon(second_half_start)+"-"+get_mon(second_half_end)+" (Amt):Currency:120"]

		query_details = """ 
			 	SUM(IF(t1.%(trans)s BETWEEN '%(fhs)s' AND '%(fhe)s', t2.qty, NULL)),
			 	SUM(IF(t1.%(trans)s BETWEEN '%(fhs)s' AND '%(fhe)s', t1.grand_total, NULL)), 
			 	SUM(IF(t1.%(trans)s BETWEEN '%(shs)s' AND '%(she)s', t2.qty, NULL)), 
			 	SUM(IF(t1.%(trans)s BETWEEN '%(shs)s' AND '%(she)s', t1.grand_total, NULL)),
			"""%{"trans": trans_date, "fhs": first_half_start, "fhe": first_half_end,"shs": second_half_start, 
		"she": second_half_end}	 
	
	else:
		pwc = [filters.get("fiscal_year")+" (Qty):Float:120", filters.get("fiscal_year")+" (Amt):Currency:120"]
		query_details = " SUM(t2.qty), SUM(t1.grand_total),"

	query_details += 'SUM(t2.qty), SUM(t1.grand_total)'
	return pwc, query_details
	
def get_monthly_conditions(month_list, month_idx, trans_date, pwc, query_details):
	pwc += [month_list[month_idx] + ' (Qty):Float:120', 
		month_list[month_idx] + ' (Amt):Currency:120']

	query_details += """
		Sum(IF(MONTH(t1.%(trans_date)s)= %(mon_num)s, t2.qty, NULL)),
		SUM(IF(MONTH(t1.%(trans_date)s)= %(mon_num)s, t1.grand_total, NULL)),
	""" % {"trans_date": trans_date, "mon_num": cstr(month_idx+1)}
	
	return query_details

def basedon_wise_colums_query(based_on, trans):
	sup_tab = ''

	if based_on == "Item":
		bon = ["Item:Link/Item:120", "Item Name:Data:120"]
		query_details = "t2.item_code, t2.item_name," 
		based = 't2.item_code'

	elif based_on == "Item Group":
		bon = ["Item Group:Link/Item Group:120"]
		query_details = "t2.item_group," 
		based = 't2.item_group'

	elif based_on == "Customer":
		bon = ["Customer:Link/Customer:120", "Territory:Link/Territory:120"]
		query_details = "t1.customer_name, t1.territory, "
		based = 't1.customer_name'

	elif based_on == "Customer Group":
		bon = ["Customer Group:Link/Customer Group"]
		query_details = "t1.customer_group,"
		based = 't1.customer_group'
	
	elif based_on == 'Supplier':
		bon = ["Supplier:Link/Supplier:120", "Supplier Type:Link/Supplier Type:120"]
		query_details = "t1.supplier, t3.supplier_type,"
		based = 't1.supplier'
		sup_tab = '`tabSupplier` t3',
	
	elif based_on == 'Supplier Type':
		bon = ["Supplier Type:Link/Supplier Type:120"]
		query_details = "t3.supplier_type,"
		based = 't3.supplier_type'
		sup_tab ='`tabSupplier` t3',

	elif based_on == "Territory":
		bon = ["Territory:Link/Territory:120"]
		query_details = "t1.territory,"
		based = 't1.territory'

	elif based_on == "Project":
		if trans in ['Sales Invoice', 'Delivery Note', 'Sales Order']:
			bon = ["Project:Link/Project:120"]
			query_details = "t1.project_name,"
			based = 't1.project_name'
		elif trans in ['Purchase Order', 'Purchase Invoice', 'Purchase Receipt']:
			bon = ["Project:Link/Project:120"]
			query_details = "t2.project_name,"
			based = 't2.project_name'
		else:
			webnotes.msgprint("Project-wise data is not available for Quotation", raise_exception=1)

	return bon, query_details, based, sup_tab

def group_wise_column(group_by):
	if group_by:
		return [group_by+":Link/"+group_by+":120"]
	else:
		return []