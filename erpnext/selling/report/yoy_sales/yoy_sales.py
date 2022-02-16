# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):


	group_by = ""
	order_by = ""

	if filters.get("based_on") == "Item":
		group_by = " Group BY sii.item_code "

	if filters.get("based_on") == "Customer" :
		group_by =" GROUP BY si.customer "
		
	if filters.get('based_on')  == "Customer Group":
		group_by =" GROUP BY si.customer_group "
		

	if filters.get('based_on') ==  "Item Group":
		group_by =" GROUP BY sii.item_group "
		
	if filters.get('based_on') == 'Territory' :
		group_by =" GROUP BY si.territory "

	# if filters.get('group_by') == "Item":	
	# 	group_by += "  ,sii.item_code "

	# if filters.get('group_by') ==  "Customer":	
	# 	group_by +=" , si.customer"

	validate_filters(filters)
	
	columns=get_columns(filters)

	data = get_data(filters, group_by, order_by)

	return columns, data

def validate_filters(filters):

	frm = filters.get("from_year")
	to = filters.get("to_year")



	if len(str(frm)) != 4 or  len(str(to)) != 4 and frm <= 2099 and to <= 2099:
		frappe.throw(_("Please enter Correct Year"))	

	if frm > to:
		frappe.throw(_("From Year cannot be greater than To Year"))		
	
	group = filters.get("group_by")
	based = filters.get("based_on")

	# if group == based:
	# 	frappe.throw(_("Group by and Based on cannot be same"))		

def get_columns(filters):
	column=[]
	from_year = filters.get("from_year")
	to_year = filters.get("to_year")

	years = frappe.db.sql("""
							Select distinct(year(modified)) as years from `tabSales Invoice Item`
						""", as_dict= 1)

	if filters.get("based_on") == "Item":
		lst =[
				{
					"label": _("Item Code"),
					"fieldname": 'item_code',
					"fieldtype": "Link",
					"options": "Item",
					"width": 200
				},
				{
					"fieldname": "item_name",
					"label": "Item Name",
					"width": 200,
					"fieldtype": "Data",
				},
		]
		column.extend(lst)					
	
	if filters.get("based_on") == "Customer":
		lst =[
			{
				"fieldname": "customer",
				"label": "Customer",
				"width": 200,
				"fieldtype": "Link",
				"options": "Customer"
			},
			{
				"fieldname": "customer_name",
				"label": "Customer Name",
				"width": 200,
				"fieldtype": "Data"
			}
		]
		column.extend(lst)		

	if filters.get("based_on") == "Customer Group":
		lst =[
			{
				"fieldname": "customer_group",
				"label": "Customer Group",
				"width": 200,
				"fieldtype": "Link",
				"options": "Customer Group"
			},
		]
		column.extend(lst)	

	if filters.get("based_on") == "Item Group":
		lst =[
			{
				"fieldname": "item_group",
				"label": "Item Group",
				"width": 200,
				"fieldtype": "Link",
				"options": "Item Group"
			},
		]
		column.extend(lst)		

	if filters.get("based_on") == "Territory":
		lst =[
			{
				"fieldname": "territory",
				"label": "Territory",
				"width": 200,
				"fieldtype": "Link",
				"options": "Territory"
			},
		]
		column.extend(lst)	

	if filters.get("group_by") == "Item":
		lst =[
				{
					"label": _("Item Code"),
					"fieldname": 'item_code',
					"fieldtype": "Link",
					"options": "Item",
					"width": 200
				},
				{
					"fieldname": "item_name",
					"label": "Item Name",
					"width": 200,
					"fieldtype": "Data",
				},
		]
		column.extend(lst)

	if filters.get("group_by") == "Customer":
		lst =[
			{
				"fieldname": "customer",
				"label": "Customer",
				"width": 200,
				"fieldtype": "Link",
				"options": "Customer"
			},
			{
				"fieldname": "customer_name",
				"label": "Customer Name",
				"width": 200,
				"fieldtype": "Data"
			}
		]
		column.extend(lst)		

	if years :

		if filters.get("value") == "Qty":
			for from_year in range (from_year,to_year): 
				a = from_year
				b = a + 1
				lst3 = [
				
					{
						"label": _(str(a) +"-"+ str(b) + "(Qty)"),
						"fieldname": (str(a) +"-"+ str(b)+ "(Qty)"),
						"fieldtype": "Read Only",
						"width": 130
					}
				]
			
				column.extend(lst3)	

			# lst_2 =[
						
			# {
			# 	"label": _("Total Qty"),
			# 	"fieldname": 'qty',
			# 	"fieldtype": "Int",
			# 	"width": 100
			# }]	
			# column.extend(lst_2)

		else:

			for from_year in range (from_year,to_year): 
				a = from_year
				b = a + 1
				lst3 = [
					{
						"label": _(str(a) +"-"+ str(b) + "(Amt)"),
						"fieldname": (str(a) +"-"+ str(b) + "(Amt)"),
						"fieldtype": "Currency",
						"width": 130
					}
				]
	
				column.extend(lst3)
			# lst_2 =[
			# {
			# 	"label": _("Total Amount"),
			# 	"fieldname": 'amt',
			# 	"fieldtype": "Currency",
			# 	"width": 100
			# },
			# ]
			# column.extend(lst_2)


	# lst_2 =[
						
	# 		{
	# 			"label": _("Total Qty"),
	# 			"fieldname": 'qty',
	# 			"fieldtype": "Int",
	# 			"width": 100
	# 		},
	# 		{
	# 			"label": _("Total Amount"),
	# 			"fieldname": 'qty',
	# 			"fieldtype": "Int",
	# 			"width": 100
	# 		},
	# ]
	# column.extend(lst_2)


	return column	

