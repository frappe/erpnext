# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from erpnext.stock.utils import update_included_uom_in_report

def execute(filters=None):
	include_uom = filters.get("include_uom")
	columns = get_columns()
	items = get_items(filters)
	sl_entries = get_stock_ledger_entries(filters, items)
	item_details = get_item_details(items, sl_entries, include_uom)
	opening_row = get_opening_balance(filters, columns)

	data = []
	groups = []
	actual_qty_groups = []
	qty_after_transaction_groups = []
	incoming_rate_groups = []
	valuation_rate_groups = []
	stock_value_groups = []
	products = []
	actual_qty_products = []
	qty_after_transaction_products = []
	incoming_rate_products = []
	valuation_rate_products = []
	stock_value_products = []
	type_transactions = []
	actual_qty_transactions = []
	qty_after_transaction_transactions = []
	incoming_rate_transactions = []
	valuation_rate_transactions = []
	stock_value_transactions = []
	conversion_factors = []
	if opening_row:
		data.append(opening_row)

	actual_qty = stock_value = 0
	for sle in sl_entries:
		item_detail = item_details[sle.item_code]

		sle.update(item_detail)

		if filters.get("batch_no"):
			actual_qty += sle.actual_qty
			stock_value += sle.stock_value_difference

			if sle.voucher_type == 'Stock Reconciliation':
				actual_qty = sle.qty_after_transaction
				stock_value = sle.stock_value
			
			sle.update({
				"qty_after_transaction": actual_qty,
				"stock_value": stock_value
			})

	for sle in sl_entries:
		new_group = True
		if sle.item_group in groups:
			new_group = False
		
		if new_group:
			groups.append(sle.item_group)
		
		new_product = True
		if sle.item_code in products:
			new_product = False
		
		if new_product:
			products.append(sle.item_code)
		
		new_transaction = True
		if sle.voucher_type in type_transactions:
			new_transaction = False
		
		if new_transaction:
			type_transactions.append(sle.voucher_type)

	# for group in groups:	
	# 	for product in products:
	# 		for sle in sl_entries:			
	# 			if sle.item_group == group:
	# 				actual_qty_groups.append(sle.actual_qty)
	# 				qty_after_transaction_groups.append(sle.qty_after_transaction)
	# 				incoming_rate_groups.append(sle.incoming_rate)
	# 				valuation_rate_groups.append(sle.valuation_rate)
	# 				stock_value_groups.append(stock_value)
	# 				if sle.item_code == product:
	# 					actual_qty_products.append(sle.actual_qty)
	# 					qty_after_transaction_products.append(sle.qty_after_transaction)
	# 					incoming_rate_products.append(sle.incoming_rate)
	# 					valuation_rate_products.append(sle.valuation_rate)
	# 					stock_value_products.append(stock_value)
	# 					for type in type_transactions:
	# 						for sle_type in sl_entries:
	# 							if sle_type.item_group == group:
	# 								if sle_type.item_code == product:
	# 									if sle_type.voucher_type == type:
	# 										actual_qty_transactions.append(sle.actual_qty)
	# 										qty_after_transaction_transactions.append(sle.qty_after_transaction)
	# 										incoming_rate_transactions.append(sle.incoming_rate)
	# 										valuation_rate_transactions.append(sle.valuation_rate)
	# 										stock_value_transactions.append(stock_value)

	for group in groups:	
		group_list = []
		group_row = [{'indent': 0.0, "transaction": group}]	
		for product in products:
			product_register = False
			actual_qty_product = 0
			qty_after_transaction_product = 0
			incoming_rate_product = 0
			valuation_rate_product = 0
			stock_value_product = 0
			transaction_add = []
			product_add = []
			for sle in sl_entries:		
				if sle.item_group == group:

					if sle.item_code == product:
						

						for type in type_transactions:
							pro = []
							actual_qty_type = 0
							qty_after_transaction_type = 0
							incoming_rate_type = 0
							valuation_rate_type = 0
							stock_value_type = 0
							actual_type = ""
							transaction_new = False
							for sle_type in sl_entries:
								if sle_type.item_group == group:
									if sle_type.item_code == product:
										if sle_type.voucher_type == type:
											actual_type = sle_type.voucher_type
												# if transaction_new == False:

												# 	add_transaction = True
												# 	if type in transaction_add:
												# 		add_transaction = False

												# 	if add_transaction:
												# 		transaction_new = True
												# 		transaction_add.append(sle_type.voucher_type)
												# 		group_list += [{'indent': 2.0, "transaction": "", "item_code":"", "item_name":"", "voucher_type":sle_type.voucher_type, "voucher_no":"",
												# 		"stock_uom":0, "actual_qty":0, "qty_after_transaction":0, "incoming_rate":0, "valuation_rate":0, "stock_value":0}]
												
											product_new = True
											if sle_type.voucher_no in product_add:
													product_new = False
																
											if product_new:
												actual_qty_product += sle_type.actual_qty
												qty_after_transaction_product += sle_type.qty_after_transaction
												incoming_rate_product += sle_type.incoming_rate
												valuation_rate_product += sle_type.valuation_rate
												stock_value_product += sle_type.stock_value

												actual_qty_type += sle_type.actual_qty
												qty_after_transaction_type += sle_type.qty_after_transaction
												incoming_rate_type += sle_type.incoming_rate
												valuation_rate_type += sle_type.valuation_rate
												stock_value_type += sle_type.stock_value
												product_add.append(sle_type.voucher_no)
												pro += [{'indent': 3.0, "transaction": "", "item_code":"", "item_name":"","voucher_type":sle_type.voucher_type, "voucher_no":sle_type.voucher_no, 
												"stock_uom":sle_type.stock_uom, "actual_qty":sle_type.actual_qty, "qty_after_transaction":sle_type.qty_after_transaction, "incoming_rate":sle_type.incoming_rate, "valuation_rate":sle_type.valuation_rate, "stock_value":sle_type.stock_value}]
							# if sle.item_code == product:
							if product_register == False:
								product_register = True
								group_list += [{'indent': 1.0, "transaction": "", "item_code":sle.item_code, "item_name":sle.item_name, "voucher_type":"", "voucher_no":"",
								"stock_uom":"", "actual_qty":0, "qty_after_transaction":0, "incoming_rate":0, "valuation_rate":0, "stock_value":0}]

							if actual_type == type:
								if transaction_new == False:
									add_transaction = True
									if actual_type in transaction_add:
										add_transaction = False

									if add_transaction:
										transaction_new = True
										transaction_add.append(actual_type)
										group_list += [{'indent': 2.0, "transaction": "", "item_code":"", "item_name":"", "voucher_type":actual_type, "voucher_no":"",
										"stock_uom":"", "actual_qty":actual_qty_type, "qty_after_transaction":qty_after_transaction_type, "incoming_rate":incoming_rate_type, "valuation_rate":valuation_rate_type, "stock_value":stock_value_type}]
								
								for p in pro:
									group_list += [p]
								
								pro = []

		data.extend(group_row or [])
		data.extend(group_list or [])
		# data.extend(products_list or [])
		# data.extend(transaction_list or [])

	update_included_uom_in_report(columns, data, include_uom, conversion_factors)
	return columns, data

