# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.core.doctype.user_permission.user_permission import get_user_permissions
from frappe.permissions import get_allowed_docs_for_doctype
from frappe.query_builder.functions import Avg, IfNull
from frappe.utils import flt, today
from frappe.utils.nestedset import get_descendants_of

import erpnext
from erpnext.stock.doctype.company_restriction.company_restriction import get_allowed_warehouses_condition
from erpnext.stock.doctype.warehouse.warehouse import get_child_warehouses


def execute(filters=None):
	templates = get_templates(filters)
	columns = get_columns(list(templates))
	data = get_data(templates, filters)
	return columns, data


def get_templates(filters):
	"""Templates picked by the Items or the Item Groups filter, mapped to their Item Group."""
	items = get_filter_values(filters, "item")
	item_groups = get_filter_values(filters, "item_group")
	if items and item_groups:
		frappe.throw(_("Select either Items or Item Groups, not both"))
	if not (items or item_groups):
		return {}

	template_filters = {"has_variants": 1}
	if items:
		template_filters["name"] = ["in", items]
	else:
		template_filters.update(disabled=0, item_group=["in", get_item_groups_with_descendants(item_groups)])

	return dict(
		frappe.get_list(
			"Item", filters=template_filters, fields=["name", "item_group"], order_by="name", as_list=True
		)
	)


def get_item_groups_with_descendants(item_groups):
	return [
		*item_groups,
		*(child for group in item_groups for child in get_descendants_of("Item Group", group)),
	]


def get_filter_values(filters, fieldname):
	values = filters.get(fieldname) or []
	return [values] if isinstance(values, str) else values


def get_data(templates, filters):
	if not templates:
		return []

	variant_results = frappe.get_list(
		"Item",
		fields=["name", "variant_of", "item_group", "stock_uom"],
		filters={"variant_of": ["in", list(templates)], "disabled": 0},
	)

	if not variant_results:
		frappe.msgprint(_("There are no item variants for the selected filters"))
		return []

	variant_list = [variant.name for variant in variant_results]
	warehouses = get_selected_warehouses(filters)
	open_orders = get_open_sales_orders(variant_list, warehouses)
	variant_rows = get_variant_rows(variant_results, warehouses, open_orders)

	rows_by_template = {}
	for row in variant_rows:
		rows_by_template.setdefault(row["template"], []).append(row)

	data = []
	for template, item_group in templates.items():
		if rows := rows_by_template.get(template):
			data.append(get_template_row(template, item_group, rows, open_orders))
			data.extend(rows)

	return data


def get_variant_rows(variant_results, warehouses, open_orders):
	"""Variant rows, indented under their template."""
	variant_list = [variant.name for variant in variant_results]
	stock_details_map = get_stock_details_map(variant_list, warehouses)
	buying_price_map = get_buying_price_map(variant_list)
	selling_price_map = get_selling_price_map(variant_list)
	currency = get_report_currency()
	attr_val_map = get_attribute_values_map(variant_list)

	variant_rows = []
	for variant in variant_results:
		stock_details = stock_details_map.get(variant.name, {})
		variant_rows.append(
			{
				**{
					frappe.scrub(attribute): value
					for attribute, value in attr_val_map.get(variant.name, {}).items()
				},
				"variant_name": variant.name,
				"template": variant.variant_of,
				"item_group": variant.item_group,
				"indent": 1,
				"stock_uom": variant.stock_uom,
				"current_stock": stock_details.get("Inventory") or 0,
				"in_production": stock_details.get("In Production") or 0,
				"open_orders": len(open_orders.get(variant.name, ())),
				"avg_buying_price_list_rate": buying_price_map.get(variant.name) or 0,
				"avg_selling_price_list_rate": selling_price_map.get(variant.name) or 0,
				"currency": currency,
			}
		)

	return variant_rows


def get_template_row(template, item_group, rows, open_orders):
	"""Template subtotal. Orders with several of its variants count once.
	Stock is totalled only when all variants share a stock UOM."""
	orders = set().union(*(open_orders.get(row["variant_name"], ()) for row in rows))
	template_row = {
		"variant_name": template,
		"item_group": item_group,
		"indent": 0,
		"open_orders": len(orders),
		"stock_uom": None,
		"current_stock": None,
		"in_production": None,
	}

	stock_uoms = {row["stock_uom"] for row in rows}
	if len(stock_uoms) == 1:
		template_row.update(
			stock_uom=stock_uoms.pop(),
			current_stock=sum(row["current_stock"] for row in rows),
			in_production=sum(row["in_production"] for row in rows),
		)

	return template_row


