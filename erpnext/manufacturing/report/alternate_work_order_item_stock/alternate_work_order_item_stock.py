# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from datetime import datetime
import frappe
from frappe import _
from frappe.utils.data import date_diff, today
from datetime import date


def execute(filters=None):
	columns=get_columns(filters)
	data = get_data(filters,columns)
	# a=add_column(columns)
	return columns,data


def get_columns(filters):
	columns=[
			{
				"label": _("Work Order"),
				"fieldname": "name",
				"fieldtype": "Link",
				"options": "Work Order",
				"width": 140
			},
			{
				"label": _("Status"),
				"fieldname": 'status',
				"fieldtype": "Data",
				"width": 100
			},
			{
				"label": _("Item To Manufacturer "),
				"fieldname": 'production_item',
				"fieldtype": "Link",
				"options": "Item",
				"width": 100
			},
			{
				"label": _("FG Item Name"),
				"fieldname": 'item_name1',
				"fieldtype": "Read Only",
				"width": 100
			},
			{
				"label": _("FG Item Qty "),
				"fieldname": 'qty',
				"fieldtype": "Data",
				"width": 100
			},
			{
				"label": _("FG item UOM"),
				"fieldname": 'stock_uom',
				"fieldtype": "Data",
				"width": 100
			},

			{
				"label": _("Work Order Item "),
				"fieldname": 'item_code',
				"fieldtype": "Link",
				"options":"Item",
				"width": 100
			},
			{
				"label": _("WO Item Name "),
				"fieldname": 'item_name',
				"fieldtype": "Read Only",
				"width": 100
			},
			{
				"label": _("WO Item Qty"),
				"fieldname": 'required_qty',
				"fieldtype": "Read Only",
				"width": 100
			},
			{
				"label": _("WO Item UOM"),
				"fieldname": 'uom1',
				"fieldtype": "Read Only",
				"width": 100
			},
			{
				"label": _("WO Item stock"),
				"fieldname": 'available_qty_at_source_warehouse',
				"fieldtype": "Link",
				"options":"Batch",
				"width": 100
			},
			{
				"label": _("Alternate Item Name "),
				"fieldname": 'alternative_item_code',
				"fieldtype": "Link",
				"options":"Item",
				"width": 100
			},
			{
				"label": _("Alternate item stock "),
				"fieldname": 'actual_qty',
				"fieldtype": "Data",
				"width": 100
			},
		
	]
	return columns


# def get_condition(filters):

# 	conditions=" "
# 	if filters.get("from_date"):
# 		conditions += " AND ip.planned_start_date>='%s'" % filters.get('from_date')
# 	if filters.get("to_date"):
# 		conditions += " AND ip.planned_end_date<='%s'" % filters.get('to_date')
# 	if filters.get("item_code"):
# 		conditions += "AND wo.production_item = '%s'" % filters.get('item_code')
# 	if filters.get("name"):
# 		conditions += "AND wo.name = '%s'" % filters.get('name')
# 	return conditions


def get_data(filters,columns):
	filter={
			"docstatus":1 ,"status":('!=','Completed')
				}
	if(filters.get('name')):
		filter['name'] = filters.get('name')
	if(filters.get('item_code')):
		filter['production_item'] = filters.get('item_code')
	lst=frappe.db.get_all("Work Order",filter,["name","status","production_item","item_name","qty","stock_uom"])
	data=[]
	for i in lst:
		doc=frappe.get_doc("Work Order",i.name)
		
		for i in doc.required_items:
			# l=frappe.db.sql("""select count(ia.item_code) from `tabItem Alternative` ia,`tabItem` i where ia.item_code= '%s'""".format(i.item_code),as_dict=1)
			# print(l)
			b=frappe.db.get_all("Item Alternative",{"Item_code":i.item_code},["alternative_item_code","item_code"])
			z=frappe.db.get_all("Item Alternative",{"alternative_item_code":i.item_code},["item_code","alternative_item_code"])

			# c=frappe.db.count("Item Alternative",{"Item_code":i.item_code},["alternative_item_code"])
			# f.append(c)
			d=frappe.db.get_all("Item",{"item_code":i.item_code},['stock_uom'])
			data_list={}
			data_list['name']=doc.name
			data_list['status']=doc.status
			data_list['production_item']=doc.production_item
			data_list['item_name1']=doc.item_name
			data_list['qty']=doc.qty
			data_list['stock_uom']=doc.stock_uom
			data_list['item_code']=i.item_code
			data_list['item_name']=i.item_name
			data_list['required_qty']=i.required_qty
			for it in d:
				data_list['uom1']=it.stock_uom
				data_list['available_qty_at_source_warehouse']=i.available_qty_at_source_warehouse
				for j in b:
					if i.item_code==j.item_code:
						data_list['alternative_item_code']=j.alternative_item_code
						c=frappe.db.get_all("Bin",{"item_code":j.alternative_item_code},['actual_qty'])
						actual=[]
						for k in c:
							actual.append(k.actual_qty)
							data_list['actual_qty']=sum(actual)
				for v in z:
					if v.alternative_item_code==i.item_code:
						data_list['alternative_item_code']=v.item_code
						t=frappe.db.get_all("Bin",{"item_code":v.item_code},['actual_qty'])
						actual=[]
						for y in t:
							actual.append(y.actual_qty)
							data_list['actual_qty']=sum(actual)
			data.append(data_list)
	# a=max(f)
	# print(a)
	# for i in range(a):
	# 	columns += [("Alternative Item Code")+":Int:54"]
	# 	columns += [("Alternate Item Stock")+":Int:54"]
	# 	for j in b:
	# 		data += [j.alternative_item_code] if j.alternative_item_code else 1
	# 		c=frappe.db.get_all("Bin",{"item_code":j.alternative_item_code},['actual_qty'])
	# 		actual=[]
	# 		for k in c:
	# 			actual.append(k.actual_qty)
	# 			data_list['actual_qty']=sum(actual)
	return data