def get_columns():
	columns = [
		{"label": _("Group"), "fieldname": "transaction", "width": 100},
		{"label": _("Item"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 130},
		{"label": _("Item Name"), "fieldname": "item_name", "width": 100},
		{"label": _("Voucher Type"), "fieldname": "voucher_type", "width": 110},
		{"label": _("Voucher #"), "fieldname": "voucher_no", "fieldtype": "Dynamic Link", "options": "voucher_type", "width": 100},
		{"label": _("Stock UOM"), "fieldname": "stock_uom", "fieldtype": "Link", "options": "UOM", "width": 100},
		{"label": _("Qty"), "fieldname": "actual_qty", "fieldtype": "Float", "width": 50, "convertible": "qty"},
		{"label": _("Balance Qty"), "fieldname": "qty_after_transaction", "fieldtype": "Float", "width": 100, "convertible": "qty"},
		{"label": _("Incoming Rate"), "fieldname": "incoming_rate", "fieldtype": "Currency", "width": 110,
			"options": "Company:company:default_currency", "convertible": "rate"},
		{"label": _("Valuation Rate"), "fieldname": "valuation_rate", "fieldtype": "Currency", "width": 110,
			"options": "Company:company:default_currency", "convertible": "rate"},
		{"label": _("Balance Value"), "fieldname": "stock_value", "fieldtype": "Currency", "width": 110,
			"options": "Company:company:default_currency"}
	]

	return columns

def get_stock_ledger_entries(filters, items):
	item_conditions_sql = ''
	if items:
		item_conditions_sql = 'and sle.item_code in ({})'\
			.format(', '.join([frappe.db.escape(i) for i in items]))

	return frappe.db.sql("""select concat_ws(" ", posting_date, posting_time) as date,
			item_code, warehouse, actual_qty, qty_after_transaction, incoming_rate, valuation_rate,
			stock_value, voucher_type, voucher_no, batch_no, serial_no, company, project, stock_value_difference
		from `tabStock Ledger Entry` sle
		where company = %(company)s and
			posting_date between %(from_date)s and %(to_date)s
			{sle_conditions}
			{item_conditions_sql}
			order by posting_date asc, posting_time asc, creation asc"""\
		.format(
			sle_conditions=get_sle_conditions(filters),
			item_conditions_sql = item_conditions_sql
		), filters, as_dict=1)

def get_items(filters):
	conditions = []
	if filters.get("item_code"):
		conditions.append("item.name=%(item_code)s")
	else:
		if filters.get("brand"):
			conditions.append("item.brand=%(brand)s")
		if filters.get("item_group"):
			conditions.append(get_item_group_condition(filters.get("item_group")))

	items = []
	if conditions:
		items = frappe.db.sql_list("""select name from `tabItem` item where {}"""
			.format(" and ".join(conditions)), filters)
	return items

def get_item_details(items, sl_entries, include_uom):
	item_details = {}
	if not items:
		items = list(set([d.item_code for d in sl_entries]))

	if not items:
		return item_details

	cf_field = cf_join = ""
	if include_uom:
		cf_field = ", ucd.conversion_factor"
		cf_join = "left join `tabUOM Conversion Detail` ucd on ucd.parent=item.name and ucd.uom=%s" \
			% frappe.db.escape(include_uom)

	res = frappe.db.sql("""
		select
			item.name, item.item_name, item.description, item.item_group, item.brand, item.stock_uom {cf_field}
		from
			`tabItem` item
			{cf_join}
		where
			item.name in ({item_codes})
	""".format(cf_field=cf_field, cf_join=cf_join, item_codes=','.join(['%s'] *len(items))), items, as_dict=1)

	for item in res:
		item_details.setdefault(item.name, item)

	return item_details

def get_sle_conditions(filters):
	conditions = []
	if filters.get("warehouse"):
		warehouse_condition = get_warehouse_condition(filters.get("warehouse"))
		if warehouse_condition:
			conditions.append(warehouse_condition)
	if filters.get("voucher_no"):
		conditions.append("voucher_no=%(voucher_no)s")
	if filters.get("batch_no"):
		conditions.append("batch_no=%(batch_no)s")
	if filters.get("project"):
		conditions.append("project=%(project)s")

	return "and {}".format(" and ".join(conditions)) if conditions else ""

def get_opening_balance(filters, columns):
	if not (filters.item_code and filters.warehouse and filters.from_date):
		return

	from erpnext.stock.stock_ledger import get_previous_sle
	last_entry = get_previous_sle({
		"item_code": filters.item_code,
		"warehouse_condition": get_warehouse_condition(filters.warehouse),
		"posting_date": filters.from_date,
		"posting_time": "00:00:00"
	})
	row = {}
	row["item_code"] = _("'Opening'")
	for dummy, v in ((9, 'qty_after_transaction'), (11, 'valuation_rate'), (12, 'stock_value')):
			row[v] = last_entry.get(v, 0)

	return row

def get_warehouse_condition(warehouse):
	warehouse_details = frappe.db.get_value("Warehouse", warehouse, ["lft", "rgt"], as_dict=1)
	if warehouse_details:
		return " exists (select name from `tabWarehouse` wh \
			where wh.lft >= %s and wh.rgt <= %s and warehouse = wh.name)"%(warehouse_details.lft,
			warehouse_details.rgt)

	return ''

def get_item_group_condition(item_group):
	item_group_details = frappe.db.get_value("Item Group", item_group, ["lft", "rgt"], as_dict=1)
	if item_group_details:
		return "item.item_group in (select ig.name from `tabItem Group` ig \
			where ig.lft >= %s and ig.rgt <= %s and item.item_group = ig.name)"%(item_group_details.lft,
			item_group_details.rgt)

	return ''
