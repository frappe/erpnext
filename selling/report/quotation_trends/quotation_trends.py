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
from webnotes.utils import cint, add_days, add_months, cstr

def execute(filters=None):
	if not filters: filters ={}

	# Global data
	trans = "Quotation"
	tab = ["tabQuotation","tabQuotation Item"]
	ysd = webnotes.conn.sql("select year_start_date from `tabFiscal Year` where name = '%s'"%filters.get("fiscal_year"))[0][0]
	year_start_date = ysd.strftime('%Y-%m-%d')
	start_month = cint(year_start_date.split('-')[1])

	columns, query_bon, query_pwc, group_by, gby = get_columns(filters, year_start_date, start_month, trans)
	data = get_data(columns,filters, tab, query_bon, query_pwc, group_by, gby)

	return columns, data 

def get_columns(filters, year_start_date, start_month, trans):
	columns, pwc, bon, gby = [], [], [], []
	query_bon, query_pwc = '', ''

	period = filters.get("period")
	based_on = filters.get("based_on")
	grby = filters.get("group_by")

	if not (period and based_on):
		webnotes.msgprint("Value missing in 'Period' or 'Based On'", raise_exception=1)

	elif based_on == grby:
		webnotes.msgprint("Plese select different values in 'Based On' and 'Group By'", raise_exception=1)

	else: 
		bon,query_bon,group_by = base_wise_column(based_on, bon)
		pwc,query_pwc = period_wise_column_and_query(filters, period, pwc, year_start_date,start_month, trans)
		gby = gruoup_wise_column(grby)
	
	if gby:	
		columns = bon + gby + pwc +["TOTAL(Qty):Float:120", "TOTAL(Amt):Currency:120"] 
	else:
		columns = bon + pwc + ["TOTAL(Qty):Float:120", "TOTAL(Amt):Currency:120"]

	return columns, query_bon, query_pwc, group_by,gby

def get_data(columns, filters, tab,  query_bon, query_pwc, group_by,gby):
	
	query_details =  query_bon + query_pwc + 'SUM(t2.qty), SUM(t1.grand_total) '
	query_pwc = query_pwc + 'SUM(t2.qty), SUM(t1.grand_total)'
	data = []
	inc = ''

	if filters.get("group_by"):
		sel_col = ''
		if filters.get("group_by") == 'Item':
			sel_col = 't2.item_code'

		elif filters.get("group_by") == 'Customer':
			sel_col = 't1.customer'

		if filters.get('based_on') in ['Item','Customer']:
			inc = 2
		else :
			inc = 1

		ind = columns.index(gby[0])

		data1 = webnotes.conn.sql(""" select %s %s from `%s` t1, `%s` t2 
			where t2.parent = t1.name and t1.company = '%s' and t1.fiscal_year = '%s' 
			and t1.docstatus = 1 group by %s """%(query_bon, query_pwc, tab[0], tab[1], 
			filters.get("company"), filters.get("fiscal_year"), group_by), as_list=1)

		for d in range(len(data1)):

			dt = data1[d]
			dt.insert(ind,'')
			data.append(dt)

			row = webnotes.conn.sql("""select DISTINCT(%s) from `%s` t1, `%s` t2 
				where t2.parent = t1.name and t1.company = '%s' and t1.fiscal_year = '%s' 
				and t1.docstatus = 1 and %s = '%s' """%(sel_col, tab[0], tab[1], filters.get("company"), 
				filters.get("fiscal_year"), group_by, data1[d][0]),as_list=1)
			
			for i in range(len(row)):
				des = ['' for q in range(len(columns))]

				row1 = webnotes.conn.sql(""" select %s , %s from `%s` t1, `%s` t2 
					where t2.parent = t1.name and t1.company = '%s' and t1.fiscal_year = '%s' 
					and t1.docstatus = 1 and %s = '%s' and %s ='%s' """%(sel_col, query_pwc, tab[0], tab[1], 
					filters.get("company"), filters.get("fiscal_year"),  sel_col, row[i][0], group_by, 
					data1[d][0]),as_list=1)

				des[ind] = row[i]
				for j in range(1,len(columns)-inc):	
					des[j+inc] = row1[0][j]
				data.append(des)
	else:

		data = webnotes.conn.sql(""" select %s from `%s` t1, `%s` t2 
			where t2.parent = t1.name and t1.company = '%s' and t1.fiscal_year = '%s' 
			and t1.docstatus = 1 group by %s	
		"""%(query_details, tab[0], tab[1], filters.get("company"), filters.get("fiscal_year"), group_by), as_list=1)

	return data

