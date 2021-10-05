# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _, throw
from frappe.utils import flt, date_diff, getdate
from frappe.utils.data import quote_urls

def execute(filters=None):
	group_by = ""

	if filters.group_by == "Transporter":
		group_by =" GROUP BY dpi.transporter "
	elif filters.group_by == "Customer":
		group_by =" GROUP BY dpi.customer "
	elif filters.group_by == "Sales Order":
		group_by =" GROUP BY dpi.sales_order "
	elif filters.group_by == "Delivery Date":
		group_by =" GROUP BY dpi.delivery_date "
	else: group_by =""

	validate_filters(filters)
	
	columns = get_columns(filters)
	conditions = get_conditions(filters)
	data = get_data(conditions, group_by, filters)
	return columns,data

def validate_filters(filters):
	from_date, to_date = filters.get("from_date"), filters.get("to_date")
	group, based = filters.get("group_by"), filters.get("based_on")

	if not from_date and to_date:
		frappe.throw(_("From and To Dates are required."))
	elif date_diff(to_date, from_date) < 0:
		frappe.throw(_("To Date cannot be before From Date."))

	if group == based:
		frappe.throw(_("Group by and Based on cannot be same"))
	


def get_conditions(filters):
	conditions = ""
	if filters.get("from_date") and filters.get("to_date"):
		conditions += " AND dpi.delivery_date between %(from_date)s and %(to_date)s"

	if filters.get("company"):
		conditions += " AND dpi.company = %(company)s"

	if filters.get("transporter"):
		conditions += " AND dpi.transporter = %(transporter)s"

	if filters.get("customer"):
		conditions += " AND dpi.customer = %(customer)s"
		
	return conditions