def get_condition(filters):

	conditions=" "
	
	if filters.get("item_code"):
		conditions += "AND sii.item_code = '%s'" % filters.get('item_code')
	
	if filters.get("item_group"):
		conditions += "AND sii.item_group = '%s'" % filters.get('item_group')

	if filters.get("company"):
		conditions += "AND si.company = '%s'" % filters.get('company')		

	return conditions

def get_data(filters, group_by, order_by):
	from_y = filters.get("from_year")
	to_year = filters.get("to_year")
	years = frappe.db.sql("""
							Select distinct(year(modified)) as years from `tabSales Invoice Item`
						""", as_dict= 1)
	conditions = get_condition(filters)

	query = "Select "

	if filters.get('based_on') == 'Item' :
		query += " sii.item_code, sii.item_name, "	

	if filters.get('based_on') == 'Item Group':
		query += " sii.item_group, "

	if filters.get('based_on') == 'Customer' :
		query += " si.customer, si.customer_name, "

	if filters.get('based_on') == 'Customer Group' :
		query += " si.customer_group, "

	if filters.get('based_on') == 'Territory' :
		query += " si.territory, "



	if filters.get('group_by') =='Customer' :
		query += " si.customer, si.customer_name, "

	if filters.get('group_by') == 'Item':
		query += " sii.item_code, sii.item_name, "				

	if years and filters.get('value') == 'Amount':
		for from_y in range (from_y,to_year): 
			a = from_y
			b = a + 1
			start_date = str(a) + '-04-01'

			end_date = str(b) + '-03-31'
			query += """ if (
			(Select sum(soi1.amount) from `tabSales Invoice Item` soi1 where soi1.item_code =  sii.item_code 
			and soi1.modified between '{0}' and '{1}') > 0,
			(Select sum(soi1.amount) from `tabSales Invoice Item` soi1 where soi1.item_code =  sii.item_code 
			and soi1.modified between '{0}' and '{1}') , 0)
			as '{2}', 
			""".format(start_date , end_date, str(str(a) +"-"+ str(b)+ "(Amt)"))

			print(start_date, end_date, query)	

	if years and filters.get('value') == 'Qty':
		for from_y in range (from_y,to_year): 
			a = from_y
			b = a + 1
			start_date = str(a) + '-04-01'

			end_date = str(b) + '-03-31'
			query += """ if (
			(Select sum(soi1.qty) from `tabSales Invoice Item` soi1 where soi1.item_code =  sii.item_code 
			and soi1.modified between '{0}' and '{1}') > 0,
			(Select sum(soi1.qty) from `tabSales Invoice Item` soi1 where soi1.item_code =  sii.item_code 
			and soi1.modified between '{0}' and '{1}') , 0)
			as '{2}', 
			""".format(start_date , end_date, str(str(a) +"-"+ str(b)+ "(Qty)"))

			print(start_date, end_date, query)	

	if filters.get('value') == 'Qty':
		query += " sum(sii.qty) qty, "

	if filters.get('value') == 'Amount':
		query += " sum(sii.amount) amt, "			


	query += """ si.company 
				from `tabSales Invoice Item` sii ,`tabSales Invoice` si
				where sii.parent = si.name AND sii.docstatus = 1 AND si.docstatus = 1
				AND sii.item_code IS NOT NULL
				{conditions}
				{groupby}
				
				"""
	result = frappe.db.sql( query.format(conditions=conditions, groupby = group_by),filters, as_dict=1)	

	print("Query", query , conditions, group_by, order_by)						

	# for res in result:
	# 	print(" this ir result", res)	

	item_details ={}
	for d in result:
		if filters.get("based_on") == _("Item"):
			key = (d.item_code, d.item_name)
			item_details.setdefault(key, {"details": []})
			fifo_queue = item_details[key]["details"]
			fifo_queue.append(d)	

		if filters.get("based_on") == _("Item Group"):
			key = (d.item_group)
			item_details.setdefault(key, {"details": []})
			fifo_queue = item_details[key]["details"]
			fifo_queue.append(d)	

		if filters.get("based_on") == _("Customer"):
			key = (d.customer, d.customer_name)
			item_details.setdefault(key, {"details": []})
			fifo_queue = item_details[key]["details"]
			fifo_queue.append(d)

		if filters.get("based_on") == _("Customer Group"):
			key = (d.customer_group)
			item_details.setdefault(key, {"details": []})
			fifo_queue = item_details[key]["details"]
			fifo_queue.append(d)

		if filters.get("based_on") == _("Territory"):
			key = (d.territory)
			item_details.setdefault(key, {"details": []})
			fifo_queue = item_details[key]["details"]
			fifo_queue.append(d)			

	f_year = filters.get("from_year")
	data =[]
	for key in item_details.keys():
		
		for d in item_details[key]['details']:
			dd = {
				'item_group' : d.get('item_group'),
				'item_code' : d.get('item_code'),
				'item_name' : d.get('item_name'),
				'customer' : d.get('customer'),
				'customer_name' : d.get('customer_name'),
				'customer_group' : d.get('customer_group'),
				'territory' : d.get('territory'),
			
				'years' : d.get('years'),
				'company' : d.get('company'),
				
			}
			data.append(dd)	

			for f_year in range (filters.get("from_year"),filters.get("to_year")+1): 
				a = f_year
				b = a + 1		
				if filters.get("value") == "Amount":
					dd[str(a) +"-"+ str(b) +"(Amt)"] = d.get(str(a) +"-"+ str(b) +'(Amt)')
								
					# print("dd",dd)
				else:	
					dd[str(a) +"-"+ str(b) +"(Qty)"] = d.get(str(a) +"-"+ str(b) +'(Qty)')

	# for d in data :
	# 	print('data 1 : ', d)		

	return data	
