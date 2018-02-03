# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import msgprint, _

def execute(filters=None):
	
	columns = get_columns()
	data = []

	rows = get_data()
	for row in rows:
		data.append(row)
	return columns,data

def get_columns():
	"""return columns based on filters"""
	columns = [
		_("Item Group") + ":Data:160", 
		_("Sales Channel") + ":Data:120", 
		_("Qty(today)") + ":Int:100",
		_("Amount(today)") + ":Currency/currency:140", 
		_("Qty(this week)") + ":Int:100",
		_("Amount(this week)") + ":Currency/currency:140", 
		_("Qty(this month)") + ":Int:100",
		_("Amount(this month)") + ":Currency/currency:140",
	]
	return columns

def get_data():
	today_data = []
	week_data = []
	month_data = []
	item_groups_array = []
	today_data_res = frappe.db.sql("""
	select 
	sum(sii.qty),sum(sii.amount), sii.item_group, si.sales_channel
	from `tabSales Invoice` si,
	`tabSales Invoice Item` sii
	where sii.parent=si.name and (DAY(si.posting_date) = DAY(NOW()- INTERVAL 1 DAY) and MONTH(si.posting_date) = MONTH(NOW()- INTERVAL 1 DAY) and YEAR(si.posting_date) = YEAR(NOW()- INTERVAL 1 DAY)) and si.is_return = 1 
	group by sii.item_group,si.sales_channel
	""")
	for qty,amount,item_group,sales_channel in today_data_res:
		data_row = []
		item_group = "%s (%s)" % (str(item_group),str(sales_channel))
		data_row = data_row + [item_group,qty,amount]
		today_data.append(data_row)
		item_groups_array.append(item_group)
	
	week_data_res = frappe.db.sql("""
	select 
	sum(sii.qty),sum(sii.amount), sii.item_group, si.sales_channel
	from `tabSales Invoice` si,
	`tabSales Invoice Item` sii
	where sii.parent=si.name and (DAY(si.posting_date) = DAY(NOW()- INTERVAL 7 DAY) and MONTH(si.posting_date) = MONTH(NOW()- INTERVAL 7 DAY) and YEAR(si.posting_date) = YEAR(NOW()- INTERVAL 7 DAY)) and si.is_return = 1 
	group by sii.item_group,si.sales_channel
	""")
	for qty,amount,item_group,sales_channel in week_data_res:
		data_row = []
		item_group = "%s (%s)" % (str(item_group),str(sales_channel))
		data_row = data_row + [item_group,qty,amount]
		week_data.append(data_row)
		item_groups_array.append(item_group)
	
	month_data_res = frappe.db.sql("""
	select 
	sum(sii.qty),sum(sii.amount), sii.item_group, si.sales_channel
	from `tabSales Invoice` si,
	`tabSales Invoice Item` sii
	where sii.parent=si.name and (MONTH(si.posting_date) = MONTH(NOW()) and YEAR(si.posting_date) = YEAR(NOW()))  and si.is_return = 1 
	group by sii.item_group,si.sales_channel
	""")
	for qty,amount,item_group,sales_channel in month_data_res:
		data_row = []
		item_group = "%s (%s)" % (str(item_group),str(sales_channel))
		data_row = data_row + [item_group,qty,amount]
		month_data.append(data_row)
		item_groups_array.append(item_group)

	data = []
	total_t_qty = 0
	total_w_qty = 0
	total_m_qty = 0
	total_t_amt = 0
	total_w_amt = 0
	total_m_amt = 0
	distinct_item_groups = set(item_groups_array)
	i=0
	for item_group in distinct_item_groups:
		t_d_temp = []
		for t_d in today_data:
			if item_group in t_d:
				t_d_temp = t_d_temp+[t_d[1]]+[t_d[2]]
				total_t_qty = total_t_qty+t_d[1]
				total_t_amt = total_t_amt+t_d[2]
		if not len(t_d_temp):
			t_d_temp = t_d_temp+[0]+[0]
		w_d_temp = []
		for w_d in week_data:
			if item_group in w_d:
				w_d_temp = w_d_temp+[w_d[1]]+[w_d[2]]
				total_w_qty = total_w_qty+w_d[1]
				total_w_amt = total_w_amt+w_d[2]
		if not len(w_d_temp):
			w_d_temp = w_d_temp+[0]+[0]
		m_d_temp = []
		for m_d in month_data:
			if item_group in m_d:
				m_d_temp = m_d_temp+[m_d[1]]+[m_d[2]]
				total_m_qty = total_m_qty+m_d[1]
				total_m_amt = total_m_amt+m_d[2]
		if not len(m_d_temp):
			m_d_temp = m_d_temp+[0]+[0]
		sales_channel = item_group[item_group.find("(")+1:item_group.find(")")]
		item_group = item_group[0:item_group.find("(")]
		data.append([item_group]+[sales_channel]+t_d_temp+w_d_temp+m_d_temp)
	# data.append(["<b>Total</b>",total_t_qty,total_t_amt,total_w_qty,total_w_amt,total_m_qty,total_m_amt])
	return data
