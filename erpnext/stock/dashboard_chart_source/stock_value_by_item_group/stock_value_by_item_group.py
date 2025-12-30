# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.query_builder.functions import Abs, Count, Date, Sum
from frappe.utils.dashboard import cache_source


@frappe.whitelist()
@cache_source
def get(
	chart_name=None,
	chart=None,
	no_cache=None,
	filters=None,
	from_date=None,
	to_date=None,
	timespan=None,
	time_interval=None,
	heatmap_year=None,
):
	if filters and isinstance(filters, str):
		filters = frappe.parse_json(filters)

	company = filters.get("company") if filters else None
	if not company:
		company = frappe.defaults.get_defaults().company

	labels, datasets = get_stock_value_by_item_group(company)

	return {
		"labels": labels,
		"datasets": [{"name": _("Stock Value"), "values": datasets}],
	}


def get_stock_value_by_item_group(company):
	doctype = frappe.qb.DocType("Bin")
	item_doctype = frappe.qb.DocType("Item")

	warehouse_filters = [["is_group", "=", 0]]
	if company:
		warehouse_filters.append(["company", "=", company])

	warehouses = frappe.get_list("Warehouse", pluck="name", filters=warehouse_filters)

	stock_value = Sum(doctype.stock_value)

	query = (
		frappe.qb.from_(doctype)
		.inner_join(item_doctype)
		.on(doctype.item_code == item_doctype.name)
		.select(item_doctype.item_group, stock_value.as_("stock_value"))
		.where(doctype.warehouse.isin(warehouses))
		.groupby(item_doctype.item_group)
		.orderby(stock_value, order=frappe.qb.desc)
		.limit(10)
	)

	results = query.run(as_dict=True)

	labels = []
	datapoints = []

	for row in results:
		if not row.stock_value:
			continue

		labels.append(_(row.item_group))
		datapoints.append(row.stock_value)

	return labels, datapoints
