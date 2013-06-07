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
from webnotes.utils import getdate, cint

def execute(filters=None):
	if not filters: filters ={}
	
	period = filters.get("period")
	based_on = filters.get("based_on")
	group_by = filters.get("group_by")

	columns = get_columns(filters, period, based_on, group_by)
	data = [] 

	return columns, data 

def get_columns(filters, period, based_on, group_by):
	columns = []
	pwc = []
	bon = []
	gby = []

	if not (period and based_on):
		webnotes.msgprint("Value missing in 'Period' or 'Based On'",raise_exception=1)
	elif based_on == group_by:
		webnotes.msgprint("Plese select different values in 'Based On' and 'Group By'")
	else: 
		pwc = period_wise_column(filters, period, pwc)
		bon = base_wise_column(based_on, bon)
		gby = gruoup_wise_column(group_by)
	
	if gby:	
		columns = bon + gby + pwc
	else:
		columns = bon + pwc
	return columns


def period_wise_column(filters, period, pwc):

	if period == "Monthly":
		month_name = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
		for month in range(0,len(month_name)):
			pwc.append(month_name[month]+' (Qty):Float:120')
			pwc.append(month_name[month]+' (Amt):Currency:120')

	elif period == "Quarterly":
		pwc = ["Q1(qty):Float:120", "Q1(amt):Currency:120", "Q2(qty):Float:120", "Q2(amt):Currency:120", 
		"Q3(qty):Float:120", "Q3(amt):Currency:120", "Q4(qty):Float:120", "Q4(amt):Currency:120"
		]

	elif period == "Half-yearly":
		pwc = ["Fisrt Half(qty):Float:120", "Fisrt Half(amt):Currency:120", "Second Half(qty):Float:120",
		 	"Second Half(amt):Currency:120"
		]
	else:
		pwc = [filters.get("fiscal_year")+"(qty):Float:120", filters.get("fiscal_year")+"(amt):Currency:120"]

	return pwc

def base_wise_column(based_on, bon):
	if based_on == "Item":
		bon = ["Item:Link/Item:120", "Item Name:Data:120"]
	elif based_on == "Item Group":
		bon = ["Item Group:Link/Item Group:120"]
	elif based_on == "Customer":
		bon = ["Customer:Link/Customer:120", "Territory:Link/Territory:120"]
	elif based_on == "Customer Group":
		bon = ["Customer Group:Link/Customer Group"]
	elif based_on == "Territory":
		bon = ["Territory:Link/Territory:120"]
	else:
		bon = ["Project:Link/Project:120"]
	return bon

def gruoup_wise_column(group_by):
	if group_by:
		return [group_by+":Link/"+group_by+":120"]
	else:
		return []