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

import webnotes
from webnotes.utils import getdate, flt

def execute(filters=None):
	if not filters: filters = {}
	float_preceision = webnotes.conn.get_default("float_preceision")

	condition =get_condition(filters)

	avg_daily_outgoing = 0
	diff = ((getdate(filters.get("to_date")) - getdate(filters.get("from_date"))).days)+1
	if diff <= 0:
		webnotes.msgprint("To Date should not be less than eual to From Date",raise_exception=1)

	columns = get_columns()
	items = get_item_info()
	consumed_item_map = get_consumed_items(condition)
	delivered_item_map = get_delivered_items(condition)

	data = []
	for item in items:

		total_outgoing = consumed_item_map.get(item.name, 0)+delivered_item_map.get(item.name,0)
		avg_daily_outgoing = flt(total_outgoing/diff, float_preceision)
		reorder_level = (avg_daily_outgoing * flt(item.lead_time_days)) + flt(item.min_order_qty)

		data.append([item.name, item.item_name, item.description, item.min_order_qty, item.lead_time_days, 
			consumed_item_map.get(item.name, 0), delivered_item_map.get(item.name,0), total_outgoing, 
			avg_daily_outgoing, reorder_level])

	return columns , data

def get_columns():
	return[
			"Item:Link/Item:120", "Item name:Data:120", "Description::160",
			"Minimum Inventory Level:Float:160", "Lead Time Days:Float:120", "Consumed:Float:120", 
			"Delivered:Float:120", "Total Outgoing:Float:120", "Avg Daily Outgoing:Float:160",
			"Reorder Level:Float:120"
	]

def get_item_info():
	return webnotes.conn.sql("""select name, item_name, description, min_order_qty,
		lead_time_days	from tabItem""", as_dict=1)

def get_consumed_items(condition):

	cn_items = webnotes.conn.sql("""select se_item.item_code, 
				sum(se_item.actual_qty) as 'consume_qty'
		from `tabStock Entry` se, `tabStock Entry Detail` se_item
		where se.name = se_item.parent and se.docstatus = 1 
		and ifnull(se_item.t_warehouse, '') = '' %s
		group by se_item.item_code""" % (condition), as_dict=1)

	cn_items_map = {}
	for item in cn_items:
		cn_items_map.setdefault(item.item_code, item.consume_qty)

	return cn_items_map

def get_delivered_items(condition):

	dn_items = webnotes.conn.sql("""select dn_item.item_code, sum(dn_item.qty) as dn_qty
		from `tabDelivery Note` dn, `tabDelivery Note Item` dn_item
		where dn.name = dn_item.parent and dn.docstatus = 1 %s 
		group by dn_item.item_code""" % (condition), as_dict=1)

	si_items = webnotes.conn.sql("""select si_item.item_name, sum(si_item.qty) as si_qty
		from `tabSales Invoice` si, `tabSales Invoice Item` si_item
		where si.name = si_item.parent and si.docstatus = 1 and 
		ifnull(si.update_stock, 0) = 1 and ifnull(si.is_pos, 0) = 1 %s 
		group by si_item.item_name""" % (condition), as_dict=1)

	dn_item_map = {}
	for item in dn_items:
		dn_item_map.setdefault(item.item_code, item.dn_qty)

	for item in si_items:
		dn_item_map.setdefault(item.item_code, item.si_qty)

	return dn_item_map

def get_condition(filters):
	conditions = ""
	if filters.get("from_date") and filters.get("to_date"):
		conditions += " and posting_date between '%s' and '%s'" % (filters["from_date"],filters["to_date"])
	else:
		webnotes.msgprint("Please set date in from date field",raise_exception=1)
	return conditions