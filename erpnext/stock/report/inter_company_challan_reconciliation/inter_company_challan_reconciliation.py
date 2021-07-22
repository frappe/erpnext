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
	data = get_data(filters)
	return columns,data


def get_columns(filters):
	columns=[
			{
				"label": _("Inward Document"),
				"fieldname": "name",
				"fieldtype": "Link",
				"options": "Stock Entry",
				"width": 140
			},
			{
				"label": _("Outward Document"),
				"fieldname": 'reference_challan',
				"fieldtype": "Link",
				"options": "Stock Entry",
				"width": 100
			},
			{
				"label": _("Inward Posting Date "),
				"fieldname": 'date',
				"fieldtype": "Date",
				"width": 100
			},
			{
				"label": _("Outward Posting Date"),
				"fieldname": 'date1',
				"fieldtype": "Link",
				"options": "Item",
				"width": 100
			},
			{
				"label": _("Outward Item code "),
				"fieldname": 'item_code',
				"fieldtype": "Link",
				"options": "Item",
				"width": 100
			},
			{
				"label": _("Inward Item Code"),
				"fieldname": 'item_code1',
				"fieldtype": "Link",
				"options": "Item",
				"width": 100
			},

			{
				"label": _("Outward Item Name "),
				"fieldname": 'item_name',
				"fieldtype": "Read Only",
				"width": 100
			},
			{
				"label": _("Inward Item Name "),
				"fieldname": 'item_name1',
				"fieldtype": "Read Only",
				"width": 100
			},
			{
				"label": _("Outward Item Description"),
				"fieldname": 'description',
				"fieldtype": "Read Only",
				"width": 100
			},
			{
				"label": _("Inward Item Description"),
				"fieldname": 'description1',
				"fieldtype": "Read Only",
				"width": 100
			},
			{
				"label": _("Outward Batch number "),
				"fieldname": 'batch_no',
				"fieldtype": "Link",
				"options":"Batch",
				"width": 100
			},
			{
				"label": _("Inward Batch number "),
				"fieldname": 'batch_no1',
				"fieldtype": "Link",
				"options":"Batch",
				"width": 100
			},
			{
				"label": _("Outward qty "),
				"fieldname": 'qty',
				"fieldtype": "Data",
				"width": 100
			},
			{
				"label": _("Inward qty"),
				"fieldname": 'qty1',
				"fieldtype": "Data",
				"width": 100
			},
			{
				"label": _("Outward Warehouse"),
				"fieldname": 's_warehouse',
				"fieldtype": "Data",
				"width": 100
			},
			{
				"label": _("Inward Warehouse"),
				"fieldname": 't_warehouse',
				"fieldtype": "Data",
				"width": 100
			},
			{
				"label": _("Outward Warehouse Qty"),
				"fieldname": 'actual_qty',
				"fieldtype": "Data",
				"width": 100
			},
			{
				"label": _("Inward Warehouse Qty"),
				"fieldname": 'actual_qty1',
				"fieldtype": "Data",
				"width": 100
			},
			{
				"label": _("Ageing"),
				"fieldname": 'age',
				"fieldtype": "Float",
				"width": 100
			}
		
	]
	return columns



def get_data(filters):
	data_list = []
	stock_filter = {
		"stock_entry_type":"Material Receipt","docstatus":1
	}
	if(filters.get('stock_entry')):
		stock_filter['name'] = filters.get('stock_entry')
	if(filters.get('reference_challan')):
		stock_filter['reference_challan']=filters.get('reference_challan')
	# if(filters.get('from_date')):
	# 	stock_filter['posting_date']=filters.get('from_date')
	# if(filters.get('to_date')):
	# 	stock_filter['posting_date']=filters.get('to_date')
	if(filters.get('company')):
		stock_filter['company']=filters.get('company')
	doc=frappe.db.get_all("Stock Entry",stock_filter,['name','reference_challan','posting_date'])
	for i in doc:
		lst=frappe.db.get_all("Stock Entry",{"name":i.reference_challan},"posting_date")
		for d in lst:
		# lst={}
		# lst['name']=i.get('name')
		# lst['reference_challan']=i.get('reference_challan')
		# data_list.append(lst)
			stock_entry_filter={
			"parent":i.reference_challan,"docstatus":1
				}
			if(filters.get('item_code')):
				stock_entry_filter['item_code'] = filters.get('item_code')
			if(filters.get('batch_no')):
				stock_entry_filter['batch_no'] = filters.get('batch_no')
		
			lst=frappe.db.get_all("Stock Entry Detail",stock_entry_filter,["item_code","batch_no","subcontracted_item","item_name","description","qty","s_warehouse","actual_qty"])
			stock_entry={
			"parent":i.name,"docstatus":1
				}
			if(filters.get('item_code1')):
				stock_entry_filter['item_code'] = filters.get('item_code1')
			if(filters.get('batch_no1')):
				stock_entry_filter['batch_no'] = filters.get('batch_no1')
			doclst=frappe.db.get_all("Stock Entry Detail",stock_entry,["item_code","batch_no","subcontracted_item","item_name","description","qty","t_warehouse","actual_qty"])
			for k in lst:
				for j in doclst:
					itm=frappe.db.get_all("Item",{"item_code":k.item_code},["intercompany_item"])
					it=frappe.db.get_all("Item",{"intercompany_item":j.item_code},["intercompany_item"])
					for m in itm:
						for u in it:
							if u.intercompany_item==j.item_code and m.intercompany_item==j.item_code:
								data={}
								data['name']=i.get('name')
								data['reference_challan']=i.get('reference_challan')
								data['date']=i.get('posting_date')
								data['date1']=d.get('posting_date')
								data['item_code']=k.get('item_code')
								data['item_name']=k.get('item_name')
								data['description']=k.get('description')
								data['batch_no']=k.get('batch_no')
								data['qty']=k.get('qty')
								data['s_warehouse']=k.get('s_warehouse')
								data['actual_qty']=k.get('actual_qty')
								data['item_code1']=j.get('item_code')
								data['item_name1']=j.get('item_name')
								data['description1']=j.get('description')
								data['batch_no1']=j.get('batch_no')
								data['qty1']=j.get('qty')
								data['t_warehouse']=j.get('t_warehouse')
								data['actual_qty1']=j.get('actual_qty')
								data['age']=date_diff(date.today(),d.get('posting_date'))
								data_list.append(data)
	return data_list