def get_columns(filters):
	column =[]
	if filters.get("based_on") == "Transporter":
		lst =[
			{
				"fieldname": "transporter",
				"label": "Transporter",
				"width": 200,
				"fieldtype": "Link",
				"options": "Supplier"
			},
			{
				"fieldname": "transporter_name",
				"label": "Transporter Name",
				"width": 200,
				"fieldtype": "Data"
			}
		]
		column.extend(lst)

	if filters.get("based_on") == "Sales Order":
		lst =[
			{
				"fieldname": "sales_order",
				"label": "Sales Order",
				"width": 200,
				"fieldtype": "Link",
				"options": "Sales Order"
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

	if filters.get("based_on") == "Delivery Date":
		lst =[
			{
				"fieldname": "delivery_date",
				"label": "Delivery Date",
				"width": 100,
				"fieldtype": "Date"
			},
		]
		column.extend(lst)	
	


	if filters.get("group_by") == "Transporter":
		lst =[
			{
				"fieldname": "transporter",
				"label": "Transporter",
				"width": 200,
				"fieldtype": "Link",
				"options": "Supplier"
			},
			{
				"fieldname": "transporter_name",
				"label": "Transporter Name",
				"width": 200,
				"fieldtype": "Data"
			}
		]
		column.extend(lst)

	if filters.get("group_by") == "Sales Order":
		lst =[
			{
				"fieldname": "sales_order",
				"label": "Sales Order",
				"width": 200,
				"fieldtype": "Link",
				"options": "Sales Order"
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

	if filters.get("group_by") == "Delivery Date":
		lst =[
			{
				"fieldname": "delivery_date",
				"label": "Delivery Date",
				"width": 100,
				"fieldtype": "Date"
			},
		]
		column.extend(lst)	
	

	lst =[
		{
			"fieldname": "item_code",
			"label": "Item Code",
			"width": 200,
			"fieldtype": "Link",
			"options": "Item"
		},
		{
			"fieldname": "item_name",
			"label": "Item Name",
			"width": 200,
			"fieldtype": "Data"
		},
		{
			"fieldname": "ordered_qty",
			"label": "Ordered Qty",
			"width": 80,
			"fieldtype": "Float"
		},
		{
			"fieldname": "qty_to_deliver",
			"label": "Qty To Deliver",
			"width": 80,
			"fieldtype": "Float"
		},
		{
			"fieldname": "weight_ordered",
			"label": "Weight Ordered",
			"width": 80,
			"fieldtype": "Float"
		},
		{
			"fieldname": "planned_delivery_weight",
			"label": "Planned Delivery Weight",
			"width": 80,
			"fieldtype": "Float"
		},
		{
			"fieldname": "actual_delivery_weight",
			"label": "Actual Delivery Weight",
			"width": 80,
			"fieldtype": "Float"
		},
		{
			"fieldname": "planned_date",
			"label": "Planned Delivery Date",
			"width": 100,
			"fieldtype": "Date"
		},
		{
			"fieldname": "delivery_note",
			"label": "Delivery Note",
			"width": 160,
			"fieldtype": "Link",
			"options": "Delivery Note"
		},
		{
			"fieldname": "delivery_note_date",
			"label": "Delivery Note Date",
			"width": 100,
			"fieldtype": "Date"
		},
		{
			"fieldname": "delay_days",
			"label": "Delay Days",
			"width": 80,
			"fieldtype": "Int"
		},
		{
			"fieldname": "pick_list",
			"label": "Pick List",
			"width": 170,
			"fieldtype": "Link",
			"options": "Pick List"
		},
		
		{
			"fieldname": "purchase_order",
			"label": "Purchase Order",
			"width": 170,
			"fieldtype": "Link",
			"options": "Purchase Order"
		},
		{
			"fieldname": "supplier",
			"label": "Supplier",
			"width": 200,
			"fieldtype": "Link",
			"options": "Supplier"
		},
		{
			"fieldname": "supplier_name",
			"label": "Supplier Name",
			"width": 200,
			"fieldtype": "Data"
		},
		{
			"fieldname": "item_planning_id",
			"label": "Item Planning ID",
			"width": 160,
			"fieldtype": "Link",
			"options": "Delivery Planning Item"
		},
		{
			"fieldname": "company",
			"label": "Company",
			"width": 200,
			"fieldtype": "Link",
			"options":"Company"
		}
	]
	column.extend(lst)
	return column

def get_data(conditions, group_by, filters):
	query = "select "
	if filters.get('group_by') =='Transporter' or filters.get('based_on') =='Transporter':
		query += "dpi.transporter,dpi.transporter_name,"

	if filters.get('group_by') =='Customer' or filters.get('based_on') =='Customer':
		query += "dpi.customer,dpi.customer_name,"

	if filters.get('group_by') =='Sales Order' or filters.get('based_on') =='Sales Order':
		query += "dpi.sales_order,"

	if filters.get('group_by') =='Delivery Date' or filters.get('based_on') =='Delivery Date':
		query += "dpi.delivery_date as expected_date,"

	query += """dpi.item_code,
				dpi.item_name,
				dpi.ordered_qty,
				dpi.qty_to_deliver,
				dpi.planned_date as planned_date,
				dpi.delivery_note,
				dn.posting_date as delivery_note_date,
					CASE 
					WHEN (DATEDIFF(dpi.planned_date, dpi.delivery_date)) > 0 
					THEN DATEDIFF(dpi.planned_date, dpi.delivery_date)
					Else 0 
					END as delay_days,
				dpi.pick_list,
				(dpi.ordered_qty *  dpi.weight_per_unit)as weight_ordered,
				dpi.weight_to_deliver as planned_delivery_weight,
					CASE
					WHEN dni.qty THEN (dni.qty * dpi.weight_per_unit)
					WHEN poi.qty THEN (poi.qty * dpi.weight_per_unit)
					ELSE 0
					END AS actual_delivery_weight,
				
				dpi.purchase_order as purchase_order,
				dpi.supplier,
				dpi.supplier_name,
				dpi.name as item_planning_id,
				dpi.company,
				dpi.related_delivey_planning as Related_to_Planning
				
				from `tabDelivery Planning Item` dpi
			
				Left join `tabDelivery Note` dn ON dn.name = dpi.delivery_note
				left join 	`tabDelivery Note Item` dni on dni.parent = dpi.delivery_note 
				and dni.item_code = dpi.item_code
	
                left join `tabPurchase Order` po ON po.name = dpi.purchase_order
                Left join `tabPurchase Order Item` poi ON poi.parent = dpi.purchase_order
                and poi.item_code = dpi.item_code

				where dpi.docstatus = 1  AND dpi.d_status = "Complete"
			
				
				{conditions}
				{groupby}
				"""
	if filters.get('group_by'):
		query +=",dpi.item_code, dpi.item_name, dpi.planned_date, dpi.delivery_note, delay_days, dpi.pick_list, dpi.purchase_order,dpi.supplier,dpi.supplier_name,dpi.name, dpi.company"
	# print('------query',query)
	result = frappe.db.sql( query.format(conditions=conditions, groupby = group_by),filters, as_dict=1)	
	# print("------------------------",result)
		
	item_details ={}
	for d in result:
		if filters.get("based_on") == _("Transporter"):
			key = (d.transporter, d.transporter_name)
			item_details.setdefault(key, {"details": []})
			fifo_queue = item_details[key]["details"]
			fifo_queue.append(d)	

		if filters.get("based_on") == _("Customer"):
			key = (d.customer, d.customer_name)
			item_details.setdefault(key, {"details": []})
			fifo_queue = item_details[key]["details"]
			fifo_queue.append(d)

		if filters.get("based_on") == _("Sales Order"):
			key = (d.sales_order)
			item_details.setdefault(key, {"details": []})
			fifo_queue = item_details[key]["details"]
			fifo_queue.append(d)

		if filters.get("based_on") == _("Delivery Date"):
			key = (d.expected_date)
			item_details.setdefault(key, {"details": []})
			fifo_queue = item_details[key]["details"]
			fifo_queue.append(d)

	data =[]
	for key in item_details.keys():
		ordered_qty=0
		qty_to_deliver = 0
		weight_ordered = 0
		planned_delivery_weight = 0
		actual_delivery_weight = 0
		for d in item_details[key]['details']:
			dd = frappe._dict({
				'transporter' : d.get('transporter'),
				'transporter_name' : d.get('transporter_name'),
				'sales_order' : d.get('sales_order'),
				'customer' : d.get('customer'),
				'customer_name' : d.get('customer_name'),
				'delivery_date' : d.get('expected_date'),
				'item_code' : d.get('item_code'),
				'item_name' : d.get('item_name'),
				'ordered_qty' : d.get('ordered_qty'),
				'qty_to_deliver' : d.get('qty_to_deliver'),
				'planned_date' : d.get('planned_date'),
				'delivery_note' : d.get('delivery_note'),
				'delivery_note_date' : d.get('delivery_note_date'),
				'delay_days' : d.get('delay_days'),
				'pick_list' : d.get('pick_list'),
				'weight_ordered' : d.get('weight_ordered'),
				'planned_delivery_weight' : d.get('planned_delivery_weight'),
				'actual_delivery_weight' :  d.get('actual_delivery_weight'),
				'purchase_order' : d.get('purchase_order'),
				'supplier' : d.get('supplier'),
				'supplier_name' : d.get('supplier_name'),
				'item_planning_id' : d.get('item_planning_id'),
				'company' : d.get('company')

			})
			ordered_qty += float(d.get('ordered_qty'))
			qty_to_deliver += float(d.get('qty_to_deliver'))
			weight_ordered += float(d.get('weight_ordered'))
			planned_delivery_weight += float(d.get('planned_delivery_weight'))
			actual_delivery_weight += float(d.get('actual_delivery_weight'))
			data.append(dd)		
		dd = frappe._dict({
				'transporter' : None,
				'transporter_name' : None,
				'sales_order' : None,
				'customer' : None,
				'customer_name' : None,
				'delivery_date' : None,
				'item_code' : None,
				'item_name' : '<b>Total</b>',
				'ordered_qty' : ordered_qty ,
				'qty_to_deliver' : qty_to_deliver,
				'planned_date' : None,
				'delivery_note' : None,
				'delivery_note_date' : None,
				'delay_days' : None,
				'pick_list' : None,
				'weight_ordered' : weight_ordered,
				'planned_delivery_weight' : planned_delivery_weight,
				'actual_delivery_weight' : actual_delivery_weight,
				'purchase_order' : None,
				'supplier' : None,
				'supplier_name' : None,
				'item_planning_id' : None,
				'company' : None

			})
		data.append(dd)



	# print("---------",data)
	return data

