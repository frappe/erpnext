# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _


def execute(filters=None):
	columns=get_columns(filters)
	data = get_data(filters)
	return columns,data


def get_columns(filters):
	columns=[
			# {
			# 	"label": _("Posting Date "),
			# 	"fieldname": 'posting_date',
			# 	"fieldtype": "Date",
			# 	"width": 100
			# },
			{
				"label": _("Receipt Document"),
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
				"label": _("Item code "),
				"fieldname": 'item_code',
				"fieldtype": "Link",
				"options": "Item",
				"width": 100
			},
			{
				"label": _("InterCompany Item"),
				"fieldname": 'intercompany_item',
				"fieldtype": "Link",
				"options": "Item",
				"width": 100
			},

			{
				"label": _("Item Name "),
				"fieldname": 'item_name',
				"fieldtype": "Read Only",
				"width": 100
			},
			{
				"label": _("Item Description"),
				"fieldname": 'description',
				"fieldtype": "Read Only",
				"width": 100
			},
			{
				"label": _("Batch number "),
				"fieldname": 'batch_no',
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
				"label": _("qty from outward_warehouse"),
				"fieldname": 'actual_qty',
				"fieldtype": "Data",
				"width": 100
			},
			{
				"label": _("qty from inward_warehouse"),
				"fieldname": 'actual_qty1',
				"fieldtype": "Data",
				"width": 100
			},
		
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
		lst={}
		lst['name']=i.get('name')
		lst['reference_challan']=i.get('reference_challan')
		# lst['posting_date']=i.get('posting_date')
		data_list.append(lst)
		stock_entry_filter={
		"parent":i.reference_challan,"docstatus":1
			}
		if(filters.get('item_code')):
			stock_entry_filter['item_code'] = filters.get('item_code')
		if(filters.get('batch_no')):
			stock_entry_filter['batch_no'] = filters.get('batch_no')

		lst=frappe.db.get_all("Stock Entry Detail",stock_entry_filter,["item_code","batch_no","item_name","description","qty","s_warehouse","actual_qty"])


		doclst=frappe.db.get_all("Stock Entry Detail",{"parent":i.name,"docstatus":1},["item_code","batch_no","qty","t_warehouse","actual_qty"])
		for k in lst:
			stock_details_filter={
				"name":k.get('item_code')
			}
			# if(filters.get('intercompany_item')):
			# 	stock_details_filter['intercompany_item'] = filters.get('intercompany_item')

			item=frappe.db.get_all("Item",stock_details_filter,["intercompany_item"])
			for j in doclst:
				for itm in item:
					data = {}
					data['item_code']=k.get('item_code')
					data['item_name']=k.get('item_name')
					data['description']=k.get('description')
					data['batch_no']=k.get('batch_no')
					data['qty']=k.get('qty')
					data['s_warehouse']=k.get('s_warehouse')
					data['actual_qty']=k.get('actual_qty')
					data['intercompany_item']=itm.get('intercompany_item')
					data['qty1']=j.get('qty')
					data['t_warehouse']=j.get('t_warehouse')
					data['actual_qty1']=j.get('actual_qty')
			data_list.append(data)
	return data_list
	

# def get_data(filters):
# 	data_list = []
# 	doc=frappe.db.sql("""Select se.name ,se.reference_challan from `tabStock Entry` se where se.stock_entry_type="Material Receipt" and se.docstatus=1 and se.reference_challan !=" " """,as_dict=1)
# 	for i in doc:
# 		data = {}
# 		lst=frappe.db.get_all("Stock Entry Detail",{"parent":i.get('reference_challan'),"docstatus":1},["item_code","item_name","description","qty","s_warehouse","actual_qty"])
# 		doclst=frappe.db.get_all("Stock Entry Detail",{"parent":i.get('name'),"docstatus":1},["item_code","batch_no","qty","t_warehouse","actual_qty"])
# 		data['name']=i.get('name')
# 		data['reference_challan']=i.get('reference_challan')
# 		data_list.append(data)
# 		for k in lst:
# 			value={}
# 			value['item_code']=k.get('item_code')
# 			value['item_name']=k.get('item_name')
# 			value['description']=k.get('description')
# 			value['qty']=k.get('qty')
# 			value['s_warehouse']=k.get('s_warehouse')
# 			value['actual_qty']=k.get('actual_qty')
# 			data_list.append(value)
# 		for j in doclst:
# 			doc_lst={}
# 			doc_lst['intercompany_item']=j.get('item_code')
# 			doc_lst['batch_no']=j.get('batch_no')
# 			doc_lst['qty1']=j.get('qty')
# 			doc_lst['t_warehouse']=j.get('t_warehouse')
# 			doc_lst['actual_qty1']=j.get('actual_qty')
# 			data_list.append(doc_lst)
# 	return data_list