def period_wise_column_and_query(filters, period, pwc, year_start_date, start_month, trans):
	query_details = ''
	if trans in ['Purchase Receipt', 'Delivery Note', 'Purchase Invoice', 'Sales Invoice']:
		trans_date = 'posting_date'
	else:
		trans_date = 'transaction_date'

	if period == "Monthly":
		month_name = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

		for month in range(start_month-1,len(month_name)):
			pwc.append(month_name[month]+' (Qty):Float:120')
			pwc.append(month_name[month]+' (Amt):Currency:120')

			query_details += """
				Sum(CASE WHEN MONTH(t1.%(trans)s)= %(mon_num)s THEN t2.qty ELSE NULL END),
				SUM(CASE WHEN MONTH(t1.%(trans)s)= %(mon_num)s THEN t1.grand_total ELSE NULL END),
			"""%{"trans": trans_date,"mon_num": cstr(month+1)}

		for month in range(0, start_month-1):
			pwc.append(month_name[month]+' (Qty):Float:120')
			pwc.append(month_name[month]+' (Amt):Currency:120')

			query_details += """
				Sum(CASE WHEN MONTH(t1.%(trans)s)= %(mon_num)s THEN t2.qty ELSE NULL END),
				SUM(CASE WHEN MONTH(t1.%(trans)s)= %(mon_num)s THEN t1.grand_total ELSE NULL END),
			"""%{"trans": trans_date, "mon_num": cstr(month+1)}
	
	elif period == "Quarterly":
		pwc = ["Q1(qty):Float:120", "Q1(amt):Currency:120", "Q2(qty):Float:120", "Q2(amt):Currency:120", 
		"Q3(qty):Float:120", "Q3(amt):Currency:120", "Q4(qty):Float:120", "Q4(amt):Currency:120"]

		first_qsd, second_qsd, third_qsd, fourth_qsd = year_start_date, add_months(year_start_date,3), add_months(year_start_date,6), add_months(year_start_date,9)
		first_qed, second_qed, third_qed, fourth_qed = add_days(add_months(first_qsd,3),-1), add_days(add_months(second_qsd,3),-1), add_days(add_months(third_qsd,3),-1), add_days(add_months(fourth_qsd,3),-1)

		bet_dates = [[first_qsd,first_qed],[second_qsd,second_qed],[third_qsd,third_qed],[fourth_qsd,fourth_qed]] 
		for d in bet_dates:
			query_details += """
				SUM(CASE WHEN t1.%(trans)s BETWEEN '%(sd)s' AND '%(ed)s' THEN t2.qty ELSE NULL END), 
				SUM(CASE WHEN t1.%(trans)s BETWEEN '%(sd)s' AND '%(ed)s' THEN t1.grand_total ELSE NULL END),
			"""%{"trans": trans_date, "sd": d[0],"ed": d[1]}

	elif period == "Half-yearly":
		pwc = ["Fisrt Half(qty):Float:120", "Fisrt Half(amt):Currency:120", "Second Half(qty):Float:120",
		 	"Second Half(amt):Currency:120"]

		first_half_start = year_start_date
		first_half_end = add_days(add_months(first_half_start,6),-1)
		second_half_start = add_days(first_half_end,1)
		second_half_end = add_days(add_months(second_half_start,6),-1)

		query_details = """ 
			 	SUM(CASE WHEN t1.%(trans)s BETWEEN '%(fhs)s' AND '%(fhe)s' THEN t2.qty ELSE NULL END),
			 	SUM(CASE WHEN t1.%(trans)s BETWEEN '%(fhs)s' AND '%(fhe)s' THEN t1.grand_total ELSE NULL END), 
			 	SUM(CASE WHEN t1.%(trans)s BETWEEN '%(shs)s' AND '%(she)s' THEN t2.qty ELSE NULL END), 
			 	SUM(CASE WHEN t1.%(trans)s BETWEEN '%(shs)s' AND '%(she)s' THEN t1.grand_total ELSE NULL END),
			"""%{"trans": trans_date, "fhs": first_half_start, "fhe": first_half_end,"shs": second_half_start, "she": second_half_end}	 
	
	else:
		pwc = [filters.get("fiscal_year")+"(qty):Float:120", filters.get("fiscal_year")+"(amt):Currency:120"]
		query_details = " SUM(t2.qty), SUM(t1.grand_total),"

	return pwc, query_details

def base_wise_column(based_on, bon):
	if based_on == "Item":
		bon = ["Item:Link/Item:120", "Item Name:Data:120"]
		query_details = "t2.item_code, t2.item_name," 
		group_by = 't2.item_code'

	elif based_on == "Item Group":
		bon = ["Item Group:Link/Item Group:120"]
		query_details = "t2.item_group," 
		group_by = 't2.item_group'

	elif based_on == "Customer":
		bon = ["Customer:Link/Customer:120", "Territory:Link/Territory:120"]
		query_details = "t1.customer_name, t1.territory, "
		group_by = 't1.customer_name'

	elif based_on == "Customer Group":
		bon = ["Customer Group:Link/Customer Group"]
		query_details = "t1.customer_group, "
		group_by = 't1.customer_group'

	elif based_on == "Territory":
		bon = ["Territory:Link/Territory:120"]
		query_details = "t1.territory, "
		group_by = 't1.territory'

	else:
		bon = ["Project:Link/Project:120"]
	return bon, query_details, group_by

def gruoup_wise_column(group_by):
	if group_by:
		return [group_by+":Link/"+group_by+":120"]
	else:
		return []