import frappe

from erpnext.deprecation_dumpster import deprecated


def get_leaderboards():
	leaderboards = {
		"Customer": {
			"fields": [
				{"fieldname": "total_sales_amount", "fieldtype": "Currency"},
				"total_qty_sold",
				{"fieldname": "outstanding_amount", "fieldtype": "Currency"},
			],
			"method": "erpnext.startup.leaderboard.get_all_customers",
			"icon": "customer",
		},
		"Item": {
			"fields": [
				{"fieldname": "total_sales_amount", "fieldtype": "Currency"},
				"total_qty_sold",
				{"fieldname": "total_purchase_amount", "fieldtype": "Currency"},
				"total_qty_purchased",
				"available_stock_qty",
				{"fieldname": "available_stock_value", "fieldtype": "Currency"},
			],
			"method": "erpnext.startup.leaderboard.get_all_items",
			"icon": "stock",
		},
		"Supplier": {
			"fields": [
				{"fieldname": "total_purchase_amount", "fieldtype": "Currency"},
				"total_qty_purchased",
				{"fieldname": "outstanding_amount", "fieldtype": "Currency"},
			],
			"method": "erpnext.startup.leaderboard.get_all_suppliers",
			"icon": "buying",
		},
		"Sales Partner": {
			"fields": [
				{"fieldname": "total_sales_amount", "fieldtype": "Currency"},
				{"fieldname": "total_commission", "fieldtype": "Currency"},
			],
			"method": "erpnext.startup.leaderboard.get_all_sales_partner",
			"icon": "hr",
		},
		"Sales Person": {
			"fields": [{"fieldname": "total_sales_amount", "fieldtype": "Currency"}],
			"method": "erpnext.startup.leaderboard.get_all_sales_person",
			"icon": "customer",
		},
	}

	return leaderboards


@frappe.whitelist()
def get_all_customers(date_range, company, field, limit=None):
	filters = [["docstatus", "=", "1"], ["company", "=", company]]
	from_date, to_date = parse_date_range(date_range)
	if field == "outstanding_amount":
		if from_date and to_date:
			filters.append(["posting_date", "between", [from_date, to_date]])

		return frappe.get_list(
			"Sales Invoice",
			fields=["customer as name", {"SUM": "outstanding_amount", "as": "value"}],
			filters=filters,
			group_by="customer",
			order_by="value desc",
			limit=limit,
		)
	else:
		if field == "total_sales_amount":
			select_field = "base_net_total"
		elif field == "total_qty_sold":
			select_field = "total_qty"

		if from_date and to_date:
			filters.append(["transaction_date", "between", [from_date, to_date]])

		return frappe.get_list(
			"Sales Order",
			fields=["customer as name", {"SUM": select_field, "as": "value"}],
			filters=filters,
			group_by="customer",
			order_by="value desc",
			limit=limit,
		)


@frappe.whitelist()
def get_all_items(date_range, company, field, limit=None):
	if field in ("available_stock_qty", "available_stock_value"):
		sum_field = "actual_qty" if field == "available_stock_qty" else "stock_value"
		results = frappe.db.get_all(
			"Bin",
			fields=["item_code as name", {"SUM": sum_field, "as": "value"}],
			group_by="item_code",
			order_by="value desc",
			limit=limit,
		)
		readable_active_items = set(frappe.get_list("Item", filters={"disabled": 0}, pluck="name"))
		return [item for item in results if item["name"] in readable_active_items]
	else:
		if field == "total_sales_amount":
			select_field = "base_net_amount"
			select_doctype = "Sales Order"
		elif field == "total_purchase_amount":
			select_field = "base_net_amount"
			select_doctype = "Purchase Order"
		elif field == "total_qty_sold":
			select_field = "stock_qty"
			select_doctype = "Sales Order"
		elif field == "total_qty_purchased":
			select_field = "stock_qty"
			select_doctype = "Purchase Order"

		filters = [["docstatus", "=", "1"], ["company", "=", company]]
		from_date, to_date = parse_date_range(date_range)
		if from_date and to_date:
			filters.append(["transaction_date", "between", [from_date, to_date]])

		child_doctype = f"{select_doctype} Item"
		return frappe.get_list(
			select_doctype,
			fields=[
				f"`tab{child_doctype}`.item_code as name",
				{"SUM": f"`tab{child_doctype}`.{select_field}", "as": "value"},
			],
			filters=filters,
			order_by="value desc",
			group_by=f"`tab{child_doctype}`.item_code",
			limit=limit,
		)


@frappe.whitelist()
def get_all_suppliers(date_range, company, field, limit=None):
	filters = [["docstatus", "=", "1"], ["company", "=", company]]
	from_date, to_date = parse_date_range(date_range)

	if field == "outstanding_amount":
		if from_date and to_date:
			filters.append(["posting_date", "between", [from_date, to_date]])

		return frappe.get_list(
			"Purchase Invoice",
			fields=["supplier as name", {"SUM": "outstanding_amount", "as": "value"}],
			filters=filters,
			group_by="supplier",
			order_by="value desc",
			limit=limit,
		)
	else:
		if field == "total_purchase_amount":
			select_field = "base_net_total"
		elif field == "total_qty_purchased":
			select_field = "total_qty"

		if from_date and to_date:
			filters.append(["transaction_date", "between", [from_date, to_date]])

		return frappe.get_list(
			"Purchase Order",
			fields=["supplier as name", {"SUM": select_field, "as": "value"}],
			filters=filters,
			group_by="supplier",
			order_by="value desc",
			limit=limit,
		)


@frappe.whitelist()
def get_all_sales_partner(date_range, company, field, limit=None):
	if field == "total_sales_amount":
		select_field = "base_net_total"
	elif field == "total_commission":
		select_field = "total_commission"

	filters = [["docstatus", "=", "1"], ["company", "=", company], ["sales_partner", "is", "set"]]
	from_date, to_date = parse_date_range(date_range)
	if from_date and to_date:
		filters.append(["transaction_date", "between", [from_date, to_date]])

	return frappe.get_list(
		"Sales Order",
		fields=[
			"sales_partner as name",
			{"SUM": select_field, "as": "value"},
		],
		filters=filters,
		group_by="sales_partner",
		order_by="value DESC",
		limit=limit,
	)


@frappe.whitelist()
def get_all_sales_person(date_range, company, field=None, limit=0):
	filters = [
		["docstatus", "=", "1"],
		["company", "=", company],
		["Sales Team", "sales_person", "is", "set"],
	]
	from_date, to_date = parse_date_range(date_range)
	if from_date and to_date:
		filters.append(["transaction_date", "between", [from_date, to_date]])

	return frappe.get_list(
		"Sales Order",
		fields=[
			"`tabSales Team`.sales_person as name",
			{"SUM": "`tabSales Team`.allocated_amount", "as": "value"},
		],
		filters=filters,
		group_by="`tabSales Team`.sales_person",
		order_by="value desc",
		limit=limit,
	)


@deprecated(f"{__name__}.get_date_condition", "unknown", "v16", "No known instructions.")
def get_date_condition(date_range, field):
	date_condition = ""
	if date_range:
		date_range = frappe.parse_json(date_range)
		from_date, to_date = date_range
		date_condition = f"and {field} between {frappe.db.escape(from_date)} and {frappe.db.escape(to_date)}"
	return date_condition


def parse_date_range(date_range):
	if date_range:
		date_range = frappe.parse_json(date_range)
		return date_range[0], date_range[1]

	return None, None