def get_columns(templates):
	columns = [
		{
			"fieldname": "variant_name",
			"label": _("Item"),
			"fieldtype": "Link",
			"options": "Item",
			"width": 200,
		},
		{
			"fieldname": "item_group",
			"label": _("Item Group"),
			"fieldtype": "Link",
			"options": "Item Group",
			"width": 150,
		},
	]

	attributes = frappe.get_all(
		"Item Variant Attribute",
		filters={"parent": ["in", templates], "parenttype": "Item"},
		pluck="attribute",
		order_by="idx",
	)

	for attribute in dict.fromkeys(attributes):
		columns.append(
			{
				"fieldname": frappe.scrub(attribute),
				"label": attribute,
				"fieldtype": "Data",
				"width": 100,
			}
		)

	additional_columns = [
		{
			"fieldname": "avg_buying_price_list_rate",
			"label": _("Avg. Buying Price List Rate"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 150,
		},
		{
			"fieldname": "avg_selling_price_list_rate",
			"label": _("Avg. Selling Price List Rate"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 150,
		},
		{
			"fieldname": "stock_uom",
			"label": _("Stock UOM"),
			"fieldtype": "Link",
			"options": "UOM",
			"width": 100,
		},
		{"fieldname": "current_stock", "label": _("Current Stock"), "fieldtype": "Float", "width": 120},
		{"fieldname": "in_production", "label": _("In Production"), "fieldtype": "Float", "width": 150},
		{
			"fieldname": "open_orders",
			"label": _("Open Sales Orders"),
			"fieldtype": "Float",
			"width": 150,
		},
	]
	columns.extend(additional_columns)

	return columns


def get_selected_warehouses(filters):
	"""Selected warehouses with the descendants of selected groups."""
	return list(
		{
			child
			for warehouse in get_filter_values(filters, "warehouse")
			for child in get_child_warehouses(warehouse)
		}
	)


def get_open_sales_orders(variants_list, warehouses):
	order_filters = [
		["Sales Order", "docstatus", "=", 1],
		["Sales Order", "status", "not in", ["Closed", "Completed"]],
		["Sales Order Item", "item_code", "in", variants_list],
	]
	if warehouses:
		order_filters.append(["Sales Order Item", "warehouse", "in", warehouses])

	open_sales_orders = frappe.db.get_list(
		"Sales Order",
		fields=[
			"name",
			"`tabSales Order Item`.item_code",
			"`tabSales Order Item`.qty",
			"`tabSales Order Item`.delivered_qty",
		],
		filters=order_filters,
	)

	open_orders = {}
	for row in open_sales_orders:
		if flt(row.delivered_qty) < flt(row.qty):
			open_orders.setdefault(row.item_code, set()).add(row.name)

	return open_orders


def get_stock_details_map(variant_list, warehouses):
	bin_filters = [{"item_code": ["in", variant_list]}]
	if warehouses:
		bin_filters.append({"warehouse": ["in", warehouses]})
	if permitted_warehouses := get_allowed_docs_for_doctype(
		get_user_permissions().get("Warehouse", []), "Item"
	):
		bin_filters.append({"warehouse": ["in", permitted_warehouses]})
	if condition := get_allowed_warehouses_condition(frappe.qb.DocType("Bin").warehouse):
		bin_filters.append(condition)

	stock_details = frappe.db.get_all(
		"Bin",
		fields=[
			{"SUM": "planned_qty", "as": "planned_qty"},
			{"SUM": "actual_qty", "as": "actual_qty"},
			{"SUM": "projected_qty", "as": "projected_qty"},
			"item_code",
		],
		filters=bin_filters,
		group_by="item_code",
	)

	stock_details_map = {}
	for row in stock_details:
		name = row.get("item_code")
		stock_details_map[name] = {
			"Inventory": row.get("actual_qty"),
			"In Production": row.get("planned_qty"),
		}

	return stock_details_map


def get_buying_price_map(variant_list):
	return get_price_map(variant_list, "buying")


def get_selling_price_map(variant_list):
	return get_price_map(variant_list, "selling")


def get_price_map(variant_list, price_type):
	item_price = frappe.qb.DocType("Item Price")
	item = frappe.qb.DocType("Item")
	rows = (
		frappe.qb.from_(item_price)
		.inner_join(item)
		.on(item.name == item_price.item_code)
		.select(item_price.item_code, Avg(item_price.price_list_rate))
		.where(
			(item_price.item_code.isin(variant_list))
			& (item_price[price_type] == 1)
			& (item_price.currency == get_report_currency())
			& (IfNull(item_price.customer, "") == "")
			& (IfNull(item_price.supplier, "") == "")
			& ((IfNull(item_price.uom, "") == "") | (item_price.uom == item.stock_uom))
			& (item_price.valid_from.isnull() | (item_price.valid_from <= today()))
			& (item_price.valid_upto.isnull() | (item_price.valid_upto >= today()))
		)
		.groupby(item_price.item_code)
	).run()

	return dict(rows)


def get_report_currency():
	company = erpnext.get_default_company()
	return (company and erpnext.get_company_currency(company)) or frappe.db.get_default("currency")


def get_attribute_values_map(variant_list):
	attribute_list = frappe.db.get_all(
		"Item Variant Attribute",
		fields=["attribute", "attribute_value", "parent"],
		filters={"parent": ["in", variant_list]},
	)

	attr_val_map = {}
	for row in attribute_list:
		name = row.get("parent")
		if not attr_val_map.get(name):
			attr_val_map[name] = {}

		attr_val_map[name][row.get("attribute")] = row.get("attribute_value")

	return attr_val_map
