
from __future__ import unicode_literals, print_function
import frappe
from frappe.utils import cint

def get_leaderboards():
	leaderboards = {
		"Customer": {
			"fields": [
				{'fieldname': 'total_sales_amount', 'fieldtype': 'Currency'},
				'total_qty_sold',
				{'fieldname': 'outstanding_amount', 'fieldtype': 'Currency'}
			],
			"method": "erpnext.startup.leaderboard.get_all_customers",
		},
		"Item": {
			"fields": [
				{'fieldname': 'total_sales_amount', 'fieldtype': 'Currency'},
				'total_qty_sold',
				{'fieldname': 'total_purchase_amount', 'fieldtype': 'Currency'},
				'total_qty_purchased',
				'available_stock_qty',
				{'fieldname': 'available_stock_value', 'fieldtype': 'Currency'}
			],
			"method": "erpnext.startup.leaderboard.get_all_items",
		},
		"Supplier": {
			"fields": [
				{'fieldname': 'total_purchase_amount', 'fieldtype': 'Currency'},
				'total_qty_purchased',
				{'fieldname': 'outstanding_amount', 'fieldtype': 'Currency'}
			],
			"method": "erpnext.startup.leaderboard.get_all_suppliers",
		},
		"Sales Partner": {
			"fields": [
				{'fieldname': 'total_sales_amount', 'fieldtype': 'Currency'},
				{'fieldname': 'total_commission', 'fieldtype': 'Currency'}
			],
			"method": "erpnext.startup.leaderboard.get_all_sales_partner",
		},
		"Sales Person": {
			"fields": [
				{'fieldname': 'total_sales_amount', 'fieldtype': 'Currency'}
			],
			"method": "erpnext.startup.leaderboard.get_all_sales_person",
		}
	}

	return leaderboards

@frappe.whitelist()
def get_all_customers(from_date, company, field, limit = None):
	if field == "outstanding_amount":
		filters = [['docstatus', '=', '1'], ['company', '=', company]]
		if from_date:
			filters.append(['posting_date', '>=', from_date])
		return frappe.db.get_all('Sales Invoice',
			fields = ['customer as name', 'sum(outstanding_amount) as value'],
			filters = filters,
			group_by = 'customer',
			order_by = 'value desc',
			limit = limit
		)
	else:
		if field == "total_sales_amount":
			select_field = "sum(so_item.base_net_amount)"
		elif field == "total_qty_sold":
			select_field = "sum(so_item.stock_qty)"

		return frappe.db.sql("""
			select so.customer as name, {0} as value
			FROM `tabSales Order` as so JOIN `tabSales Order Item` as so_item
				ON so.name = so_item.parent
			where so.docstatus = 1 and so.transaction_date >= %s and so.company = %s
			group by so.customer
			order by value DESC
			limit %s
		""".format(select_field), (from_date, company, cint(limit)), as_dict=1) #nosec

@frappe.whitelist()
def get_all_items(from_date, company, field, limit = None):
	if field in ("available_stock_qty", "available_stock_value"):
		select_field = "sum(actual_qty)" if field=="available_stock_qty" else "sum(stock_value)"
		return frappe.db.get_all('Bin',
			fields = ['item_code as name', '{0} as value'.format(select_field)],
			group_by = 'item_code',
			order_by = 'value desc',
			limit = limit
		)
	else:
		if field == "total_sales_amount":
			select_field = "sum(order_item.base_net_amount)"
			select_doctype = "Sales Order"
		elif field == "total_purchase_amount":
			select_field = "sum(order_item.base_net_amount)"
			select_doctype = "Purchase Order"
		elif field == "total_qty_sold":
			select_field = "sum(order_item.stock_qty)"
			select_doctype = "Sales Order"
		elif field == "total_qty_purchased":
			select_field = "sum(order_item.stock_qty)"
			select_doctype = "Purchase Order"

		return frappe.db.sql("""
			select order_item.item_code as name, {0} as value
			from `tab{1}` sales_order join `tab{1} Item` as order_item
				on sales_order.name = order_item.parent
			where sales_order.docstatus = 1
				and sales_order.company = %s and sales_order.transaction_date >= %s
			group by order_item.item_code
			order by value desc
			limit %s
		""".format(select_field, select_doctype), (company, from_date, cint(limit)), as_dict=1) #nosec

@frappe.whitelist()
def get_all_suppliers(from_date, company, field, limit = None):
	if field == "outstanding_amount":
		filters = [['docstatus', '=', '1'], ['company', '=', company]]
		if from_date:
			filters.append(['posting_date', '>=', from_date])
		return frappe.db.get_all('Purchase Invoice',
			fields = ['supplier as name', 'sum(outstanding_amount) as value'],
			filters = filters,
			group_by = 'supplier',
			order_by = 'value desc',
			limit = limit
		)
	else:
		if field == "total_purchase_amount":
			select_field = "sum(purchase_order_item.base_net_amount)"
		elif field == "total_qty_purchased":
			select_field = "sum(purchase_order_item.stock_qty)"

		return frappe.db.sql("""
			select purchase_order.supplier as name, {0} as value
			FROM `tabPurchase Order` as purchase_order LEFT JOIN `tabPurchase Order Item`
				as purchase_order_item ON purchase_order.name = purchase_order_item.parent
			where purchase_order.docstatus = 1 and  purchase_order.modified >= %s
				and  purchase_order.company = %s
			group by purchase_order.supplier
			order by value DESC
			limit %s""".format(select_field), (from_date, company, cint(limit)), as_dict=1) #nosec

@frappe.whitelist()
def get_all_sales_partner(from_date, company, field, limit = None):
	if field == "total_sales_amount":
		select_field = "sum(`base_net_total`)"
	elif field == "total_commission":
		select_field = "sum(`total_commission`)"

	filters = {
		'sales_partner': ['!=', ''],
		'docstatus': 1,
		'company': company
	}
	if from_date:
		filters['transaction_date'] = ['>=', from_date]

	return frappe.get_list('Sales Order', fields=[
		'`sales_partner` as name',
		'{} as value'.format(select_field),
	], filters=filters, group_by='sales_partner', order_by='value DESC', limit=limit)

@frappe.whitelist()
def get_all_sales_person(from_date, company, field = None, limit = 0):
	return frappe.db.sql("""
		select sales_team.sales_person as name, sum(sales_order.base_net_total) as value
		from `tabSales Order` as sales_order join `tabSales Team` as sales_team
			on sales_order.name = sales_team.parent and sales_team.parenttype = 'Sales Order'
		where sales_order.docstatus = 1
			and sales_order.transaction_date >= %s
			and sales_order.company = %s
		group by sales_team.sales_person
		order by value DESC
		limit %s
	""", (from_date, company, cint(limit)), as_dict=1)
